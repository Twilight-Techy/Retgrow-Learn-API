# src/discussions/discussion_service.py

from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_

from src.models.models import Discussion, DiscussionReply, User

async def get_discussions_by_course(course_id: str, db: AsyncSession) -> List[Discussion]:
    """
    Retrieve all discussions for a given course.
    """
    stmt = select(Discussion).where(Discussion.course_id == course_id).order_by(Discussion.created_at.desc())
    result = await db.execute(stmt)
    discussions = result.scalars().all()
    return discussions

async def create_discussion(course_id: str, discussion_data: dict, current_user: User, db: AsyncSession) -> Discussion:
    """
    Create a new discussion for the given course by the current user.
    """
    new_discussion = Discussion(
        course_id=course_id,
        user_id=current_user.id,
        title=discussion_data["title"],
        content=discussion_data["content"]
    )
    db.add(new_discussion)
    await db.commit()
    await db.refresh(new_discussion)
    return new_discussion

async def create_discussion_reply(course_id: str, discussion_id: str, reply_data: dict, current_user: User, db: AsyncSession) -> Optional[DiscussionReply]:
    """
    Create a new reply for a discussion.
    
    Verifies that the discussion exists and belongs to the given course.
    """
    # Verify that the discussion exists and is associated with the given course.
    stmt = select(Discussion).where(and_(Discussion.id == discussion_id, Discussion.course_id == course_id))
    result = await db.execute(stmt)
    discussion = result.scalars().first()
    if not discussion:
        return None

    new_reply = DiscussionReply(
        discussion_id=discussion_id,
        user_id=current_user.id,
        content=reply_data["content"]
    )
    db.add(new_reply)
    await db.commit()
    await db.refresh(new_reply)
    return new_reply
