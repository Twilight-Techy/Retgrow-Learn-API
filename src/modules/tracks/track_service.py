# src/tracks/track_service.py

from typing import List, Optional
import uuid
from sqlalchemy import or_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.models import Module, Track, TrackCourse

async def get_all_tracks(
    db: AsyncSession, 
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 10
) -> List[Track]:
    """
    Retrieve all tracks from the database with optional search filtering and pagination.
    
    Args:
        db (AsyncSession): The database session.
        q (Optional[str]): Optional search query to filter tracks by title or description.
        skip (int): Number of records to skip (for pagination).
        limit (int): Maximum number of records to return.
        
    Returns:
        List[Track]: A list of tracks matching the criteria.
    """
    if q:
        query = select(Track).where(
            or_(
                Track.title.ilike(f"%{q}%"),
                Track.description.ilike(f"%{q}%")
            )
        ).offset(skip).limit(limit)
    else:
        query = select(Track).offset(skip).limit(limit)
    
    result = await db.execute(query)
    tracks = result.scalars().all()
    return tracks

async def get_track_by_slug(slug: str, db: AsyncSession) -> Optional[Track]:
    """
    Retrieve a track by its slug.
    """
    result = await db.execute(select(Track).where(Track.slug == slug))
    track = result.scalars().first()
    return track

async def create_track(track_data: dict, db: AsyncSession) -> Track:
    new_track = Track(
        id=uuid.uuid4(),  # Include if your model does not auto-generate the id.
        slug=track_data["slug"],
        title=track_data["title"],
        description=track_data.get("description"),
        image_url=track_data.get("image_url"),
        level=track_data["level"],
        duration=track_data.get("duration"),
        prerequisites=track_data.get("prerequisites") or []
    )
    db.add(new_track)
    await db.commit()
    await db.refresh(new_track)
    return new_track

async def update_track(slug: str, track_data: dict, db: AsyncSession) -> Optional[Track]:
    result = await db.execute(select(Track).where(Track.slug == slug))
    track = result.scalars().first()
    if not track:
        return None
    for key, value in track_data.items():
        if value is not None:
            setattr(track, key, value)
    db.add(track)
    await db.commit()
    await db.refresh(track)
    return track

async def delete_track(slug: str, db: AsyncSession) -> bool:
    result = await db.execute(select(Track).where(Track.slug == slug))
    track = result.scalars().first()
    if not track:
        return False
    await db.delete(track)
    await db.commit()
    return True

async def get_track_curriculum(slug: str, db: AsyncSession) -> List[dict]:
    """
    Retrieve the curriculum for the track identified by the given slug.
    Returns a list of dictionaries with course details, order, and their respective modules.
    """
    # Find the track by its slug.
    track_result = await db.execute(select(Track).where(Track.slug == slug))
    track = track_result.scalars().first()
    if not track:
        return []

    # Retrieve track courses ordered by the `order` field.
    stmt = (
        select(TrackCourse)
        .where(TrackCourse.track_id == track.id)
        .order_by(TrackCourse.order.asc())
    )
    result = await db.execute(stmt)
    track_course_records = result.scalars().all()

    curriculum = []
    for track_course in track_course_records:
        course = track_course.course  # Assuming a relationship exists in TrackCourse model

        # Fetch all modules for this course, ordered by position
        module_stmt = (
            select(Module)
            .where(Module.course_id == course.id)
            .order_by(Module.order.asc())
        )
        module_result = await db.execute(module_stmt)
        modules = module_result.scalars().all()

        curriculum.append({
            "id": str(course.id),
            "title": course.title,
            "description": course.description,
            "order": track_course.order,
            "modules": [
                {
                    "id": str(module.id),
                    "title": module.title,
                    "description": module.description,
                    "order": module.order
                }
                for module in modules
            ]
        })

    return curriculum
