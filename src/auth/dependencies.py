# src/auth/dependencies.py
import logging

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jwt.exceptions import DecodeError
import jwt

from src.common.config import settings
from src.common.database.database import get_db_session
from src.models.models import User

logger = logging.getLogger(__name__)


bearer_scheme = HTTPBearer(auto_error=False)
cookie_scheme = APIKeyCookie(name="access_token", auto_error=False)

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    cookie_token: str = Depends(cookie_scheme),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Dependency to retrieve the current user based on the JWT token provided in the Authorization header.
    """
    logger.info(f"Authenticating request. Path: {request.url.path}")
    
    token = None
    if credentials:
        token = credentials.credentials
        logger.debug("Found token in Authorization header")
    elif cookie_token:
        token = cookie_token
        logger.debug("Found token in access_token cookie")
    
    if not token:
        logger.warning(f"No authentication token found for path: {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except DecodeError:
        raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
    except Exception as e:
        raise credentials_exception from e

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user
