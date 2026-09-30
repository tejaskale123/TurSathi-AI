import re
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password
from app.database.models.user import User
from app.schemas.auth import UserRegister


def register_user(db: Session, user_in: UserRegister) -> User:
    """
    Registers a new user after verifying duplicate mobile number and email.
    Hashes the password securely and commits the user to PostgreSQL.
    """
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
    
    # Normalize mobile number if identifier looks like mobile
    cleaned_mobile = re.sub(r"[\s()\-\+]", "", cleaned_identifier)
    if cleaned_mobile.startswith("91") and len(cleaned_mobile) == 12:
        cleaned_mobile = cleaned_mobile[2:]

    # Query user by mobile number OR email
    db_user = db.query(User).filter(
        or_(
            User.mobile_number == cleaned_mobile,
            User.mobile_number == cleaned_identifier,
            User.email == cleaned_identifier.lower()
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
