# src/auth/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jwt.exceptions import DecodeError
import jwt

from src.common.config import settings
from src.common.database.database import get_db_session
from src.models.models import User

bearer_scheme = HTTPBearer()

async def get_current_user(
    token: str = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Dependency to retrieve the current user based on the JWT token provided in the Authorization header.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except DecodeError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user
