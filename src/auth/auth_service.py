# src/auth/auth_service.py

from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, BackgroundTasks
import jwt
from sqlalchemy import or_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jwt.exceptions import DecodeError

from src.common.config import settings
from src.common.utils.email_service import send_email, send_verification_email
from src.common.utils.otp import generate_verification_code
from src.models.models import User, UserLogin, AuthProvider

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow


# Initialize the password context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that the provided password matches the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token including an expiration date."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=settings.JWT_EXPIRATION_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT refresh token with a longer expiry, signed with a separate secret."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

async def create_user(user_data: dict, db: AsyncSession):
    # Check if user with provided email already exists
    result = await db.execute(
        select(User).where(
            or_(
                User.email == user_data["email"],
                User.username == user_data["username"]
            )
        )
    )
    existing_user = result.scalars().first()

    if existing_user:
        if existing_user.email == user_data["email"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists!"
            )
        elif existing_user.username == user_data["username"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this username already exists!"
            )

    verification_code = generate_verification_code()

    # Create a new User instance
    new_user = User(
        username=user_data["username"],
        email=user_data["email"],
        password_hash=hash_password(user_data["password"]),
        first_name=user_data["first_name"],
        last_name=user_data["last_name"],
        verification_code=verification_code,
        role=user_data["role"]
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def signup_user(user_data: dict, db: AsyncSession, background_tasks: BackgroundTasks):
    """Create a new user and send a verification email."""
    if user_data["password"] != user_data["password_confirm"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match!"
        )

    new_user = await create_user(user_data, db)
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signup data or user already exists!"
        )

    background_tasks.add_task(send_verification_email, new_user.email, new_user.first_name, new_user.verification_code)

async def resend_verification_email(email: str, db: AsyncSession, background_tasks: BackgroundTasks):
    """
    Resend a verification email to the user.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found!")
    if user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already verified!")

    new_verification_code = generate_verification_code()
    user.verification_code = new_verification_code
    await db.commit()
    await db.refresh(user)
    background_tasks.add_task(send_verification_email, user.email, user.first_name, new_verification_code)

async def verify_user(verification_data: dict, db: AsyncSession, background_tasks: BackgroundTasks) -> str:
    """Verify a user's email using the provided verification code.
    """
    result = await db.execute(select(User).where(User.email == verification_data["email"]))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user does not exist!"
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified!"
        )

    if user.verification_code != verification_data["verification_code"]:    
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code!"
        )

    user.is_verified = True
    await db.commit()
    await db.refresh(user)

    access_token_expires = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    background_tasks.add_task(
        send_email,
        subject="Email Verification Successful",
        body="Your email has been successfully verified.",
        recipients=[user.email],
        html_body=f"<p>Your email has been successfully verified.</p>"
    )

    return access_token, refresh_token

async def record_login_event(user_id: str, db: AsyncSession):
    login_event = UserLogin(user_id=user_id)
    db.add(login_event)
    await db.commit()

async def authenticate_user(email: str, password: str, db: AsyncSession):
    """Attempt to retrieve the user by email and verify the password."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email you provided does not exist!",
        )
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials provided!",
        )
    return user

async def login_user(email: str, password: str, db: AsyncSession):
    """Authenticate a user and return JWT access + refresh tokens if successful."""
    user = await authenticate_user(email, password, db)
    if not user:
        return None
    await record_login_event(user.id, db)
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return user, access_token, refresh_token

def get_google_flow() -> Flow:
    """Creates and returns a Google OAuth2 Flow instance."""
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "project_id": "retgrow-learn",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=[
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid"
        ]
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow

async def generate_google_auth_url() -> str:
    """Generates the Google authorization URL."""
    flow = get_google_flow()
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url

async def handle_google_callback(code: str, db: AsyncSession):
    """
    Exchanges the authorization code for tokens, extracts user info,
    and forwards it to the authentication handler.
    """
    flow = get_google_flow()
    flow.fetch_token(code=code)
    
    credentials = flow.credentials
    if not credentials.id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ID token found in Google response"
        )
        
    try:
        # Verify the ID token and get user info
        user_info = id_token.verify_oauth2_token(
            credentials.id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Google ID Token: {str(e)}"
        )
        
    return await authenticate_google_user(user_info, db)


