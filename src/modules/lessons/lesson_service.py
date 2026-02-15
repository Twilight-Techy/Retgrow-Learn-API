# src/lessons/lesson_service.py

from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy import and_, asc
from sqlalchemy.orm import selectinload

from src.models.models import Course, Lesson, Module, User, UserCourse, UserLesson
from src.modules.subscriptions import access_control_service

async def is_user_enrolled_in_course(user_id: str, course_id: str, db: AsyncSession) -> bool:
    stmt = select(UserCourse).where(
        and_(
            UserCourse.user_id == user_id,
            UserCourse.course_id == course_id
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first() is not None

async def get_lessons_by_course(course_id: str, current_user: User, db: AsyncSession):
    stmt = (
        select(
            Lesson,
            Module,
            Course,
            UserLesson.id.isnot(None).label("completed"),
        )
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .outerjoin(
            UserLesson,
            and_(
                UserLesson.lesson_id == Lesson.id,
                UserLesson.user_id == current_user.id
            )
        )
        .where(Module.course_id == course_id)
        .order_by(Module.order.asc(), Lesson.order.asc())
    )

    result = await db.execute(stmt)

    lessons = []
    # Result rows: (Lesson, Module, Course, completed)
    for lesson, module, course, completed in result.all():
        # Check access
        has_access = await access_control_service.check_module_access(current_user, module, course, db)
        
        # We need to return Lesson objects with attached fields like 'module_title' and 'completed'
        # and 'is_locked'.
        # Since we are modifying the ORM object, we should be careful. 
        # But this is a read operation and specific to this request.
        
        lesson.completed = completed
        lesson.module_title = module.title
        
        if not has_access:
            lesson.content = None
            lesson.video_url = None
            lesson.is_locked = True
        else:
            lesson.is_locked = False
            
        lessons.append(lesson)

    return lessons


async def get_lesson_in_course(course_id: str, lesson_id: str, db: AsyncSession) -> Optional[Lesson]:
    """
    Retrieve a single lesson and ensure it belongs to the given course (via Module.course_id).
    """
    stmt = (
        select(Lesson)
        .join(Module)
        .where(
            and_(
                Lesson.id == lesson_id,
                Module.course_id == course_id
            )
        )
    )
    result = await db.execute(stmt)
    lesson = result.scalars().first()
    return lesson


async def complete_lesson(course_id: str, lesson_id: str, current_user: User, db: AsyncSession) -> bool:
    """
    Mark a lesson as completed for the current user (idempotent).
    Returns True on success (including when already completed), False on failure (e.g. not found or not enrolled).
    """
    # 1) Ensure lesson exists and belongs to the course
    lesson = await get_lesson_in_course(course_id, lesson_id, db)
    if not lesson:
        return False

    # 2) Ensure user is enrolled in the course
    stmt = select(UserCourse).where(
        and_(
            UserCourse.user_id == current_user.id,
            UserCourse.course_id == course_id
        )
    )
    result = await db.execute(stmt)
    enrolled = result.scalars().first()
    if not enrolled:
        # user not enrolled -> cannot complete
        return False

    # 3) If already completed, return True (idempotent)
    stmt = select(UserLesson).where(
        and_(
            UserLesson.user_id == current_user.id,
            UserLesson.lesson_id == lesson_id
        )
    )
    result = await db.execute(stmt)
    existing = result.scalars().first()
    if existing:
        return True

    # 4) Create completion record
    try:
        new_completion = UserLesson(
            user_id=current_user.id,
            lesson_id=lesson_id,
            completed_at=datetime.now(timezone.utc)
        )
        db.add(new_completion)
        await db.commit()
        return True
    except IntegrityError:
        # race or duplicate -- treat as success (idempotent)
        await db.rollback()
        return True

async def create_lesson(module_id: str, lesson_data: dict, db: AsyncSession) -> Lesson:
    """
    Create a new lesson.
    """
    new_lesson = Lesson(
        module_id=module_id,
        title=lesson_data["title"],
        content=lesson_data["content"],
        video_url=lesson_data["video_url"],
        order=lesson_data["order"]
    )
    db.add(new_lesson)
    await db.commit()
    await db.refresh(new_lesson)
    return new_lesson

async def update_lesson(lesson_id: str, lesson_data: dict, db: AsyncSession) -> Optional[Lesson]:
    """
    Update an existing lesson.
    """
    lesson = await get_lesson_in_course(lesson_id, db)
    if not lesson:
        return None
    for key, value in lesson_data.items():
        setattr(lesson, key, value)
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson

async def get_last_or_first_lesson_for_user(course_id: str, user_id: str, db: AsyncSession) -> Optional[Dict]:
    """
    Return dict {"lesson_id": <uuid>}:
      - If user has completed lessons in course, return most recently completed lesson (UserLesson.completed_at desc)
      - Else return the first lesson in the course (module.order asc, lesson.order asc)
      - If course has no lessons return None
    Also ensure user is enrolled (UserCourse exists); if not, raise an exception upstream (we return None or raise here).
    """

    # 0) Ensure user is enrolled in the course
    uc_stmt = select(UserCourse).where(
        and_(
            UserCourse.course_id == course_id,
            UserCourse.user_id == user_id
        )
    )
    uc_res = await db.execute(uc_stmt)
    user_course = uc_res.scalars().first()
    if not user_course:
        # We choose to raise here by returning a special sentinel (controller maps to 403).
        # But service can also raise. We'll return a sentinel to let controller return 403.
        raise PermissionError("User not enrolled in course")

    # 1) Try to find most recent completed lesson for this user within the course
    # Join UserLesson -> Lesson -> Module (filter Module.course_id)
    ul_stmt = (
        select(UserLesson, Lesson)
        .join(Lesson, UserLesson.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .where(
            and_(
                Module.course_id == course_id,
                UserLesson.user_id == user_id
            )
        )
        .order_by(UserLesson.completed_at.desc())
        .limit(1)
    )
    ul_res = await db.execute(ul_stmt)
    ul_row = ul_res.first()
    if ul_row:
        # ul_row = (UserLesson, Lesson)
        _, lesson = ul_row
        return {"lesson_id": lesson.id}

    # 2) No completed lessons — find the first lesson in the course ordered by module.order then lesson.order
    first_stmt = (
        select(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .where(Module.course_id == course_id)
        .order_by(asc(Module.order), asc(Lesson.order))
        .limit(1)
    )
    first_res = await db.execute(first_stmt)
    first_lesson = first_res.scalars().first()
    if first_lesson:
        return {"lesson_id": first_lesson.id}

    # 3) Course has no lessons
    return None