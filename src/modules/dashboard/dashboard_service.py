# src/dashboard/dashboard_service.py

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
async def get_recent_resources(user_id: str, db: AsyncSession, limit: int = 5) -> List[Dict]:
    """
    Return recent resources accessed by user as plain dicts:
    [{ id, title, type, url, track_title }]
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
    resources = result.scalars().all()

    out = []
    for r in resources:
        out.append({
            "id": str(r.id),
            "title": r.title,
            # r.type might be an enum; convert to string safely
            "type": (r.type.value if hasattr(r.type, "value") else str(r.type)) if r.type is not None else None,
            "url": r.url,
            "track_title": (r.track.title if getattr(r, "track", None) else None)
        })
    return out

# Service function to get upcoming deadlines.
async def get_upcoming_deadlines(user_id: str, db: AsyncSession, limit: int = 10) -> List[dict]:
    """
    Retrieve deadlines for the user's enrolled courses.
    Includes deadlines in the past (marked as is_overdue=True) and future.
    Results are ordered by due_date ascending (earliest first).
    """
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

    now = datetime.now(timezone.utc)

    stmt = (
        select(Deadline)
        .options(selectinload(Deadline.course))
        .where(Deadline.course_id.in_(course_ids))
        .order_by(Deadline.due_date.asc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    deadlines = result.scalars().all()

    out = []
    for d in deadlines:
        is_overdue = False
        try:
            is_overdue = d.due_date is not None and d.due_date < now
        except Exception:
            is_overdue = False

        out.append({
            "id": str(d.id),
            "title": d.title,
            "description": d.description,
            "due_date": d.due_date,              # datetime -> Pydantic will serialize to ISO
            "course": d.course.title if getattr(d, "course", None) else None,
            "is_overdue": is_overdue
        })
    return out

# Service function to aggregate dashboard data.
async def get_dashboard_data(user_id: str, db: AsyncSession) -> dict:
    enrolled_courses = await get_enrolled_courses(user_id, db)
    recent_resources = await get_recent_resources(user_id, db)
    upcoming_deadlines = await get_upcoming_deadlines(user_id, db)
    
    return {
        "enrolled_courses": enrolled_courses,
        "recent_resources": recent_resources,
        "upcoming_deadlines": upcoming_deadlines
    }

async def get_recent_achievements(user_id: str, db: AsyncSession, limit: int = 5) -> List[dict]:
    """
    Query the UserAchievement table for the specified user,
    ordered by earned_at descending, and return the top achievements.
    """
    stmt = (
        select(UserAchievement)
        .where(UserAchievement.user_id == user_id)
        .options(selectinload(UserAchievement.achievement))
        .order_by(UserAchievement.earned_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    user_achievements = result.scalars().all()

    # Transform the results into dictionaries that include achievement details.
    # We assume that each UserAchievement instance has an attribute `achievement`
    # representing the associated Achievement record.
    recent = []
    for ua in user_achievements:
        achievement = ua.achievement
        recent.append({
            "id": str(achievement.id),
            "title": achievement.title,
            "description": achievement.description,
            "icon_url": achievement.icon_url,
            "earned_at": ua.earned_at,
        })
    return recent

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

    # 2) Collect enrolled course ids
    uc_result = await db.execute(
        select(UserCourse.course_id).where(UserCourse.user_id == user_id)
    )
    enrolled_course_ids = {row[0] for row in uc_result.all()}

    # 3) Get courses for the track (ordered by TrackCourse.order)
    stmt = (
        select(Course)
        .join(TrackCourse, TrackCourse.course_id == Course.id)
        .where(TrackCourse.track_id == track_id)
        .order_by(TrackCourse.order.asc())
    )
    result = await db.execute(stmt)
    courses_in_track = result.scalars().all()

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