async def authenticate_google_user(user_info: dict, db: AsyncSession):
    """
    Process the Google user info, find or create the user, 
    and return the user object along with JWT access and refresh tokens.
    """
    email = user_info.get("email")
    first_name = user_info.get("given_name", "")
    last_name = user_info.get("family_name", "")
    avatar_url = user_info.get("picture", None)
    username = email.split('@')[0] if email else "" # Fallback username

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not found in Google Token"
        )

    # Check if a user with this email already exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if user:
        # If user exists but was created via regular sign-up, we still let them log in, 
        # optionally we could link the accounts or update auth_provider.
        if user.auth_provider != AuthProvider.GOOGLE:
            user.auth_provider = AuthProvider.GOOGLE
            await db.commit()
            await db.refresh(user)
    else:
        # User doesn't exist, create a new one instantly verified with Google
        user = User(
            username=f"{username}_{int(datetime.now().timestamp())}",  # Ensure unique username
            email=email,
            first_name=first_name,
            last_name=last_name,
            avatar_url=avatar_url,
            is_verified=True,  # Google emails are already verified
            password_hash=None, # No password
            auth_provider=AuthProvider.GOOGLE
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    await record_login_event(user.id, db)
    
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return user, access_token, refresh_token

async def refresh_access_token(refresh_token_str: str, db: AsyncSession):
    """
    Validate a refresh token and issue a new access + refresh token pair.
    Returns (access_token, refresh_token) or raises HTTPException.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token. Please log in again.",
    )
    try:
        payload = jwt.decode(
            refresh_token_str,
            settings.JWT_REFRESH_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise credentials_exception
    except (DecodeError, jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise credentials_exception

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception

    # Issue new token pair (rotation)
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    new_access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return new_access_token, new_refresh_token

def create_reset_token(email: str, expires_delta: timedelta = None) -> str:
    """Generate a JWT reset token for password recovery."""
    to_encode = {"sub": email}
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=30))
    to_encode.update({"exp": expire})
    reset_token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return reset_token

async def process_forgot_password(email: str, db: AsyncSession, background_tasks: BackgroundTasks) -> bool:
    """
    Process a forgot-password request.
    
    If a user with the provided email exists, generate a reset token and (in a real application)
    send an email containing the reset instructions. This function always returns True so that
    the API does not disclose whether the email exists.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if user:
        # Generate a reset token (this example sets a 30-minute expiration)
        reset_token = create_reset_token(email, expires_delta=timedelta(minutes=30))

        # Prepare the email content
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        subject = "Password Reset Request"
        text_body = f"Click the link below to reset your password:\n{reset_link}"
        html_body = f"""
        <p>Click the link below to reset your password:</p>
        <a href="{reset_link}">Reset Password</a>
        """

        # Send the email
        background_tasks.add_task(send_email, subject, text_body, [email], html_body=html_body)
    
    # Always return True to prevent email enumeration
    return True

async def reset_password(token: str, new_password: str, db: AsyncSession, background_tasks: BackgroundTasks) -> bool:
    """
    Verify the reset token, update the user's password, and return True if successful.
    """
    try:
        # Decode the token. The token should include the email in its "sub" field.
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return False
    except DecodeError:
        return False

    # Look up the user by email.
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        return False

    # Hash the new password and update the user record.
    user.password_hash = hash_password(new_password)
    await db.commit()
    await db.refresh(user)

    # Prepare the email content.
    subject = "Your Password Has Been Reset"
    text_body = (
        "Your password has been successfully reset. "
        "If you did not initiate this reset, please contact support immediately."
    )
    html_body = f"""
    <p>Your password has been successfully reset.</p>
    <p>If you did not initiate this reset, please <a href="{settings.SUPPORT_URL}">contact support</a> immediately.</p>
    """
    # Send the notification email.
    background_tasks.add_task(send_email, subject, text_body, [user.email], html_body=html_body)

    return True

async def change_password(user: User, current_password: str, new_password: str, db: AsyncSession, background_tasks: BackgroundTasks) -> bool:
    """
    Verify the current password, then update the user's password with the new one.
    Returns True if the password was updated, or False if the current password was incorrect.
    """
    if not verify_password(current_password, user.password_hash):
        return False

    user.password_hash = hash_password(new_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)

     # Send password change notification email
    subject = "Your Password Has Been Changed"
    text_body = "Your password has been successfully changed. If you did not perform this action, please contact support immediately."
    html_body = """
    <p>Your password has been successfully changed.</p>
    <p>If you did not perform this action, please <a href="{support_link}">contact support</a> immediately.</p>
    """.format(support_link=settings.SUPPORT_URL)

    background_tasks.add_task(send_email, subject, text_body, [user.email], html_body=html_body)

    return True