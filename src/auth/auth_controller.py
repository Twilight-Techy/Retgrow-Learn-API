# src/auth/auth_controller.py

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.check_consecutive_logins import check_consecutive_logins
from src.auth.dependencies import get_current_user
from src.common.database.database import get_db_session
from src.auth import auth_service, schemas
from src.models.models import User
from src.modules.achievements.achievement_tasks import award_achievement

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=schemas.TokenResponse)
async def login(
    credentials: schemas.LoginRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Authenticate a user and return an access token.
    
    - **email**: The user's email address.
    - **password**: The user's password.
    """
    user, access_token = await auth_service.login_user(credentials.email, credentials.password, db)
    if not access_token or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
     # Check if the user qualifies for the "Consistent" achievement.
    if await check_consecutive_logins(user, db):
        background_tasks.add_task(award_achievement, str(user.id), "Consistent")

    return schemas.TokenResponse(access_token=access_token)

@router.post("/signup", response_model=schemas.SignupResponse)
async def signup(
    signup_data: schemas.SignupRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Register a new user and return an access token.
    
    - **username**: The user's username.
    - **email**: The user's email address.
    - **password**: The user's password.
    - **first_name**: The user's first name.
    - **last_name**: The user's last name.
    """
    access_token = await auth_service.signup_user(signup_data.model_dump(), db)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signup data or user already exists"
        )
    return schemas.SignupResponse(access_token=access_token)

@router.post("/forgot-password", response_model=schemas.ForgotPasswordResponse)
async def forgot_password(
    request: schemas.ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Process a forgot-password request.
    
    The endpoint will always return a success message, even if the email is not associated with any account.
    """
    await auth_service.process_forgot_password(request.email, db)
    return schemas.ForgotPasswordResponse(
        message="If an account with this email exists, a password reset link has been sent."
    )

@router.post("/reset-password", response_model=schemas.ResetPasswordResponse)
async def reset_password(
    payload: schemas.ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Reset the user's password.
    
    - **token**: The password reset token.
    - **new_password**: The new password to set.
    """
    success = await auth_service.reset_password(payload.token, payload.new_password, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )
    return schemas.ResetPasswordResponse(message="Password reset successful.")

@router.post("/change-password", response_model=schemas.ChangePasswordResponse)
async def change_password(
    change_req: schemas.ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Change the current user's password.
    
    The request must include the current password, a new password (minimum 8 characters),
    and a confirmation that matches the new password.
    """
    success = await auth_service.change_password(
        current_user,
        change_req.current_password,
        change_req.new_password,
        db
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )
    return {"message": "Password changed successfully."}