# src/dashboard/dashboard_service.py

from typing import List
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from src.models.models import LearningPath, TrackCourse, UserAchievement, UserCourse, Course, UserResource, Resource, Deadline

# Service function to get enrolled courses for a user.
async def get_enrolled_courses(user_id: str, db: AsyncSession) -> List[Course]:
    # Query the UserCourse join table and retrieve related Course objects.
    stmt = select(Course, UserCourse.progress).join(UserCourse, UserCourse.course_id == Course.id).where(UserCourse.user_id == user_id)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    courses = []
    for course, progress in rows:
        setattr(course, "progress", float(progress or 0))
        courses.append(course)
    return courses

# Service function to get recent resources for a user.
async def get_recent_resources(user_id: str, db: AsyncSession, limit: int = 5):
    # join UserResource -> Resource, include Track info
    stmt = (
        select(Resource)
        .join(UserResource, UserResource.resource_id == Resource.id)
        .options(joinedload(Resource.track))
        .where(UserResource.user_id == user_id)
        .order_by(UserResource.last_accessed.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    resources = res.scalars().all()
    # Resource.track is available; Pydantic can read attributes (track.slug, track.title) if schema defines them.
    return resources

# Service function to get upcoming deadlines.
async def get_upcoming_deadlines(user_id: str, db: AsyncSession, limit: int = 10) -> List[Deadline]:
    enrolled_courses = await get_enrolled_courses(user_id, db)
    course_ids = [course.id for course in enrolled_courses]
    if not course_ids:
        return []
    now = datetime.now(timezone.utc)
    stmt = (
        select(Deadline)
        .where(Deadline.course_id.in_(course_ids), Deadline.due_date >= now)
        .order_by(Deadline.due_date.asc()).limit(limit)
    )
    result = await db.execute(stmt)
    deadlines = result.scalars().all()
    return deadlines

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
    Calculate progress overview for the currently enrolled courses for a user.
    - "Completed": courses with progress >= 100
    - "Not Started": courses with progress == 0 (or <= 0)
    - "In Progress": courses with progress > 0 and < 100
    Returns percentages for each category.
    """
    result = await db.execute(select(UserCourse).where(UserCourse.user_id == user_id))
    courses = result.scalars().all()
    total = len(courses)
    
    # If the user isn't enrolled in any courses, return all zeros.
    if total == 0:
        return [
            {"name": "Completed", "value": 0},
            {"name": "In Progress", "value": 0},
            {"name": "Not Started", "value": 0},
        ]
    
    completed = sum(1 for course in courses if course.progress >= 100)
    not_started = sum(1 for course in courses if course.progress <= 0)
    in_progress = total - completed - not_started
    
    # Calculate percentages (rounding to the nearest integer).
    completed_pct = round((completed / total) * 100)
    in_progress_pct = round((in_progress / total) * 100)
    not_started_pct = round((not_started / total) * 100)
    
    return [
        {"name": "Completed", "value": completed_pct},
        {"name": "In Progress", "value": in_progress_pct},
        {"name": "Not Started", "value": not_started_pct},
    ]

async def get_recommended_courses(user_id: str, db: AsyncSession) -> List[Course]:
    """
    Returns recommended courses for the user based on their current track enrollment.
    The logic:
      1. Retrieve the user's active learning path (completed_at is null).
      2. Retrieve all courses for that track from the TrackCourse association (with order).
      3. Retrieve courses the user is already enrolled in from UserCourse.
      4. Exclude already enrolled courses and return the remaining ones, sorted by TrackCourse.order.
    """
    # 1. Get the active learning path for the user.
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

    # 2. Retrieve all courses for the track using TrackCourse association.
    tc_result = await db.execute(
        select(TrackCourse)
        .where(TrackCourse.track_id == track_id)
        .order_by(TrackCourse.order.asc())
    )
    track_course_records = tc_result.scalars().all()
    # Build a set of all course IDs in the track and a mapping for ordering.
    all_course_ids = {tc.course_id for tc in track_course_records}
    order_map = {tc.course_id: tc.order for tc in track_course_records}

    # 3. Retrieve courses the user is already enrolled in.
    uc_result = await db.execute(
        select(UserCourse).where(UserCourse.user_id == user_id)
    )
    user_course_records = uc_result.scalars().all()
    enrolled_course_ids = {uc.course_id for uc in user_course_records}

    # 4. Recommended courses: courses in the track that the user is not enrolled in.
    recommended_ids = list(all_course_ids - enrolled_course_ids)
    if not recommended_ids:
        return []

    # Retrieve the Course objects for the recommended_ids.
    courses_result = await db.execute(
        select(Course).where(Course.id.in_(recommended_ids))
    )
    recommended_courses = courses_result.scalars().all()
    # Sort the courses by the order defined in the TrackCourse association.
    recommended_courses.sort(key=lambda course: order_map.get(course.id, 0))
    return recommended_courses