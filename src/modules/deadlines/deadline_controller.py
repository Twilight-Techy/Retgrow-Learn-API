# src/instructor/course_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.utils.global_functions import ensure_instructor_or_admin
from src.modules.deadlines import deadline_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user
from src.models.models import User

router = APIRouter(prefix="/deadlines", tags=["deadlines"])

@router.post("", response_model=schemas.DeadlineResponse)
async def create_deadline(
    deadline_request: schemas.DeadlineCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new upcoming deadline.
    This endpoint is restricted to users with the 'instructor' or 'admin' role.
    """
    ensure_instructor_or_admin(current_user)
    # Use model_dump() (Pydantic v2) instead of dict()
    deadline_data = deadline_request.model_dump()
    new_deadline = await deadline_service.create_deadline(deadline_data, db)
    if not new_deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create deadline."
        )
    return new_deadline