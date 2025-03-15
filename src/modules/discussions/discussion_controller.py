# src/discussions/discussion_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.modules.discussions import discussion_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user  # Assumes this dependency is implemented
from src.models.models import User

router = APIRouter(prefix="/courses", tags=["discussions"])

# GET /courses/{courseId}/discussions – Retrieve all discussions for a course.
@router.get("/{courseId}/discussions", response_model=List[schemas.DiscussionResponse])
async def get_discussions(
    courseId: str,
    db: AsyncSession = Depends(get_db_session)
):
    discussions = await discussion_service.get_discussions_by_course(courseId, db)
    return discussions

# POST /courses/{courseId}/discussions – Create a new discussion.
@router.post("/{courseId}/discussions", response_model=schemas.DiscussionResponse)
async def create_discussion(
    courseId: str,
    discussion: schemas.DiscussionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    new_discussion = await discussion_service.create_discussion(courseId, discussion.model_dump(), current_user, db)
    if not new_discussion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create discussion."
        )
    return new_discussion

# POST /courses/{courseId}/discussions/{discussionId}/replies – Create a new reply.
@router.post("/{courseId}/discussions/{discussionId}/replies", response_model=schemas.DiscussionReplyResponse)
async def create_discussion_reply(
    courseId: str,
    discussionId: str,
    reply: schemas.DiscussionReplyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    new_reply = await discussion_service.create_discussion_reply(courseId, discussionId, reply.model_dump(), current_user, db)
    if not new_reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found or does not belong to the specified course."
        )
    return new_reply
