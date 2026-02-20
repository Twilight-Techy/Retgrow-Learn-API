# src/search/search_service.py

import asyncio
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

async def _search_courses(pattern: str, db: AsyncSession) -> List[SearchResultItem]:
    stmt = select(Course).where(or_(Course.title.ilike(pattern), Course.description.ilike(pattern)))
    result = await db.execute(stmt)
    return [format_course(c) for c in result.scalars().all()]

async def _search_tracks(pattern: str, db: AsyncSession) -> List[SearchResultItem]:
    stmt = select(Track).where(or_(Track.title.ilike(pattern), Track.description.ilike(pattern)))
    result = await db.execute(stmt)
    return [format_track(t) for t in result.scalars().all()]

async def _search_resources(pattern: str, db: AsyncSession) -> List[SearchResultItem]:
    stmt = select(Resource).where(or_(Resource.title.ilike(pattern), Resource.description.ilike(pattern)))
    result = await db.execute(stmt)
    return [format_resource(r) for r in result.scalars().all()]

async def search(query: str, db: AsyncSession) -> SearchResponse:
    pattern = f"%{query}%"

    # Run all 3 search queries concurrently
    courses, tracks, resources = await asyncio.gather(
        _search_courses(pattern, db),
        _search_tracks(pattern, db),
        _search_resources(pattern, db),
    )

    return SearchResponse(
        courses=courses,
        tracks=tracks,
        resources=resources
    )

