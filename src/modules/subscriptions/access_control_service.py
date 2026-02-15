
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.models import User, Course, Module, SubscriptionPlan, SubscriptionStatus
from src.modules.subscriptions import subscription_service

async def _get_user_plan(user: User, db: AsyncSession) -> SubscriptionPlan:
    """Helper to get user's active plan. Defaults to FREE."""
    subscription = await subscription_service.get_active_subscription(user.id, db)
    if subscription and subscription.status == SubscriptionStatus.ACTIVE:
        return subscription.plan
    return SubscriptionPlan.FREE

async def check_enrollment_eligibility(user: User, course: Course, db: AsyncSession) -> bool:
    """
    Check if a user is eligible to enroll in a course based on their plan.
    
    Rules:
    - Pro: Can enroll in anything.
    - Free/Focused: Can enroll only if:
        1. Course price is 0 (Free course).
        2. OR Course is part of their Enrolled Learning Path.
    """
    plan = await _get_user_plan(user, db)
    
    # Pro users can enroll in everything
    if plan == SubscriptionPlan.PRO:
        return True
    
    # Free/Focused users
    # 1. Free Value Course
    if course.price == 0:
        return True
        
    # 2. Check Learning Path
    # We need to check if this course is in the user's active learning path.
    # Assuming user.learning_path is loaded or we fetch it.
    # For now, let's fetch the learning path if not available on user object
    # Note: The User model has `learning_path` relationship (uselist=False).
    
    # If the user has a learning path, check if the course is in it.
    # We might need to query TrackCourse to see if course is in Track.
    if user.learning_path:
        track_id = user.learning_path.track_id
        # We need to check if course is in this track.
        # This requires a query or checking associations if loaded.
        # Let's assume we can check via relationships if loaded, otherwise query.
        
        # Optimization: Pass a flag or check DB
        # For simplicity and robustness, let's query if course is in track.
        from sqlalchemy import select
        from src.models.models import TrackCourse
        
        result = await db.execute(
            select(TrackCourse).where(
                TrackCourse.track_id == track_id,
                TrackCourse.course_id == course.id
            )
        )
        if result.scalars().first():
            return True
            
    return False

async def check_module_access(user: User, module: Module, course: Course, db: AsyncSession) -> bool:
    """
    Check if a user can access a specific module's content.
    
    Rules:
    - Pro: Full Access.
    - Free:
        - Full Access if Course Price == 0.
        - Else: Access only if module.is_free == True. (Even in Learning Path).
    - Focused:
        - Full Access if Course Price == 0.
        - Full Access if Course is in Enrolled Learning Path.
        - Else: Access only if module.is_free == True.
    """
    plan = await _get_user_plan(user, db)
    
    if plan == SubscriptionPlan.PRO:
        return True
        
    # Free course -> Access for everyone
    if course.price == 0:
        return True
        
    # Free module -> Access for everyone
    if module.is_free:
        return True
        
    if plan == SubscriptionPlan.FOCUSED:
        # Check if course is in learning path
        if user.learning_path:
            track_id = user.learning_path.track_id
            from sqlalchemy import select
            from src.models.models import TrackCourse
            result = await db.execute(
                select(TrackCourse).where(
                    TrackCourse.track_id == track_id,
                    TrackCourse.course_id == course.id
                )
            )
            if result.scalars().first():
                return True
                
    return False
