# src/search/search_service.py

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from src.modules.search.schemas import SearchResultItem, SearchResponse

# Import models (assumed to be defined already)
from src.models.models import Course, Track, Resource

def format_course(course: Course) -> SearchResultItem:
    return SearchResultItem(
        id=str(course.id),
        type="course",
        title=course.title,
        description=course.description
    )

def format_track(track: Track) -> SearchResultItem:
    return SearchResultItem(
        id=str(track.id),
        type="track",
        title=track.title,
        description=track.description
    )

def format_resource(resource: Resource) -> SearchResultItem:
    return SearchResultItem(
        id=str(resource.id),
        type="resource",
        title=resource.title,
        description=resource.description
    )

async def search(query: str, db: AsyncSession) -> SearchResponse:
    pattern = f"%{query}%"
    
    # Search courses by title or description.
    course_stmt = select(Course).where(
        or_(Course.title.ilike(pattern), Course.description.ilike(pattern))
    )
    course_result = await db.execute(course_stmt)
    courses = course_result.scalars().all()
    formatted_courses = [format_course(course) for course in courses]
    
    # Search tracks by title or description.
    track_stmt = select(Track).where(
        or_(Track.title.ilike(pattern), Track.description.ilike(pattern))
    )
    track_result = await db.execute(track_stmt)
    tracks = track_result.scalars().all()
    formatted_tracks = [format_track(track) for track in tracks]
    
    # Search resources by title or description.
    resource_stmt = select(Resource).where(
        or_(Resource.title.ilike(pattern), Resource.description.ilike(pattern))
    )
    resource_result = await db.execute(resource_stmt)
    resources = resource_result.scalars().all()
    formatted_resources = [format_resource(resource) for resource in resources]
    
    return SearchResponse(
        courses=formatted_courses,
        tracks=formatted_tracks,
        resources=formatted_resources
    )
