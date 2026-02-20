# src/dashboard/dashboard_service.py

import asyncio

from typing import Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from src.models.models import LearningPath, TrackCourse, UserAchievement, UserCourse, Course, UserResource, Resource, Deadline

async def get_enrolled_courses(user_id: str, db: AsyncSession) -> List[dict]:
    """
    Retrieve enrolled courses for a user with their progress.
    Returns a list of dicts: { id, title, progress } matching EnrolledCourseResponse.
    """
    # join UserCourse to Course and pull progress
    stmt = (
        select(Course, UserCourse.progress)
        .join(UserCourse, UserCourse.course_id == Course.id)
        .where(UserCourse.user_id == user_id)
        .order_by(func.coalesce(UserCourse.progress, 0).desc())
    )

    result = await db.execute(stmt)
    rows = result.all()  # returns list of (Course, progress)

    courses: List[dict] = []
    for course, progress in rows:
        courses.append({
            "id": course.id,
            "title": course.title,
            # ensure float (and clamp if you want)
            "progress": float(progress or 0.0)
        })

    return courses

# Service function to get recent resources for a user.
async def get_recent_resources(user_id: str, db: AsyncSession, limit: int = 5) -> list:
    """
    Return recent resources accessed by user.
    ORM objects are returned directly — Pydantic's model_validator handles serialization.
    """
    stmt = (
        select(Resource)
        .join(UserResource, UserResource.resource_id == Resource.id)
        .options(joinedload(Resource.track))
        .where(UserResource.user_id == user_id)
        .order_by(UserResource.last_accessed.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().unique().all()

# Service function to get upcoming deadlines.
async def get_upcoming_deadlines(user_id: str, db: AsyncSession, limit: int = 10, enrolled_courses: Optional[List[dict]] = None) -> List[dict]:
    """
    Retrieve deadlines for the user's enrolled courses.
    Includes deadlines in the past (marked as is_overdue=True) and future.
    Results are ordered by due_date ascending (earliest first).

    Args:
        enrolled_courses: If provided, skips the extra DB query to fetch them.
    """
    if enrolled_courses is None:
        enrolled_courses = await get_enrolled_courses(user_id, db)

    # Build course_ids robustly for both dicts and ORM objects
    course_ids = []
    for c in enrolled_courses:
        if isinstance(c, dict):
            course_ids.append(c.get("id"))
        else:
            course_ids.append(getattr(c, "id", None))
    course_ids = [cid for cid in course_ids if cid]

    if not course_ids:
        return []


    stmt = (
        select(Deadline)
        .options(selectinload(Deadline.course))
        .where(Deadline.course_id.in_(course_ids))
        .order_by(Deadline.due_date.asc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    return result.scalars().all()


async def get_recent_achievements(user_id: str, db: AsyncSession, limit: int = 5) -> list:
    """
    Query the UserAchievement table for the specified user,
    ordered by earned_at descending, and return the top achievements.
    ORM objects are returned — Pydantic's model_validator flattens Achievement data.
    """
    stmt = (
        select(UserAchievement)
        .where(UserAchievement.user_id == user_id)
        .options(selectinload(UserAchievement.achievement))
        .order_by(UserAchievement.earned_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_progress_overview(user_id: str, db: AsyncSession, limit: int = 0) -> List[dict]:
    """
    Calculate progress overview for the user's enrolled courses:
     - "Completed": progress >= 100
     - "Not Started": progress <= 0
     - "In Progress": 0 < progress < 100
    Returns integer percentages that sum to 100.
    """
    result = await db.execute(select(UserCourse).where(UserCourse.user_id == user_id))
    courses = result.scalars().all()
    total = len(courses)

    if total == 0:
        return [
            {"name": "Completed", "value": 0},
            {"name": "In Progress", "value": 0},
            {"name": "Not Started", "value": 0},
        ]

    completed = sum(1 for c in courses if (c.progress or 0) >= 100)
    not_started = sum(1 for c in courses if (c.progress or 0) <= 0)
    in_progress = total - completed - not_started

    # Compute exact floats then integer percentages with rounding while ensuring sum == 100
    def pct(count: int) -> float:
        return (count / total) * 100.0

    completed_f = pct(completed)
    in_progress_f = pct(in_progress)
    not_started_f = pct(not_started)

    # Round the first two and compute last as remainder to guarantee sum==100
    completed_pct = round(completed_f)
    in_progress_pct = round(in_progress_f)
    not_started_pct = 100 - (completed_pct + in_progress_pct)

    # Edge-case guard: if rounding makes last negative (rare), clamp and adjust
    if not_started_pct < 0:
        # push negative into in_progress (or completed) proportionally — simple fallback:
        not_started_pct = 0
        # recompute in_progress_pct so sum = 100
        in_progress_pct = 100 - completed_pct

    return [
        {"name": "Completed", "value": completed_pct},
        {"name": "In Progress", "value": in_progress_pct},
        {"name": "Not Started", "value": not_started_pct},
    ]

async def get_recommended_courses(user_id: str, db: AsyncSession) -> List[Dict]:
    """
    Returns recommended courses for the user based on their current track enrollment.
    The logic:
      1. Retrieve the user's active learning path (completed_at is null).
      2. Retrieve all courses for that track from the TrackCourse association (with order).
      3. Retrieve courses the user is already enrolled in from UserCourse.
      4. Exclude already enrolled courses and return the remaining ones, sorted by TrackCourse.order.
    """
   # 1) Active learning path
    lp_result = await db.execute(
        select(LearningPath).where(
            LearningPath.user_id == user_id,
            LearningPath.completed_at.is_(None)
        )
    )
    learning_path = lp_result.scalars().first()
    if not learning_path:
        return []

    track_id = learning_path.track_id

    # 2) Collect enrolled course ids and track courses in parallel (independent queries)
    uc_stmt = select(UserCourse.course_id).where(UserCourse.user_id == user_id)
    tc_stmt = (
        select(Course)
        .join(TrackCourse, TrackCourse.course_id == Course.id)
        .where(TrackCourse.track_id == track_id)
        .order_by(TrackCourse.order.asc())
    )

    uc_result, tc_result = await asyncio.gather(
        db.execute(uc_stmt),
        db.execute(tc_stmt),
    )

    enrolled_course_ids = set(uc_result.scalars().all())
    courses_in_track = tc_result.scalars().all()

    # 4) Build response list of dicts (filter out enrolled)
    recommended = []
    for c in courses_in_track:
        if c.id in enrolled_course_ids:
            continue

        # Ensure you convert numeric/enum types to python types Pydantic likes.
        # Pydantic will accept strings for enum fields too (it will coerce) but
        # it's fine to pass the enum instance if course.level is an enum.
        recommended.append({
            "id": c.id,
            "track_id": track_id,
            "title": c.title,
            "description": c.description,
            "image_url": c.image_url,
            "level": getattr(c, "level", None),  # enum instance or string; Pydantic will coerce
            "duration": c.duration,
            "price": float(c.price) if c.price is not None else 0.0,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        })

    return recommended

async def get_active_learning_path(user_id: str, db: AsyncSession, course_limit: Optional[int] = None) -> Optional[dict]:
    """
    Return active learning path for the user (completed_at IS NULL).
    Includes: learning path metadata, track brief, and courses ordered by TrackCourse.order.
    If course_limit is None => return all courses for the track.
    """
    lp_stmt = (
        select(LearningPath)
        .where(LearningPath.user_id == user_id, LearningPath.completed_at.is_(None))
        .options(selectinload(LearningPath.track))
    )
    lp_res = await db.execute(lp_stmt)
    lp = lp_res.scalars().first()
    if not lp:
        return None

    # Build the base statement for TrackCourse -> Course (ordered)
    tc_stmt = (
        select(TrackCourse, Course)
        .join(Course, TrackCourse.course_id == Course.id)
        .where(TrackCourse.track_id == lp.track_id)
        .order_by(TrackCourse.order.asc())
    )

    if course_limit is not None:
        tc_stmt = tc_stmt.limit(course_limit)

    tc_res = await db.execute(tc_stmt)
    rows = tc_res.all()  # list of (TrackCourse, Course)

    courses = []
    for _, course in rows:
        courses.append({
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "image_url": getattr(course, "image_url", None)
        })

    resp = {
        "id": lp.id,
        "user_id": lp.user_id,
        "track": {
            "id": lp.track.id,
            "slug": getattr(lp.track, "slug", None),
            "title": lp.track.title,
            "description": lp.track.description,
            "image_url": getattr(lp.track, "image_url", None)
        },
        "current_course_id": lp.current_course_id,
        "progress": float(lp.progress or 0.0),
        "courses": courses,
        "created_at": lp.created_at,
        "updated_at": lp.updated_at,
        "completed_at": lp.completed_at,
    }

    return resp


async def get_all_dashboard_data(user_id: str, db: AsyncSession) -> dict:
    """
    Fetch ALL dashboard data in a single call using asyncio.gather().
    This replaces 7+ individual API calls from the frontend with one round-trip.
    """
    (
        enrolled_courses,
        recent_resources,
        recent_achievements,
        progress_overview,
        recommended_courses,
        learning_path,
    ) = await asyncio.gather(
        get_enrolled_courses(user_id, db),
        get_recent_resources(user_id, db),
        get_recent_achievements(user_id, db),
        get_progress_overview(user_id, db),
        get_recommended_courses(user_id, db),
        get_active_learning_path(user_id, db, course_limit=5),
    )

    # Depends on enrolled_courses, so run after gather
    upcoming_deadlines = await get_upcoming_deadlines(
        user_id, db, enrolled_courses=enrolled_courses
    )

    return {
        "enrolled_courses": enrolled_courses,
        "recent_resources": recent_resources,
        "upcoming_deadlines": upcoming_deadlines,
        "recent_achievements": recent_achievements,
        "progress_overview": progress_overview,
        "recommended_courses": recommended_courses,
        "learning_path": learning_path,
    }