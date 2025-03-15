# src/auth/auth_service.py

from datetime import datetime, timedelta, timezone
import jwt
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jwt.exceptions import JWTDecodeError

from src.common.config import settings
from src.models.models import User, UserLogin

# Initialize the password context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that the provided password matches the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT token including an expiration date."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

async def create_user(user_data: dict, db: AsyncSession):
    # Check if user with provided email already exists
    result = await db.execute(select(User).where(User.email == user_data["email"]))
    existing_user = result.scalars().first()
    if existing_user:
        return None  # Alternatively, you might raise an exception

    # Create a new User instance
    new_user = User(
        username=user_data["username"],
        email=user_data["email"],
        password_hash=hash_password(user_data["password"]),
        first_name=user_data["first_name"],
        last_name=user_data["last_name"],
        role="student"  # Default role, adjust as necessary
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def signup_user(user_data: dict, db: AsyncSession) -> str:
    new_user = await create_user(user_data, db)
    if not new_user:
        return None
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    access_token = create_access_token(data={"sub": str(new_user.id)}, expires_delta=access_token_expires)
    return access_token

async def record_login_event(user_id: str, db: AsyncSession):
    login_event = UserLogin(user_id=user_id)
    db.add(login_event)
    await db.commit()

async def authenticate_user(email: str, password: str, db: AsyncSession):
    """Attempt to retrieve the user by email and verify the password."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

async def login_user(email: str, password: str, db: AsyncSession) -> str:
    """Authenticate a user and return a JWT access token if successful."""
    user = await authenticate_user(email, password, db)
    if not user:
        return None
    record_login_event(user.id)
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    return user, access_token

def create_reset_token(email: str, expires_delta: timedelta = None) -> str:
    """Generate a JWT reset token for password recovery."""
    to_encode = {"sub": email}
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=30))
    to_encode.update({"exp": expire})
    reset_token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return reset_token

async def process_forgot_password(email: str, db: AsyncSession) -> bool:
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
        # Here you would normally call your email service to send the reset email.
        # For demonstration purposes, we simply print the reset token.
        print(f"Password reset token for {email}: {reset_token}")
    
    # Always return True to prevent email enumeration
    return True

async def reset_password(token: str, new_password: str, db: AsyncSession) -> bool:
    """
    Verify the reset token, update the user's password, and return True if successful.
    """
    try:
        # Decode the token. The token should include the email in its "sub" field.
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return False
    except JWTDecodeError:
        return False

    # Look up the user by email.
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        return False

    # Hash the new password and update the user record.
    user.password_hash = hash_password(new_password)
    await db.commit()
    return True

async def change_password(user: User, current_password: str, new_password: str, db: AsyncSession) -> bool:
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
    return True