# src/tracks/track_controller.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.common.utils.global_functions import ensure_instructor_or_admin
from src.models.models import User
from src.modules.tracks import track_service, schemas
from src.common.database.database import get_db_session

router = APIRouter(prefix="/tracks", tags=["tracks"])

@router.get("", response_model=List[schemas.TrackResponse])
async def get_tracks(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve all tracks with optional search filtering and pagination.
    
    Query Parameters:
      - **q**: Optional search query to filter tracks by title or description.
      - **skip**: Number of records to skip.
      - **limit**: Maximum number of records to return.
    """
    tracks = await track_service.get_all_tracks(db, q, skip, limit)
    return tracks

@router.get("/popular", response_model=List[schemas.TrackResponse])
async def get_popular_tracks(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the top 3 popular tracks based on the number of enrollments.
    """
    popular_tracks = await track_service.get_popular_tracks(db, limit=3)
    if not popular_tracks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No popular tracks found."
        )
    return popular_tracks

@router.get("/{slug}", response_model=schemas.TrackResponse)
async def get_track(slug: str, db: AsyncSession = Depends(get_db_session)):
    """
    Retrieve a track by its slug.
    """
    track = await track_service.get_track_by_slug(slug, db)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found"
        )
    return track

@router.post("", response_model=schemas.TrackResponse)
async def create_track(
    track_request: schemas.TrackCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    track_data = track_request.model_dump()
    new_track = await track_service.create_track(track_data, db)
    if not new_track:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create track."
        )
    return new_track

@router.put("/{slug}", response_model=schemas.TrackResponse)
async def update_track(
    slug: str,
    track_request: schemas.TrackUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    track_data = track_request.model_dump()
    updated_track = await track_service.update_track(slug, track_data, db)
    if not updated_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found."
        )
    return updated_track

@router.delete("/{slug}", response_model=dict)
async def delete_track(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    success = await track_service.delete_track(slug, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found."
        )
    return {"message": "Track deleted successfully."}

@router.get("/{slug}/curriculum", response_model=schemas.TrackCurriculumResponse)
async def get_track_curriculum(
    slug: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the curriculum for the track identified by its slug.
    Returns track details including prerequisites and the curriculum:
    an ordered list of courses with their modules.
    """
    curriculum = await track_service.get_track_curriculum(slug, db)
    if not curriculum:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track or curriculum not found."
        )
    return curriculum

@router.put("/{slug}/courses", response_model=schemas.TrackResponse)
async def update_track_courses(
    slug: str,
    course_updates: schemas.UpdateTrackCoursesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update the courses in a track. This endpoint allows:
    - Adding new courses to the track
    - Removing courses from the track
    - Reordering existing courses
    Only instructors and admins can modify track courses.
    """
    ensure_instructor_or_admin(current_user)
    
    updated_track = await track_service.update_track_courses(
        slug, 
        [course.model_dump() for course in course_updates.courses], 
        db
    )
    
    if not updated_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found"
        )
    return updated_track