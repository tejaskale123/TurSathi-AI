from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.core.security import create_access_token, decode_access_token
from app.database.models.user import User
from app.database.session import get_db
from app.schemas.auth import Token, UserLogin, UserRegister, UserResponse
from app.services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_current_user(
    authorization: str = Header(..., description="Bearer token in format: Bearer <token>"),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that validates JWT access token from request header
    and retrieves current authenticated user.
    """
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
