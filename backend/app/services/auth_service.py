import re
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password
from app.database.models.user import User
from app.schemas.auth import UserRegister


def normalize_mobile(mobile: str) -> str:
    if not mobile:
        return mobile
    cleaned = re.sub(r"[\s()\-\+]", "", mobile.strip())
    if cleaned.startswith("91") and len(cleaned) == 12:
        return cleaned[2:]
    return cleaned

def normalize_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return email
    return email.strip().lower()

def register_user(db: Session, user_in: UserRegister) -> User:
    """
    Registers a new user after verifying duplicate mobile number and email.
    Hashes the password securely and commits the user to PostgreSQL.
    """
    user_in.mobile_number = normalize_mobile(user_in.mobile_number)
    user_in.email = normalize_email(user_in.email)

    # 1. Check duplicate mobile number
    existing_mobile = db.query(User).filter(User.mobile_number == user_in.mobile_number).first()
    if existing_mobile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile number is already registered. Please login or use a different mobile number."
        )

    # 2. Check duplicate email if provided
    if user_in.email:
        existing_email = db.query(User).filter(User.email == user_in.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered. Please login or use a different email."
            )

    # 3. Hash password securely
    hashed_password = get_password_hash(user_in.password)

    # 4. Create User instance
    db_user = User(
        full_name=user_in.full_name,
        mobile_number=user_in.mobile_number,
        email=user_in.email,
        password_hash=hashed_password,
        is_active=True
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, identifier: str, password: str) -> User:
    """
    Authenticates a user by email OR mobile number and verifies password.
    Returns user instance or raises HTTP 401/400.
    """
    cleaned_identifier = identifier.strip()
    
    # Normalize mobile number and email
    cleaned_mobile = normalize_mobile(cleaned_identifier)
    cleaned_email = normalize_email(cleaned_identifier)

    # Query user by mobile number OR email
    db_user = db.query(User).filter(
        or_(
            User.mobile_number == cleaned_mobile,
            User.email == cleaned_email
        )
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mobile number/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mobile number/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive. Please contact support."
        )

    return db_user


def authenticate_google_user(db: Session, google_id: str, email: str, name: str) -> User:
    """
    Finds or creates a TurSathi user from Google OAuth profile data.
    """
    normalized_email = normalize_email(email)
    
    # 1. Check if google_id already exists
    user = db.query(User).filter(User.google_id == google_id).first()
    if user:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account is inactive. Please contact support.")
        return user
        
    # 2. Check if a local user exists with the SAME verified email
    if normalized_email:
        existing_email_user = db.query(User).filter(User.email == normalized_email).first()
        if existing_email_user:
            # Safely link the google_id to the existing user
            existing_email_user.google_id = google_id
            db.commit()
            db.refresh(existing_email_user)
            if not existing_email_user.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account is inactive. Please contact support.")
            return existing_email_user
            
    # 3. Create a NEW Google-only user
    new_user = User(
        full_name=name or "Google User",
        email=normalized_email,
        google_id=google_id,
        auth_provider="google",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

