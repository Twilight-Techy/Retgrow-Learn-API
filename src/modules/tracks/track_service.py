# src/tracks/track_service.py

from typing import List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.models import LearningPath, Lesson, Module, Track, TrackCourse

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
    Returns a list of courses for the given track slug. Each course contains modules
    and each module contains ordered lessons. Matches CurriculumCourseResponse schema.
    """
    # Find the track
    track_result = await db.execute(select(Track).where(Track.slug == slug))
    track = track_result.scalars().first()
    if not track:
        return []

    # Eager-load `course` for every TrackCourse to avoid lazy-load at access time
    tc_stmt = (
        select(TrackCourse)
        .where(TrackCourse.track_id == track.id)
        .order_by(TrackCourse.order.asc())
        .options(selectinload(TrackCourse.course))
    )
    tc_result = await db.execute(tc_stmt)
    track_course_records = tc_result.scalars().all()

    curriculum = []
    for tc in track_course_records:
        course = tc.course  # now already loaded, no lazy-load

        # Fetch modules for this course (ordered)
        module_stmt = (
            select(Module)
            .where(Module.course_id == course.id)
            .order_by(Module.order.asc())
        )
        module_result = await db.execute(module_stmt)
        modules = module_result.scalars().all()

        modules_out = []
        for module in modules:
            # Fetch lessons for module (ordered)
            lesson_stmt = (
                select(Lesson)
                .where(Lesson.module_id == module.id)
                .order_by(Lesson.order.asc())
            )
            lesson_result = await db.execute(lesson_stmt)
            lessons = lesson_result.scalars().all()

            modules_out.append({
                "id": str(module.id),
                "title": module.title,
                "description": getattr(module, "description", None),
                "order": module.order,
                "lessons": [
                    {"id": str(lesson.id), "title": lesson.title, "order": lesson.order}
                    for lesson in lessons
                ],
            })

        curriculum.append({
            "id": str(course.id),
            "title": course.title,
            "description": course.description,
            "order": tc.order,
            "modules": modules_out,
        })

    return curriculum

async def get_popular_tracks(db: AsyncSession, limit: int = 3) -> List[Track]:
    """
    Retrieve the top 'limit' popular tracks, determined by the number of LearningPath records
    (enrollments) for each track. If fewer than 'limit' tracks are found,
    the remaining spots are filled with the most recently created tracks.
    """
    # 1. Get the popular tracks
    stmt_popular = (
        select(Track, func.count(LearningPath.user_id).label("popularity"))
        .join(LearningPath, LearningPath.track_id == Track.id)
        .group_by(Track.id)
        .order_by(func.count(LearningPath.user_id).desc())
        .limit(limit)
    )
    result_popular = await db.execute(stmt_popular)
    popular_tracks = [row[0] for row in result_popular.all()]

    # 2. Check if we have enough tracks
    if len(popular_tracks) < limit:
        # Calculate how many more tracks we need
        needed = limit - len(popular_tracks)
        
        # Get the IDs of the popular tracks to exclude them from the new query
        popular_track_ids = [track.id for track in popular_tracks]
        
        # Query for the most recently created tracks that are not already in our list
        stmt_recent = (
            select(Track)
            .where(Track.id.notin_(popular_track_ids))
            .order_by(Track.created_at.desc())
            .limit(needed)
        )
        result_recent = await db.execute(stmt_recent)
        recent_tracks = result_recent.scalars().all()
        
        # 3. Combine the lists
        popular_tracks.extend(recent_tracks)

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