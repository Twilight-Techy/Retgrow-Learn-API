import asyncio
import logging
from uuid import uuid4
from sqlalchemy import select

from src.models.models import Track, Course
from src.common.database.database import async_session
from src.events.dispatcher import dispatcher
import src.main # Pre-loads all listeners

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_lifecycle_events():
    async with async_session() as session:
        # Fetch existing records to satisfy Foreign Key constraints
        track_res = await session.execute(select(Track).limit(1))
        test_track = track_res.scalar_one_or_none()
        if not test_track:
            logging.error("No tracks found in the database. Please create a track before running this test.")
            return
        dummy_track_id = str(test_track.id)

        course_res = await session.execute(select(Course).limit(1))
        test_course = course_res.scalar_one_or_none()
        if not test_course:
            logging.error("No courses found in the database. Please create a course before running this test.")
            return
        dummy_course_id = str(test_course.id)

        # 1. Global Track Created Event
        logging.info("--- Dispatching 'track_event' (Global) ---")
        await dispatcher.dispatch("track_event", track_title="Cybersecurity Fundamentals", action="added", db=session)
        
        # 2. Track-Scoped Course Updated Event
        logging.info("--- Dispatching 'course_event' (Scoped to track) ---")
        await dispatcher.dispatch("course_event", course_title="Network Security 101", track_id=dummy_track_id, action="updated", db=session)
        
        # 3. Course-Scoped Module Deleted Event
        logging.info("--- Dispatching 'course_content_event' (Scoped to course) ---")
        await dispatcher.dispatch("course_content_event", item_type="Module", item_title="Firewalls", course_id=dummy_course_id, action="deleted", db=session)

        # 4. Track-Scoped Resource Updated Event
        logging.info("--- Dispatching 'track_content_event' (Scoped to track) ---")
        await dispatcher.dispatch("track_content_event", item_type="Resource", item_title="Handy Cheat_Sheet.pdf", track_id=dummy_track_id, action="updated", db=session)

        logging.info("--- Events dispatched, database commit expected via background tasks ---")

if __name__ == "__main__":
    asyncio.run(test_lifecycle_events())
