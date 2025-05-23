# src/tracks/track_service.py

from typing import List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.models import LearningPath, Module, Track, TrackCourse

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
    existing_track = await get_track_by_slug(track_data["slug"], db)
    if existing_track:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Track with this slug already exists."  
        ) 
    
    new_track = Track(
        id=uuid.uuid4(),  # Include if your model does not auto-generate the id.
        slug=track_data["slug"],
        title=track_data["title"],
        description=track_data["description"],
        image_url=track_data["image_url"],
        level=track_data["level"],
        duration=track_data["duration"],
        prerequisites=track_data["prerequisites"] or []
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

async def get_popular_tracks(db: AsyncSession, limit: int = 3) -> List[Track]:
    """
    Retrieve the top 'limit' popular tracks, determined by the number of LearningPath records
    (enrollments) for each track.
    """
    stmt = (
        select(Track, func.count(LearningPath.user_id).label("popularity"))
        .join(LearningPath, LearningPath.track_id == Track.id)
        .group_by(Track.id)
        .order_by(func.count(LearningPath.user_id).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    # Each row is a tuple (Track, popularity). We only need the Track instance.
    popular_tracks = [row[0] for row in result.all()]
    return popular_tracks

async def update_track_courses(slug: str, course_updates: List[dict], db: AsyncSession) -> Optional[Track]:
    """
    Update the courses in a track. This will:
    1. Find existing track-course relationships
    2. Update orders for existing courses
    3. Add new courses
    4. Remove courses not in the update list
    """
    # Find the track
    result = await db.execute(select(Track).where(Track.slug == slug))
    track = result.scalars().first()
    if not track:
        return None

    # Get existing track-course relationships
    stmt = select(TrackCourse).where(TrackCourse.track_id == track.id)
    result = await db.execute(stmt)
    existing_track_courses = {str(tc.course_id): tc for tc in result.scalars().all()}
    
    # Keep track of processed course IDs to identify which ones to remove
    processed_course_ids = set()

    # Update existing courses and add new ones
    for course_data in course_updates:
        course_id = str(course_data["course_id"])
        processed_course_ids.add(course_id)

        if course_id in existing_track_courses:
            # Update existing track-course relationship
            track_course = existing_track_courses[course_id]
            track_course.order = course_data["order"]
            db.add(track_course)
        else:
            # Create new track-course relationship
            new_track_course = TrackCourse(
                track_id=track.id,
                course_id=course_data["course_id"],
                order=course_data["order"]
            )
            db.add(new_track_course)

    # Remove courses that weren't in the update
    for course_id, track_course in existing_track_courses.items():
        if course_id not in processed_course_ids:
            await db.delete(track_course)

    await db.commit()
    await db.refresh(track)
    return track