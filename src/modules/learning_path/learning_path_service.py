# src/learning_path/learning_path_service.py

from typing import List
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException, status
from src.models.models import LearningPath, UserSkill, TrackCourse

async def get_user_skills(user_id: str, db: AsyncSession) -> List[UserSkill]:
    """
    Return list of UserSkill ORM objects with skill relationship loaded.
    Each result will deserialize to UserSkillResponse (skill + proficiency + last_updated).
    If no rows found, returns an empty list.
    """
    stmt = (
        select(UserSkill)
        .options(selectinload(UserSkill.skill))   # load Skill relationship
        .where(UserSkill.user_id == user_id)
        .order_by(UserSkill.last_updated.desc())
    )
    result = await db.execute(stmt)
    user_skills = result.scalars().all()
    return user_skills or []

async def enroll_in_track(user_id: str, track_id: str, db: AsyncSession):
    """
    Enroll a user in a new track.
    
    - If the user already has an active learning path (i.e. not completed) and it's a different track,
      it is removed (unenrolled).
    - Then a new learning path record is created with the provided track_id.
    """
    # Fetch the first course in the requested track to satisfy the NOT NULL constraint on current_course_id
    stmt_course = select(TrackCourse.course_id).where(TrackCourse.track_id == track_id).order_by(TrackCourse.order.asc()).limit(1)
    res_course = await db.execute(stmt_course)
    first_course_id = res_course.scalars().first()
    
    if not first_course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enroll in this track as it currently has no courses."
        )

    # Query if the user already has a learning path record.
    result = await db.execute(
        select(LearningPath).where(LearningPath.user_id == user_id)
    )
    existing_path = result.scalars().first()
    
    if existing_path:
        # If the user is already enrolled in a track
        if existing_path.completed_at is None:
            # If it's the same track, we simply return the existing record.
            if str(existing_path.track_id) == track_id:
                return existing_path
            else:
                # Unenroll from the current track by deleting the active record.
                await db.delete(existing_path)
                await db.commit()
    
    # Create a new learning path record.
    new_learning_path = LearningPath(
        user_id=user_id,
        track_id=track_id,
        progress=0.0,
        current_course_id=first_course_id,
        completed_at=None
    )
    db.add(new_learning_path)
    await db.commit()
    await db.refresh(new_learning_path)
    return new_learning_path