from datetime import datetime
import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserRegister(BaseModel):
    full_name: str = Field(..., description="User's full name")
    mobile_number: str = Field(..., description="10-digit Indian mobile number")
    email: str = Field(..., description="Email address required for password recovery")
    password: str = Field(..., min_length=8, description="Password (at least 8 characters)")
    confirm_password: str = Field(..., description="Must match password")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Full name cannot be empty")
        return trimmed

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, v: str) -> str:
        # Strip spaces, hyphens, and +91 prefix
        cleaned = re.sub(r"[\s()\-\+]", "", v)
        if cleaned.startswith("91") and len(cleaned) == 12:
            cleaned = cleaned[2:]
        
        if not re.match(r"^[6-9]\d{9}$", cleaned):
            raise ValueError("Mobile number must be a valid 10-digit Indian mobile number")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v:
            raise ValueError("Email address is required")
        trimmed = v.strip().lower()
        if not trimmed:
            raise ValueError("Email address cannot be empty")
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", trimmed):
            raise ValueError("Enter a valid email address")
        return trimmed

    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserRegister":
        if self.password != self.confirm_password:
            raise ValueError("Password and Confirm Password do not match")
        return self


class UserLogin(BaseModel):
    identifier: str = Field(..., description="Mobile number or Email address")
    password: str = Field(..., description="User's password")

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Mobile number or Email address is required")
        return trimmed

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v:
            raise ValueError("Password is required")
        return v


class UserResponse(BaseModel):
    id: int
    full_name: str
    mobile_number: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(..., description="Registered email address")

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not trimmed:
            raise ValueError("Email address is required")
        return trimmed


class VerifyOTPRequest(BaseModel):
    identifier: str = Field(..., description="Registered email address")
    otp: str = Field(..., description="6-digit verification code")

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not trimmed:
            raise ValueError("Email address is required")
        return trimmed

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        cleaned = re.sub(r"\s+", "", v)
        if not re.match(r"^\d{6}$", cleaned):
            raise ValueError("Verification code must be exactly 6 digits")
        return cleaned


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(..., description="Single-use reset authorization token")
    new_password: str = Field(..., min_length=8, description="New password (at least 8 characters)")
    confirm_password: str = Field(..., description="Must match new password")

    @field_validator("reset_token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Reset authorization token is required")
        return trimmed

    @model_validator(mode="after")
    def check_passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Password and Confirm Password do not match")
        return self


class GenericAuthResponse(BaseModel):
    message: str


class VerifyOTPResponse(BaseModel):
    reset_token: str
    token_type: str = "bearer"
    message: str = "Code verified successfully."
