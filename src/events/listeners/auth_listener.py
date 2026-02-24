import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.events.dispatcher import dispatcher
from src.models.models import UserLogin

logger = logging.getLogger(__name__)

async def handle_user_logged_in(user_id: str, db: AsyncSession, **kwargs):
    """
    Called when the 'user_logged_in' event is dispatched.
    Automatically records the login instance in the database.
    """
    try:
        login_event = UserLogin(user_id=user_id)
        db.add(login_event)
        logger.info(f"Recorded login event for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to record login event for {user_id}: {e}")

# Subscribe the listener to the dispatcher
dispatcher.subscribe("user_logged_in", handle_user_logged_in)
