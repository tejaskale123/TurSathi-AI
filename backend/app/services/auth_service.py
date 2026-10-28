from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import re
import secrets
from typing import Optional
from fastapi import HTTPException, status
import jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.database.models.password_reset_otp import PasswordResetOTP
from app.database.models.user import User
from app.schemas.auth import UserRegister
from app.services.email_service import send_otp_email

logger = logging.getLogger("tursathi.auth")


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


def hash_otp(otp: str) -> str:
    """
    Computes a keyed HMAC-SHA256 digest of the 6-digit OTP using settings.SECRET_KEY.
    Prevents offline dictionary guessing attacks if database records are exposed.
    """
    key = settings.SECRET_KEY.encode("utf-8")
    data = otp.strip().encode("utf-8")
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def create_reset_token(user_id: int, jti: str) -> str:
    """
    Creates a single-purpose, cryptographically signed JWT reset authorization token.
    Valid for settings.RESET_TOKEN_EXPIRE_MINUTES (15 mins).
    Includes a unique token identifier (jti) tracked in the database to prevent replay.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "purpose": "password_reset",
        "jti": jti,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_reset_token(token: str) -> Optional[dict]:
    """
    Decodes and validates a single-purpose password reset token.
    Rejects normal access tokens or tokens with mismatched purpose.
    Returns dictionary with user_id and jti if valid, else None.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("purpose") != "password_reset":
            return None
        user_id = int(payload.get("sub"))
        jti = payload.get("jti")
        if not jti:
            return None
        return {"user_id": user_id, "jti": jti}
    except Exception:
        return None


def request_password_reset(db: Session, identifier: str) -> None:
    """
    Handles a password recovery request for a registered email or mobile number.
    Enforces rate-limiting resend cooldown, invalidates superseded OTPs,
    generates a secure 6-digit OTP, stores its HMAC hash, and sends an email.
    Always returns without error for nonexistent accounts (anti-enumeration).
    """
    cleaned = identifier.strip()
    cleaned_email = normalize_email(cleaned)
    cleaned_mobile = normalize_mobile(cleaned)

    # 1. Lookup user by email or mobile number
    db_user = db.query(User).filter(
        or_(
            User.email == cleaned_email,
            User.mobile_number == cleaned_mobile
        )
    ).first()

    # If user doesn't exist, has no email, or is inactive, exit silently (anti-enumeration)
    if not db_user or not db_user.email or not db_user.is_active:
        logger.info("[AUTH] Password reset requested for non-eligible or non-existent identifier.")
        return

    now_utc = datetime.now(timezone.utc)

    # 2. Check resend cooldown on the most recent unexpired OTP for this user
    recent_active_otp = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == db_user.id,
        PasswordResetOTP.is_used == False,
        PasswordResetOTP.expires_at > now_utc
    ).order_by(PasswordResetOTP.created_at.desc()).first()

    if recent_active_otp and recent_active_otp.created_at:
        created_time = recent_active_otp.created_at
        if created_time.tzinfo is None:
            created_time = created_time.replace(tzinfo=timezone.utc)
        elapsed = (now_utc - created_time).total_seconds()
        if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
            wait_remaining = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {wait_remaining} seconds before requesting another code."
            )

    # 3. Supersede / invalidate all prior active OTPs for this user
    db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == db_user.id,
        PasswordResetOTP.is_used == False
    ).update({"is_used": True}, synchronize_session=False)

    # 4. Generate a 6-digit cryptographically secure OTP
    otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
    otp_hash = hash_otp(otp_code)
    expires_at = now_utc + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    # 5. Record OTP in database
    new_otp = PasswordResetOTP(
        user_id=db_user.id,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempts=0,
        is_used=False
    )
    db.add(new_otp)
    db.commit()

    # 6. Dispatch email via SMTP
    email_sent = send_otp_email(
        recipient_email=db_user.email,
        recipient_name=db_user.full_name,
        otp_code=otp_code
    )

    if not email_sent:
        # Invalidate OTP immediately if delivery failed to avoid phantom active codes
        new_otp.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again later."
        )


def verify_password_reset_otp(db: Session, identifier: str, otp: str) -> str:
    """
    Verifies the 6-digit OTP against the stored HMAC hash.
    Enforces maximum attempts, expiry, and single-use invalidation.
    Returns a signed reset authorization token upon success.
    """
    cleaned = identifier.strip()
    cleaned_email = normalize_email(cleaned)
    cleaned_mobile = normalize_mobile(cleaned)

    db_user = db.query(User).filter(
        or_(
            User.email == cleaned_email,
            User.mobile_number == cleaned_mobile
        )
    ).first()

    if not db_user or not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code or email address."
        )

    now_utc = datetime.now(timezone.utc)

    # Retrieve the latest active OTP for this user that hasn't been verified yet
    otp_record = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == db_user.id,
        PasswordResetOTP.is_used == False,
        PasswordResetOTP.reset_token_hash.is_(None)
    ).order_by(PasswordResetOTP.created_at.desc()).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code found. Please request a new one."
        )

    # Check expiry
    expiry = otp_record.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if now_utc > expiry:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one."
        )

    # Check max attempts before checking hash
    if otp_record.attempts >= settings.OTP_MAX_ATTEMPTS:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum verification attempts exceeded. Please request a new code."
        )

    # Constant-time comparison of keyed HMAC hash
    computed_hash = hash_otp(otp)
    if not hmac.compare_digest(otp_record.otp_hash, computed_hash):
        otp_record.attempts += 1
        db.commit()
        remaining = max(0, settings.OTP_MAX_ATTEMPTS - otp_record.attempts)
        if remaining == 0:
            otp_record.is_used = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum verification attempts exceeded. Please request a new code."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification code. {remaining} attempt(s) remaining."
        )

    # Successful verification: mark OTP as verified and record unique reset_token_hash
    jti = secrets.token_hex(16)
    otp_record.reset_token_hash = hash_otp(jti)
    db.commit()

    return create_reset_token(db_user.id, jti)


def reset_password_with_token(db: Session, reset_token: str, new_password: str) -> None:
    """
    Validates the single-use reset authorization token, updates the user's password,
    updates updated_at timestamp, and invalidates all outstanding OTP requests.
    """
    token_data = decode_reset_token(reset_token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired password reset authorization. Please request a new code.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = token_data["user_id"]
    jti = token_data["jti"]

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user or not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify that this reset_token_hash exists, is unused, and belongs to this user
    jti_hash = hash_otp(jti)
    valid_reset_record = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == user_id,
        PasswordResetOTP.reset_token_hash == jti_hash,
        PasswordResetOTP.is_used == False
    ).first()

    if not valid_reset_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This password reset authorization has already been used or is no longer valid. Please request a new code.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Invalidate all remaining OTP/reset records for this user
    db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == db_user.id,
        PasswordResetOTP.is_used == False
    ).update({"is_used": True}, synchronize_session=False)

    # Hash new password securely using bcrypt
    db_user.password_hash = get_password_hash(new_password)
    from sqlalchemy import func
    db_user.updated_at = func.now()

    db.commit()
    db.refresh(db_user)
    logger.info("[AUTH] Password successfully reset for user id %s", db_user.id)

