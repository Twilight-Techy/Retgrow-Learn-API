# src/learning_path/learning_path_service.py

from typing import Optional, List
import uuid
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.models import LearningPath, UserSkill

async def get_learning_path(user_id: str, db: AsyncSession) -> Optional[LearningPath]:
    """
    Retrieve the learning path for the given user.
    """
    result = await db.execute(select(LearningPath).where(LearningPath.user_id == user_id))
    learning_path = result.scalars().first()
    return learning_path

async def get_user_skills(user_id: str, db: AsyncSession) -> List[UserSkill]:
    """
    Retrieve all user skills for the given user.
    """
    result = await db.execute(select(UserSkill).where(UserSkill.user_id == user_id))
    user_skills = result.scalars().all()
    return user_skills

async def enroll_in_track(user_id: str, track_id: str, db: AsyncSession):
    """
    Enroll a user in a new track.
    
    - If the user already has an active learning path (i.e. not completed) and it's a different track,
      it is removed (unenrolled).
    - Then a new learning path record is created with the provided track_id.
    """
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
        current_course_id=None,
        completed_at=None
    )
    db.add(new_learning_path)
    await db.commit()
    await db.refresh(new_learning_path)
    return new_learning_path