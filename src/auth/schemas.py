# src/auth/schemas.py

from typing import Annotated, Optional
from pydantic import BaseModel, EmailStr, Field, model_validator

from src.models.models import UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

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
    token_type: str = "bearer"

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    message: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: Annotated[str, Field(min_length=8)]  # Enforce a minimum length

class ChangePasswordResponse(BaseModel):
    message: str

class ResetPasswordResponse(BaseModel):
    message: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str = Field(..., min_length=8)

    @model_validator(mode="after")
    def check_passwords_match(cls, values):
        new = values.new_password
        confirm = values.confirm_new_password
        if new != confirm:
            raise ValueError("new_password and confirm_new_password must match")
        return values

    class Config:
        from_attributes = True