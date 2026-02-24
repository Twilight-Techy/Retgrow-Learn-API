import asyncio
import logging
from uuid import uuid4

from src.common.database.database import async_session
from src.events.dispatcher import dispatcher
import src.main # Pre-loads all listeners

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_lifecycle_events():
    async with async_session() as session:
        # 1. Global Track Created Event
        logging.info("--- Dispatching 'track_event' (Global) ---")
        await dispatcher.dispatch("track_event", track_title="Cybersecurity Fundamentals", action="added", db=session)
        
        # 2. Track-Scoped Course Updated Event
        logging.info("--- Dispatching 'course_event' (Scoped to track) ---")
        dummy_track_id = str(uuid4())
        await dispatcher.dispatch("course_event", course_title="Network Security 101", track_id=dummy_track_id, action="updated", db=session)
        
        # 3. Course-Scoped Module Deleted Event
        logging.info("--- Dispatching 'course_content_event' (Scoped to course) ---")
        dummy_course_id = str(uuid4())
        await dispatcher.dispatch("course_content_event", item_type="Module", item_title="Firewalls", course_id=dummy_course_id, action="deleted", db=session)

        # 4. Track-Scoped Resource Updated Event
        logging.info("--- Dispatching 'track_content_event' (Scoped to track) ---")
        await dispatcher.dispatch("track_content_event", item_type="Resource", item_title="Handy Cheat_Sheet.pdf", track_id=dummy_track_id, action="updated", db=session)

        logging.info("--- Events dispatched, database commit expected via background tasks ---")

if __name__ == "__main__":
    asyncio.run(test_lifecycle_events())
