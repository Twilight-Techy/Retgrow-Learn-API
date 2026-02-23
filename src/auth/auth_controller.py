# src/auth/auth_controller.py

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import SignupRequest, ResendVerificationRequest
from src.auth.check_consecutive_logins import check_consecutive_logins
from src.auth.dependencies import get_current_user
from src.common.database.database import get_db_session
from src.common.rate_limit import limiter
from src.auth import auth_service, schemas
from src.models.models import User
from src.modules.achievements.achievement_tasks import award_achievement

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: schemas.LoginRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Authenticate a user and return an access token.
    
    - **email**: The user's email address.
    - **password**: The user's password.
    """
    user, access_token, refresh_token = await auth_service.login_user(credentials.email, credentials.password, db)
    if not access_token or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
     # Check if the user qualifies for the "Consistent" achievement.
    if await check_consecutive_logins(user, db):
        background_tasks.add_task(award_achievement, str(user.id), "Consistent")

    return schemas.TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.get("/google/login")
async def google_auth_login():
    """
    Redirect the user to the Google OAuth2 consent screen.
    """
    auth_url = await auth_service.generate_google_auth_url()
    return RedirectResponse(url=auth_url)

@router.get("/google/callback")
async def google_auth_callback(
    code: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Handle the callback from Google OAuth2.
    Exchanges the code for tokens, authenticates the user, 
    and redirects to the frontend with tokens as query params.
    """
    user, access_token, refresh_token = await auth_service.handle_google_callback(code, db)
    
    # Check consistent login achievement
    if await check_consecutive_logins(user, db):
        background_tasks.add_task(award_achievement, str(user.id), "Consistent")

    from src.common.config import settings
    frontend_callback_url = f"{settings.FRONTEND_URL}/api/auth/callback"
    redirect_url = f"{frontend_callback_url}?access_token={access_token}&refresh_token={refresh_token}"
    return RedirectResponse(url=redirect_url)

@router.get("/me", response_model=schemas.AuthMeResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info (minimal).
    """
    return current_user

@router.post("/signup", response_model=schemas.SignupResponse)
async def signup(
    signup_data: SignupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    """

    Register a new user and return a message.
    
    - **username**: The user's username.
    - **email**: The user's email address.
    - **password**: The user's password.
    - **first_name**: The user's first name.
    - **last_name**: The user's last name.
    """
    await auth_service.signup_user(
        signup_data.model_dump(), db, background_tasks
    )

    return schemas.SignupResponse()

@router.post("/resend-verification")
async def resend_verification(
    request: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Resend a verification email to the user.    
    - **email**: The user's email address.
    """

    await auth_service.resend_verification_email(
        request.email, db, background_tasks
    )

    return schemas.ResendVerificationResponse()

@router.post("/verify")
async def verify_user(
    verification_data: schemas.VerifyUserRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """Verify a user's email using a verification code."""
    access_token, refresh_token = await auth_service.verify_user(verification_data.model_dump(), db, background_tasks)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code."
        )
    return schemas.VerifyUserResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
async def refresh_token(
    request: Request,
    payload: schemas.RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    """
    new_access, new_refresh = await auth_service.refresh_access_token(payload.refresh_token, db)
    return schemas.TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/forgot-password", response_model=schemas.ForgotPasswordResponse)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    forgot_req: schemas.ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Process a forgot-password request.
    
    The endpoint will always return a success message, even if the email is not associated with any account.
    """
    await auth_service.process_forgot_password(forgot_req.email, db, background_tasks)
    return schemas.ForgotPasswordResponse(
        message="If an account with this email exists, a password reset link has been sent."
    )

@router.post("/reset-password", response_model=schemas.ResetPasswordResponse)
async def reset_password(
    payload: schemas.ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Reset the user's password.
    
    - **token**: The password reset token.
    - **new_password**: The new password to set.
    """
    success = await auth_service.reset_password(payload.token, payload.new_password, db, background_tasks)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )
    return schemas.ResetPasswordResponse(message="Password reset successful.")

@router.post("/change-password", response_model=schemas.ChangePasswordResponse)
async def change_password(
    change_req: schemas.ChangePasswordRequest,
    background_tasks: BackgroundTasks,
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
        db,
        background_tasks
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect!"
        )
    return schemas.ChangePasswordResponse(message="Password changed successfully!")