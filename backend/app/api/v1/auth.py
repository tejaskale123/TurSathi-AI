from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status, Body
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx
from datetime import timedelta
import urllib.parse
import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.database.models.user import User
from app.database.session import get_db
from app.schemas.auth import Token, UserLogin, UserRegister, UserResponse
from app.services.auth_service import authenticate_user, register_user, authenticate_google_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer token in format: Bearer <token>"),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that validates JWT access token from request header
    and retrieves current authenticated user.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1].strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id_int).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Registers a new farmer account.
    Returns signed JWT access token and public user profile upon successful registration.
    """
    new_user = register_user(db=db, user_in=user_in)
    access_token = create_access_token(subject=new_user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
def login(
    login_in: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticates a farmer using mobile number OR email and password.
    Returns signed JWT access token and user profile.
    """
    user = authenticate_user(
        db=db,
        identifier=login_in.identifier,
        password=login_in.password
    )
    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Returns the currently authenticated farmer's user profile.
    """
    return UserResponse.model_validate(current_user)


@router.get("/google/login", status_code=status.HTTP_302_FOUND)
def google_login():
    """
    Redirects the user to Google's OAuth 2.0 authorization page.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured on the server.")
    
    scope = "openid email profile"
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scope": scope,
        "access_type": "online",
        "prompt": "select_account"
    }
    url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    """
    Handles the callback from Google. Exchanges the code for an access token,
    retrieves user info, and creates a short-lived exchange code.
    Redirects back to the frontend with the exchange code.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured.")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code with Google.")
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        # Get user info
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        userinfo_response = await client.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve user info from Google.")
            
        user_info = userinfo_response.json()

    if not user_info.get("email_verified"):
        raise HTTPException(status_code=400, detail="Google account email is not verified.")
        
    google_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")
    
    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Incomplete user information from Google.")
        
    # Authenticate or create user
    user = authenticate_google_user(db, google_id=google_id, email=email, name=name)
    
    # Create a short-lived exchange code (valid for 5 minutes)
    exchange_code = create_access_token(subject=f"exchange_{user.id}", expires_delta=timedelta(minutes=5))
    
    # Extract the frontend origin for redirection
    frontend_url = "http://localhost:8081"
    if settings.FRONTEND_CORS_ORIGINS:
        origins = [o.strip() for o in settings.FRONTEND_CORS_ORIGINS.split(",")]
        if origins:
            frontend_url = origins[0]
            
    redirect_url = f"{frontend_url}?exchange_code={exchange_code}"
    return RedirectResponse(redirect_url)


@router.post("/google/exchange", response_model=Token, status_code=status.HTTP_200_OK)
def google_exchange(
    exchange_code: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Exchanges the short-lived exchange code for a permanent access token.
    """
    payload = decode_access_token(exchange_code)
    if not payload or not payload.get("sub", "").startswith("exchange_"):
        raise HTTPException(status_code=401, detail="Invalid or expired exchange code.")
        
    try:
        user_id = int(payload["sub"].split("_")[1])
    except (ValueError, IndexError):
        raise HTTPException(status_code=401, detail="Invalid token subject.")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")
        
    # Generate the real access token
    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

