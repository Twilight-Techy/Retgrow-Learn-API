# common/utils/global_functions.py
from typing import Any, Dict, Union
from fastapi import HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.models import User, UserRole

def resPayloadData(
    code: int,
    error: bool,
    message: str,
    total_count: int | None = None,
    data: Union[dict, list, str, None] = None,
    res: Response = None
) -> Dict[str, Any]:
    """
    Constructs a standardized response payload.

    Args:
        code (int): The HTTP status code.
        error (bool): Indicates if the response represents an error.
        message (str): A message associated with the response.
        total_count (int | None, optional): The total count of items, if applicable.
        data (Union[dict, list, str, None], optional): The response data.
        res (Response, optional): An optional FastAPI Response object to update its status code.

    Returns:
        Dict[str, Any]: A dictionary containing the structured response.

    If error is True, the provided message will be assigned to errorMessage and the message field will be set to None. 
    Conversely, if error is False, message is assigned to the message field and errorMessage is None.
    """
    response_data = {
        "statusCode": code,
        "message": None if error else message or None,
        "errorMessage": message if error else None,
        "totalCount": total_count,
        "data": data
    }

    # Special handling when data is an object with only one key 'message'
    if data and isinstance(data, dict) and 'message' in data and len(data) == 1:
        response_data = {
            "statusCode": code,
            "message": data.get('message'),
            "errorMessage": None,
            "totalCount": None,
            "data": None
        }

    if res:
        res.status_code = code

    return response_data

async def award_xp(user: User, db: AsyncSession, amount: int = 5):
    user.xp += amount
    db.add(user)
    await db.commit()
    await db.refresh(user)

def ensure_instructor_or_admin(current_user: User):
    if current_user.role not in [UserRole.TUTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action."
        )
    return current_user