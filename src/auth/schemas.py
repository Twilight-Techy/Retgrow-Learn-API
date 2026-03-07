# src/auth/schemas.py

from typing import Annotated, Optional
from uuid import UUID
from pydantic import ConfigDict, BaseModel, EmailStr, Field, model_validator
from fastapi import HTTPException

from src.models.models import UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    # token_type: str = "bearer"

class GoogleAuthRequest(BaseModel):
    token: str

class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    password_confirm: str
    first_name: str
    last_name: str
    role: Optional[UserRole] = UserRole.STUDENT

class SignupResponse(BaseModel):
    message: str = "User successfully created. Please check your email to verify your account."

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class ResendVerificationResponse(BaseModel):
    message: str = "A new verification email has been sent."

class VerifyUserRequest(BaseModel):
    email: EmailStr
    verification_code: str

class VerifyUserResponse(BaseModel):
    message: str = "User has been verified successfully."
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    message: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: Annotated[str, Field(min_length=8)]  # Enforce a minimum length
    confirm_new_password: Annotated[str, Field(min_length=8)]  # Enforce a minimum length

    @model_validator(mode="after")
    def check_passwords_match(self):
        new = self.new_password
        confirm = self.confirm_new_password
        if new != confirm:
            raise HTTPException(
                status_code=400,
                detail="New password and confirmation do not match."
            )
        return self
class ResetPasswordResponse(BaseModel):
    message: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str = Field(..., min_length=8)

    @model_validator(mode="after")
    def check_passwords_match(self):
        new = self.new_password
        confirm = self.confirm_new_password
        if new != confirm:
            raise HTTPException(
                status_code=400,
                detail="New password and confirmation do not match."
            )
        if new == self.current_password:
            raise HTTPException(
                status_code=400,
                detail="New password cannot be the same as the current password."
            )
        return self
    model_config = ConfigDict(from_attributes=True)

class ChangePasswordResponse(BaseModel):
    message: str

class AuthMeResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    role: str
    is_active: bool = True
    current_plan: Optional[str] = "free"
    model_config = ConfigDict(from_attributes=True)
