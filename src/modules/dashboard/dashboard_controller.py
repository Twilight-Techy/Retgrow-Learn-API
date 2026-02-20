# src/dashboard/dashboard_controller.py

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from src.modules.dashboard import dashboard_service, schemas
from src.modules.certificates import certificate_service
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user  # Assumes this is implemented
from src.models.models import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# GET /dashboard/all – Single aggregated endpoint for the entire dashboard page.
@router.get("/all", response_model=schemas.AggregatedDashboardResponse)
async def get_all_dashboard_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Returns all dashboard data in a single response.
    Runs all queries concurrently using asyncio.gather().
    """
    user_id = str(current_user.id)

    # Run dashboard data + certificates in parallel
    dashboard_data, certs = await asyncio.gather(
        dashboard_service.get_all_dashboard_data(user_id, db),
        certificate_service.get_user_certificates(current_user.id, db),
    )

    # Format certificates
    dashboard_data["certificates"] = [
        {
            "id": str(c.id),
            "course_id": str(c.course_id),
            "course_title": c.course.title if c.course else "Unknown Course",
            "certificate_url": c.certificate_url,
            "issued_at": c.issued_at,
        }
        for c in certs
    ]

    return dashboard_data

# GET /dashboard/enrolled-courses – List enrolled courses.
@router.get("/enrolled-courses", response_model=List[schemas.EnrolledCourseResponse])
async def get_enrolled_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    courses = await dashboard_service.get_enrolled_courses(str(current_user.id), db)
    return courses

# GET /dashboard/recent-resources – List recent resources.
@router.get("/recent-resources", response_model=List[schemas.RecentResourceResponse])
async def get_recent_resources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 5
):
    resources = await dashboard_service.get_recent_resources(str(current_user.id), db, limit=limit)
    return resources

# GET /dashboard/upcoming-deadlines – List upcoming deadlines.
@router.get("/upcoming-deadlines", response_model=List[schemas.DeadlineResponse])
async def get_upcoming_deadlines(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 10
):
    deadlines = await dashboard_service.get_upcoming_deadlines(str(current_user.id), db, limit=limit)
    return deadlines

@router.get("/recent-achievements", response_model=List[schemas.RecentAchievementResponse])
async def get_recent_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 3
):
    """
    Retrieve the most recent achievements awarded to the current user.
    """
    recent_achievements = await dashboard_service.get_recent_achievements(str(current_user.id), db, limit=limit)
    return recent_achievements

@router.get("/progress-overview", response_model=List[schemas.ProgressOverviewItem])
async def progress_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Returns a progress overview for the user's currently enrolled courses.
    Example response:
    [
      { "name": "Completed", "value": 60 },
      { "name": "In Progress", "value": 30 },
      { "name": "Not Started", "value": 10 },
    ]
    """
    overview = await dashboard_service.get_progress_overview(str(current_user.id), db)
    return overview

@router.get("/recommended-courses", response_model=List[schemas.CourseResponse])
async def get_recommended_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve recommended courses for the current user based on their active track.
    Only courses in the user's current track that they are not already enrolled in will be returned,
    sorted by the track-specific order.
    """
    recommended_courses = await dashboard_service.get_recommended_courses(str(current_user.id), db)
    return recommended_courses

@router.get("/learning-path", response_model=Optional[schemas.LearningPathResponse])
async def get_learning_path(
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user),
    limit: Optional[int] = Query(None, alias="limit"),
):
    """
    Return the user's active learning path (or null if none).
    Optional query param `limit` controls how many courses are returned (no limit when omitted).
    """
    user_id = str(current_user.id)
    lp = await dashboard_service.get_active_learning_path(user_id, db, course_limit=limit)
    if lp is None:
        return None
    return lp