# src/achievements/check_consecutive_logins.py

from datetime import datetime, timezone, timedelta
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.models import UserLogin

async def check_consecutive_logins(user, db: AsyncSession) -> bool:
    """
    Check if the user has logged in for 7 consecutive days.
    This function assumes that each login event is recorded in the UserLogin table,
    and that login_at is a timezone-aware datetime in UTC.
    """
    now = datetime.now(timezone.utc)
    # Consider login events for the last 10 days (to be safe)
    start_date = now - timedelta(days=10)
    
    result = await db.execute(
        select(UserLogin)
        .where(
            UserLogin.user_id == user.id,
            UserLogin.login_at >= start_date
        )
        .order_by(UserLogin.login_at.desc())
    )
    login_events = result.scalars().all()
    
    # Extract unique login dates (as date objects)
    unique_dates = {event.login_at.date() for event in login_events}
    
    # Sort the dates in descending order (most recent first)
    sorted_dates = sorted(unique_dates, reverse=True)
    
    # If there are fewer than 7 unique days, the achievement cannot be met.
    if len(sorted_dates) < 7:
        return False

    # Check if the 7 most recent unique dates are consecutive.
    for i in range(6):
        if (sorted_dates[i] - sorted_dates[i+1]).days != 1:
            return False

    return True
