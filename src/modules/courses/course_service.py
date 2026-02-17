# src/courses/course_service.py

from datetime import datetime, timezone 
from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import selectinload
from src.models.models import Course, Lesson, Module, Track, TrackCourse, UserCourse, User, UserLesson, Certificate
from src.modules.notifications.notification_service import create_notification
from src.modules.subscriptions import access_control_service

# Retrieve all courses
async def get_all_courses(
    db: AsyncSession,
    q: Optional[str] = None,
    track: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
) -> List[Course]:
    """
    Retrieve courses with optional search, track filter, and pagination.
    """

    query = select(Course)

    # Search by q
    if q:
        query = query.where(
            or_(
                Course.title.ilike(f"%{q}%"),
                Course.description.ilike(f"%{q}%"),
            )
        )

    # Filter by track slug
    if track:
        query = (
            query.join(Course.track_associations)
            .join(TrackCourse.track)
            .where(Track.slug == track)
        )

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()

async def get_course_by_id(course_id: str, db: AsyncSession) -> Optional[Course]:
    stmt = (
        select(Course)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons)
        )
        .where(Course.id == course_id)
    )
    result = await db.execute(stmt)
    return result.scalars().first()

async def create_course(course_data: dict, db: AsyncSession) -> Course:
    """
    Create a new course using the provided data.
    """
    new_course = Course(
        title=course_data["title"],
        description=course_data["description"],
        image_url=course_data["image_url"],
        level=course_data["level"],
        duration=course_data["duration"],
        price=course_data["price"]
    )
    db.add(new_course)
    await db.commit()
    await db.refresh(new_course)
    return new_course

async def create_course_with_content(course_data: dict, db: AsyncSession) -> Course:
    """
    Create a new course along with its modules and lessons.
    """
    new_course = Course(
        title=course_data["title"],
        description=course_data["description"],
        image_url=course_data["image_url"],
        level=course_data["level"],
        duration=course_data["duration"],
        price=course_data["price"]
    )
    db.add(new_course)

    for module_data in course_data.get("modules", []):
        new_module = Module(
            title=module_data["title"],
            order=module_data["order"],
            is_free=module_data.get("is_free", False),
            course=new_course # Associate module with the course
        )
        db.add(new_module)
        for lesson_data in module_data.get("lessons", []):
            new_lesson = Lesson(
                title=lesson_data["title"],
                content=lesson_data.get("content"),
                video_url=lesson_data.get("video_url"),
                order=lesson_data["order"],
                module=new_module # Associate lesson with the module
            )
            db.add(new_lesson)

    await db.commit()
    await db.refresh(new_course)
    return new_course

async def delete_course(course_id: str, db: AsyncSession) -> Course:
    """
    Delete a course by its ID.
    """
    course = await get_course_by_id(course_id, db)
    if not course:
        raise ValueError("Course not found")
    try:
        await db.delete(course)
    except NoResultFound:
        raise ValueError("Course not found")
    except IntegrityError:
        raise ValueError("Course is associated with other records and cannot be deleted.")
    await db.commit()

async def update_course(course_id: str, course_data: dict, db: AsyncSession) -> Optional[Course]:
    """
    Update an existing course with the provided data.
    """
    course = await get_course_by_id(course_id, db)
    if not course:
        return None
    for key, value in course_data.items():
        if value is not None:
            setattr(course, key, value)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course

async def update_course_with_content(course_id: str, course_data: dict, db: AsyncSession) -> Optional[Course]:
    """
    Update a course along with its modules and lessons.
    This implementation:
    1. Updates course metadata
    2. Compares existing modules/lessons with new data
    3. Only updates/deletes content that has actually changed
    4. Resets progress only for modified modules
    """
    course = await get_course_by_id(course_id, db)
    if not course:
        return None

    # Update course fields
    for key, value in course_data.items():
        if key != "modules" and value is not None:
            setattr(course, key, value)

    if "modules" in course_data:
        existing_modules = {module.order: module for module in course.modules}
        modified_module_ids = set()  # Track which modules have changed

        for module_data in course_data.get("modules", []):
            module_order = module_data.get("order")
            if not module_order:
                continue

            existing_module = existing_modules.get(module_order)
            module_changed = False

            if existing_module:
                # Check if module has changed
                if (existing_module.title != module_data["title"] or 
                    existing_module.is_free != module_data.get("is_free", False)):
                    module_changed = True
                    existing_module.title = module_data["title"]
                    existing_module.is_free = module_data.get("is_free", False)

                # Compare lessons
                if "lessons" in module_data:
                    existing_lessons = {lesson.order: lesson for lesson in existing_module.lessons}
                    
                    for lesson_data in module_data.get("lessons", []):
                        lesson_order = lesson_data.get("order")
                        if not lesson_order:
                            continue

                        existing_lesson = existing_lessons.get(lesson_order)
                        
                        if existing_lesson:
                            # Check if lesson content has changed
                            if (existing_lesson.title != lesson_data["title"] or
                                existing_lesson.content != lesson_data.get("content") or
                                existing_lesson.video_url != lesson_data.get("video_url")):
                                module_changed = True
                                existing_lesson.title = lesson_data["title"]
                                existing_lesson.content = lesson_data.get("content")
                                existing_lesson.video_url = lesson_data.get("video_url")
                        else:
                            # New lesson added
                            module_changed = True
                            new_lesson = Lesson(
                                title=lesson_data["title"],
                                content=lesson_data.get("content"),
                                video_url=lesson_data.get("video_url"),
                                order=lesson_order,
                                module=existing_module
                            )
                            db.add(new_lesson)
                    
                    # Check for deleted lessons
                    new_lesson_orders = {l.get("order") for l in module_data.get("lessons", [])}
                    if any(order not in new_lesson_orders for order in existing_lessons.keys()):
                        module_changed = True
                        for lesson in existing_module.lessons:
                            if lesson.order not in new_lesson_orders:
                                await db.delete(lesson)

                if module_changed:
                    modified_module_ids.add(str(existing_module.id))
            else:
                # Create new module with lessons
                new_module = Module(
                    title=module_data["title"],
                    order=module_order,
                    is_free=module_data.get("is_free", False),
                    course=course
                )
                db.add(new_module)
                
                for lesson_data in module_data.get("lessons", []):
                    new_lesson = Lesson(
                        title=lesson_data["title"],
                        content=lesson_data.get("content"),
                        video_url=lesson_data.get("video_url"),
                        order=lesson_data["order"],
                        module=new_module
                    )
                    db.add(new_lesson)
                modified_module_ids.add(str(new_module.id))

        # Check for deleted modules
        new_module_orders = {m.get("order") for m in course_data.get("modules", [])}
        for order, module in existing_modules.items():
            if order not in new_module_orders:
                modified_module_ids.add(str(module.id))
                await db.delete(module)        # Notify users about content changes if any modules were modified
        if modified_module_ids:
            # Get all enrollments for this course
            enrollments = await db.execute(
                select(UserCourse)
                .where(UserCourse.course_id == course_id)
            )
            for enrollment in enrollments.scalars():
                # Notify user about course changes but keep their progress
                await create_notification(
                    enrollment.user_id,
                    "Course Content Updated",
                    f"Some content in this course has been updated. Your progress has been preserved, but you may want to review the updated sections.",
                    db
                )

    await db.commit()
    await db.refresh(course)
    return course


