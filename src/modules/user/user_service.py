# src/user/user_service.py

from sqlalchemy.future import select
from src.models.models import User, UserCourse
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user_profile(current_user: User) -> User:
    """
    Retrieve the current user's profile.
    
    In this example, we simply return the current user instance.
    Additional business logic or data transformations can be applied here if needed.
    """
    return current_user

async def update_user_profile(current_user: User, profile_data: dict, db: AsyncSession) -> User:
    """
    Update the current user's profile with provided data.
    
    Only the fields provided (non-None) will be updated.
    """
    for key, value in profile_data.items():
        if value is not None:
            setattr(current_user, key, value)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

async def get_user_progress(current_user: User, db: AsyncSession) -> dict:
    """
    Retrieve the user's progress details.
    
    It returns a dictionary with:
      - overall_progress: The average progress across all enrolled courses.
      - courses: A list of individual course progress details.
    """
    # Query all UserCourse records for the current user
    result = await db.execute(select(UserCourse).where(UserCourse.user_id == current_user.id))
    user_courses = result.scalars().all()

    # Calculate overall progress (average) or 0 if no courses are enrolled
    if user_courses:
        overall_progress = sum(course.progress for course in user_courses) / len(user_courses)
    else:
        overall_progress = 0.0

    # Build the list of course progress details
    courses_progress = [
        {"course_id": str(course.course_id), "progress": course.progress}
        for course in user_courses
    ]

    return {"overall_progress": overall_progress, "courses": courses_progress}
