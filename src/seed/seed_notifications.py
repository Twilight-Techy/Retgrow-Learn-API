# scripts/seed_notifications.py
"""
Seed script to create sample notifications with different types and scopes.

Usage:
    python scripts/seed_notifications.py

Notes:
- This script expects an AsyncSession factory named `async_session` to be importable.
- Creates notifications with different types (info, success, warning, error)
- Creates notifications with different scopes (global, course-specific, track-specific, user-specific)
- Can be run multiple times - will skip if notifications already exist
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from typing import List, Dict

# Adjust this import if your DB file/module path differs.
try:
    from src.common.database.database import async_session
except Exception as e:
    raise ImportError(
        "Couldn't import async_session from src.common.database.database. "
        "Adjust the import path to point to your DB module.\n"
        f"Original error: {e}"
    )


# UUIDs from your schema
USER_ID = "02b1c149-7b2a-456f-a289-c51a9d5f93a9"
COURSE_IDS = [
    "6e34354e-4ef1-4a5f-ab2a-db3f929116ff",
    "f6902b0f-047a-4f4e-88e4-e4ba97b19edb",
    "1f71998f-c815-4c22-9f9f-0524d71f4e34"
]
TRACK_ID = "d3992bb0-9afc-46c6-bb63-888f86ad5eb7"


# Sample notifications to seed
NOTIFICATIONS = [
    # Global notifications (no scope)
    {
        "type": "INFO",
        "title": "Platform Maintenance Scheduled",
        "message": "We will be performing scheduled maintenance on Saturday from 2 AM to 4 AM UTC. Some features may be temporarily unavailable.",
        "course_id": None,
        "track_id": None,
        "user_id": None,
    },
    {
        "type": "SUCCESS",
        "title": "New Features Released!",
        "message": "We've just launched several new features including enhanced analytics and improved course navigation. Check them out!",
        "course_id": None,
        "track_id": None,
        "user_id": None,
    },
    {
        "type": "WARNING",
        "title": "System Update Required",
        "message": "Please update your mobile app to the latest version to ensure compatibility with new features.",
        "course_id": None,
        "track_id": None,
        "user_id": None,
    },
    
    # Course-specific notifications
    {
        "type": "INFO",
        "title": "New Course Content Available",
        "message": "Three new lessons have been added to this course. Check out the latest modules in the curriculum section.",
        "course_id": COURSE_IDS[0],
        "track_id": None,
        "user_id": None,
    },
    {
        "type": "SUCCESS",
        "title": "Course Completion Milestone",
        "message": "Congratulations! Over 1,000 students have completed this course. Join the community of successful learners!",
        "course_id": COURSE_IDS[1],
        "track_id": None,
        "user_id": None,
    },
    {
        "type": "WARNING",
        "title": "Assignment Deadline Approaching",
        "message": "Your final project for this course is due in 3 days. Make sure to submit before the deadline to receive credit.",
        "course_id": COURSE_IDS[2],
        "track_id": None,
        "user_id": None,
    },
    {
        "type": "ERROR",
        "title": "Course Access Issue",
        "message": "There was a problem accessing some course materials. Our team is working on a fix. Please try again later.",
        "course_id": COURSE_IDS[0],
        "track_id": None,
        "user_id": None,
    },
    
    # Track-specific notifications
    {
        "type": "INFO",
        "title": "Track Curriculum Updated",
        "message": "We've updated the learning path for this track based on industry feedback. New courses have been added to enhance your learning experience.",
        "course_id": None,
        "track_id": TRACK_ID,
        "user_id": None,
    },
    {
        "type": "SUCCESS",
        "title": "Track Milestone Achieved",
        "message": "You're making great progress! You've completed 50% of the courses in this track. Keep up the excellent work!",
        "course_id": None,
        "track_id": TRACK_ID,
        "user_id": None,
    },
    
    # User-specific notifications
    {
        "type": "INFO",
        "title": "Welcome to the Platform!",
        "message": "We're excited to have you here. Start by exploring your dashboard and enrolling in your first course.",
        "course_id": None,
        "track_id": None,
        "user_id": USER_ID,
    },
    {
        "type": "SUCCESS",
        "title": "Achievement Unlocked!",
        "message": "Congratulations! You've earned the 'Early Bird' achievement for completing 5 lessons this week.",
        "course_id": None,
        "track_id": None,
        "user_id": USER_ID,
    },
    {
        "type": "WARNING",
        "title": "Profile Incomplete",
        "message": "Your profile is missing some important information. Complete your profile to get personalized course recommendations.",
        "course_id": None,
        "track_id": None,
        "user_id": USER_ID,
    },
    {
        "type": "ERROR",
        "title": "Payment Method Expired",
        "message": "Your payment method on file has expired. Please update your billing information to continue accessing premium content.",
        "course_id": None,
        "track_id": None,
        "user_id": USER_ID,
    },
]


async def check_existing_notifications(session) -> int:
    """Check how many notifications already exist."""
    stmt = text("SELECT COUNT(*) FROM notifications")
    result = await session.execute(stmt)
    return result.scalar()


async def insert_notification(session, notification: Dict, created_by: str):
    """Insert a single notification into the database."""
    notification_id = uuid.uuid4()
    
    stmt = text("""
        INSERT INTO notifications (
            id, type, course_id, track_id, user_id,
            title, message, created_by, created_at
        ) VALUES (
            :id, CAST(:type AS notificationtype), :course_id, :track_id, :user_id,
            :title, :message, :created_by, :created_at
        )
    """)
    
    # Create timestamps with slight variations for realism
    created_at = datetime.now(timezone.utc) - timedelta(
        hours=NOTIFICATIONS.index(notification),
        minutes=NOTIFICATIONS.index(notification) * 15
    )
    
    await session.execute(stmt, {
        "id": str(notification_id),
        "type": notification["type"],
        "course_id": notification["course_id"],
        "track_id": notification["track_id"],
        "user_id": notification["user_id"],
        "title": notification["title"],
        "message": notification["message"],
        "created_by": created_by,
        "created_at": created_at,
    })
    
    return notification_id, notification["title"]


async def seed_notifications(session):
    """Seed the database with sample notifications."""
    
    # Check if notifications already exist
    existing_count = await check_existing_notifications(session)
    
    if existing_count > 0:
        print(f"Found {existing_count} existing notifications in the database.")
        response = input("Do you want to add more sample notifications? (y/n): ").strip().lower()
        if response != 'y':
            print("Seed operation cancelled.")
            return
    
    print(f"\nSeeding {len(NOTIFICATIONS)} sample notifications...")
    print("=" * 60)
    
    created_notifications = []
    
    for notification in NOTIFICATIONS:
        notification_id, title = await insert_notification(
            session, 
            notification, 
            created_by=USER_ID
        )
        
        # Determine scope for display
        scope = "Global"
        if notification["course_id"]:
            scope = f"Course ({notification['course_id'][:8]}...)"
        elif notification["track_id"]:
            scope = f"Track ({notification['track_id'][:8]}...)"
        elif notification["user_id"]:
            scope = f"User ({notification['user_id'][:8]}...)"
        
        print(f"✓ [{notification['type']:8}] [{scope:30}] {title}")
        created_notifications.append((notification_id, title))
    
    # Commit all changes
    await session.commit()
    
    print("=" * 60)
    print(f"\n✓ Successfully created {len(created_notifications)} notifications!")
    print("\nBreakdown by type:")
    
    type_counts = {}
    for notification in NOTIFICATIONS:
        type_counts[notification["type"]] = type_counts.get(notification["type"], 0) + 1
    
    for notification_type, count in sorted(type_counts.items()):
        print(f"  - {notification_type}: {count}")
    
    print("\nBreakdown by scope:")
    scope_counts = {
        "global": sum(1 for n in NOTIFICATIONS if not any([n["course_id"], n["track_id"], n["user_id"]])),
        "course": sum(1 for n in NOTIFICATIONS if n["course_id"]),
        "track": sum(1 for n in NOTIFICATIONS if n["track_id"]),
        "user": sum(1 for n in NOTIFICATIONS if n["user_id"]),
    }
    
    for scope, count in scope_counts.items():
        if count > 0:
            print(f"  - {scope.capitalize()}: {count}")


async def main():
    """Main function to run the seed script."""
    async with async_session() as session:
        try:
            await seed_notifications(session)
        except Exception as exc:
            # Rollback and re-raise so the error is visible
            await session.rollback()
            print("\n❌ Error while running seed script. Rolled back transaction.")
            raise


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("NOTIFICATIONS SEED SCRIPT")
    print("=" * 60)
    asyncio.run(main())