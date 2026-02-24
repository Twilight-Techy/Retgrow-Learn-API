import asyncio
import logging
from typing import Callable, Dict, List, Any
from src.common.database.database import async_session

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[..., Any]

class EventDispatcher:
    """
    A lightweight internal Pub/Sub system.
    Listeners can subscribe to string-based events.
    The dispatcher is designed to be called asynchronously (often from a BackgroundTask).
    It manages its own database session and provides it to listeners as `db`.
    """
    def __init__(self):
        self._listeners: Dict[str, List[EventHandler]] = {}

    def subscribe(self, event_name: str, handler: EventHandler):
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(handler)
        logger.info(f"Subscribed {handler.__name__} to '{event_name}'")

    async def dispatch(self, event_name: str, **kwargs):
        """
        Dispatches an event to all subscribed listeners concurrently.
        Injects a fresh AsyncSession into kwargs as 'db'.
        """
        if event_name not in self._listeners or not self._listeners[event_name]:
            logger.debug(f"Event '{event_name}' dispatched, but no listeners attached.")
            return

        logger.info(f"Dispatching event '{event_name}' to {len(self._listeners[event_name])} listeners.")

        # Create a new session for the background listeners
        async with async_session() as session:
            kwargs["db"] = session
            try:
                # Prepare tasks to run concurrently
                tasks = [handler(**kwargs) for handler in self._listeners[event_name]]
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    # Log any unhandled exceptions raised by listeners
                    for res in results:
                        if isinstance(res, Exception):
                            logger.error(f"Error in listener for '{event_name}': {res}", exc_info=res)
                
                # Commit all database changes made by listeners during this event cycle
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to complete event dispatch for '{event_name}': {e}")
                await session.rollback()

# Singleton instance
dispatcher = EventDispatcher()