# Retrieve course content: modules and their lessons
async def get_course_content(course_id: str, db: AsyncSession, current_user: Optional[User] = None) -> Optional[Course]:
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons)
        )
    )
    course = result.scalars().first()
    
    if not course:
        return None

    if current_user:
        # Check permissions and redact content if necessary
        
        # optimized: fetch all completed lesson IDs for this course & user
        completed_lesson_ids = set()
        stmt = (
            select(UserLesson.lesson_id)
            .join(Lesson, UserLesson.lesson_id == Lesson.id)
            .join(Module, Lesson.module_id == Module.id)
            .where(
                Module.course_id == course_id,
                UserLesson.user_id == current_user.id
            )
        )
        res = await db.execute(stmt)
        completed_lesson_ids = set(res.scalars().all())

        for module in course.modules:
            # Check module access
            has_access = await access_control_service.check_module_access(current_user, module, course, db)
            
            for lesson in module.lessons:
                # Set completion status
                lesson.completed = lesson.id in completed_lesson_ids

                if not has_access:
                    lesson.content = None
                    lesson.video_url = None
                    lesson.is_locked = True
                else:
                    lesson.is_locked = False
                    
    return course

# Enroll the current user in a course
async def enroll_in_course(course_id: str, current_user: User, db: AsyncSession) -> bool:
    # Check if the user is already enrolled
    result = await db.execute(
        select(UserCourse).where(
            (UserCourse.user_id == current_user.id) &
            (UserCourse.course_id == course_id)
        )
    )
    enrollment = result.scalars().first()
    if enrollment:
        # Already enrolled; no need to add again.
        return False

    # Check eligibility
    course = await get_course_by_id(course_id, db)
    if not course:
        raise ValueError("Course not found")
        
    is_eligible = await access_control_service.check_enrollment_eligibility(current_user, course, db)
    if not is_eligible:
        raise PermissionError("You are not eligible to enroll in this course with your current plan.")

    # Create a new enrollment record
    new_enrollment = UserCourse(
        user_id=current_user.id,
        course_id=course_id,
        progress=0.0  # Starting progress
    )
    db.add(new_enrollment)
    await db.commit()
    return True

async def check_and_mark_course_completion(user_id: str, course_id: str, db: AsyncSession) -> Optional[Certificate]:
    """
    Check if the user's enrollment in the specified course has reached 100% progress.
    If so, mark the course as completed and send a notification.
    Returns the generated certificate if eligible and successful.
    """
    result = await db.execute(
        select(UserCourse).where(
            UserCourse.user_id == user_id,
            UserCourse.course_id == course_id
        )
    )
    enrollment = result.scalars().first()
    
    # If already completed or just completed
    if enrollment and enrollment.progress >= 100:
        if enrollment.completed_at is None:
            enrollment.completed_at = datetime.now(timezone.utc)
            db.add(enrollment)
            await db.commit()
            # Send notification that the course is completed.
            await create_notification(
                user_id,
                "Course Completed",
                f"You have completed the course successfully!",
                db
            )
        
        # Try to generate certificate (logic inside will check eligibility)
        # Even if completed_at was already set, we check for certificate existence/regeneration
        from src.modules.certificates import certificate_service
        
        user_res = await db.execute(select(User).where(User.id == user_id))
        user = user_res.scalars().first()
        
        course_res = await db.execute(select(Course).where(Course.id == course_id))
        course = course_res.scalars().first()
        
        if user and course:
            try:
                # generate_certificate handles existence check internally
                # but if it returns existing_cert, that's fine.
                # if record was deleted, it creates new one.
                cert = await certificate_service.generate_certificate(user, course, db)
                return cert
            except Exception as e:
                print(f"Error generating certificate: {e}")
                # Don't fail the completion if cert generation fails?
                return None
    return None

async def get_enrollment_status(course_id: str, current_user: User, db: AsyncSession) -> Optional[UserCourse]:
    result = await db.execute(
        select(UserCourse).where(
            (UserCourse.user_id == current_user.id) &
            (UserCourse.course_id == course_id)
        )
    )
    return result.scalars().first()
