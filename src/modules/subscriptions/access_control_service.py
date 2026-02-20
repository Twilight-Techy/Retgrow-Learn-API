
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.models import User, Course, Module, SubscriptionPlan, SubscriptionStatus
from src.modules.subscriptions import subscription_service

async def _get_user_plan(user: User, db: AsyncSession) -> SubscriptionPlan:
    """Helper to get user's active plan. Defaults to FREE."""
    subscription = await subscription_service.get_best_valid_subscription(user.id, db)
    # The service function already filters for valid status/date and sorts by priority.
    if subscription:
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
    # Query LearningPath explicitly to avoid lazy load error
    from sqlalchemy import select
    from src.models.models import TrackCourse, LearningPath
    
    lp_result = await db.execute(select(LearningPath).where(LearningPath.user_id == user.id))
    learning_path = lp_result.scalars().first()
    
    if learning_path:
        track_id = learning_path.track_id
        # Check if course is in this track
        result = await db.execute(
            select(TrackCourse).where(
                TrackCourse.track_id == track_id,
                TrackCourse.course_id == course.id
            )
        )
        if result.scalars().first():
            return True
            
    return False

async def check_module_access(user: User, module: Module, course: Course, db: AsyncSession, plan: SubscriptionPlan = None) -> bool:
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
    
    Args:
        plan: If provided, skips the DB query to fetch the user's plan.
              Pass this when calling in a loop to avoid O(N) redundant queries.
    """
    if plan is None:
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
        # Explicitly query learning path to avoid lazy load error
        from src.models.models import LearningPath, TrackCourse
        from sqlalchemy import select
        
        lp_result = await db.execute(select(LearningPath).where(LearningPath.user_id == user.id))
        learning_path = lp_result.scalars().first()
        
        if learning_path:
            track_id = learning_path.track_id
            result = await db.execute(
                select(TrackCourse).where(
                    TrackCourse.track_id == track_id,
                    TrackCourse.course_id == course.id
                )
            )
            if result.scalars().first():
                return True
                
    return False

async def check_skills_access(user: User, db: AsyncSession) -> bool:
    """
    Check if a user can access skills tracking.
    Only FOCUSED and PRO plans have access.
    """
    plan = await _get_user_plan(user, db)
    return plan in [SubscriptionPlan.FOCUSED, SubscriptionPlan.PRO]
