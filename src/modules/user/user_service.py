# src/user/user_service.py

from sqlalchemy.future import select
from src.models.models import Course, User, UserCourse
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
    Retrieve the user's progress details, including course titles.

    It returns a dictionary with:
      - overall_progress: The average progress across all enrolled courses.
      - courses: A list of individual course progress details, including the title.
    """
    # Query all UserCourse records for the current user and join with the Course table to get the title
    result = await db.execute(
        select(UserCourse, Course.title)
        .join(Course, UserCourse.course_id == Course.id)
        .where(UserCourse.user_id == current_user.id)
    )
    # The result now contains tuples of (UserCourse object, Course title)
    user_courses_with_titles = result.all()

    # Calculate overall progress or 0 if no courses are enrolled
    if user_courses_with_titles:
        # Sum the progress from the UserCourse objects in the tuples
        overall_progress = sum(row.UserCourse.progress for row in user_courses_with_titles) / len(user_courses_with_titles)
    else:
        overall_progress = 0.0

    # Build the list of course progress details with the course title
    courses_progress = [
        {"course_id": str(row.UserCourse.course_id), "progress": row.UserCourse.progress, "title": row.title}
        for row in user_courses_with_titles
    ]

    return {"overall_progress": overall_progress, "courses": courses_progress}