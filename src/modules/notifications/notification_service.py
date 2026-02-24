# src/notifications/notification_service.py

from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from src.models.models import Notification, NotificationType, UserNotification, UserCourse, LearningPath
from src.events.sse_manager import sse_manager
from sqlalchemy.orm import selectinload

async def _ensure_user_meta(user_id: str, db: AsyncSession) -> UserNotification:
    # Get or create user notification meta row
    result = await db.execute(select(UserNotification).where(UserNotification.user_id == user_id))
    meta = result.scalars().first()
    if not meta:
        meta = UserNotification(user_id=user_id, last_read_at=None, unread_notifications=[])
        db.add(meta)
        await db.commit()
        await db.refresh(meta)
    return meta

async def get_notifications(user_id: str, db: AsyncSession, limit: int = 10, offset: int = 0) -> Tuple[List[dict], int, bool]:
    """
    Returns a list of notifications visible to the user. Each item includes `is_unread` boolean.
    Also persists any newly-loaded notification ids into user_notification.unread_notifications (if not already present).
    Visibility rules:
      - Global (no course_id, no track_id, no user_id)
      - Notifications for user's active track (learning_path where completed_at is null)
      - Notifications for courses the user is enrolled in (user_courses)
      - Notifications with user_id == user (user-scoped)
    Unread definition:
      - id in user_meta.unread_notifications OR created_at > last_read_at (or last_read_at is None -> treat as unread)
    """
    meta = await _ensure_user_meta(user_id, db)

    # get user's learning path track_id (active)
    lp_track_id = None
    lp_res = await db.execute(
        select(LearningPath).where(LearningPath.user_id == user_id, LearningPath.completed_at.is_(None))
    )
    lp = lp_res.scalars().first()
    if lp:
        lp_track_id = lp.track_id

    # get enrolled course ids
    uc_res = await db.execute(select(UserCourse).where(UserCourse.user_id == user_id))
    user_courses = uc_res.scalars().all()
    enrolled_course_ids = [uc.course_id for uc in user_courses] if user_courses else []

    # Candidate query: notifications that might be visible
    stmt = select(Notification).order_by(Notification.created_at.desc())
    result = await db.execute(stmt)
    candidates = result.scalars().all()  # we'll filter in python (keeps SQL simple)

    # Build python-side filters & unread logic
    last_read_at = meta.last_read_at
    unread_set = set(str(i) for i in (meta.unread_notifications or []))

    to_return = []
    added_unread_ids = set()

    for n in candidates:
        # visibility checks
        is_global = (n.course_id is None and n.track_id is None and n.user_id is None)
        is_for_user = (n.user_id is not None and str(n.user_id) == str(user_id))
        is_for_track = (lp_track_id is not None and n.track_id is not None and str(n.track_id) == str(lp_track_id))
        is_for_enrolled_course = (n.course_id is not None and any(str(n.course_id) == str(cid) for cid in enrolled_course_ids))

        if not (is_global or is_for_user or is_for_track or is_for_enrolled_course):
            continue

        # determine unread status
        created_at = n.created_at
        created_at_dt = created_at if isinstance(created_at, datetime) else datetime.fromisoformat(str(created_at))
        is_unread = False
        if str(n.id) in unread_set:
            is_unread = True
        else:
            # if last_read_at is None -> consider unread; else compare
            if last_read_at is None:
                is_unread = True
            else:
                # assume last_read_at is datetime
                if created_at_dt > last_read_at:
                    is_unread = True

        # If we brought a notification that's unread but not in the meta.unread_notifications, remember to add it
        if is_unread and str(n.id) not in unread_set:
            added_unread_ids.add(str(n.id))

        to_return.append({
            "id": n.id,
            "type": n.type.value if hasattr(n.type, "value") else str(n.type),
            "title": n.title,
            "message": n.message,
            "created_at": n.created_at,
            "course_id": n.course_id,
            "track_id": n.track_id,
            "user_id": n.user_id,
            "is_unread": is_unread,
        })

    # Persist newly added unread ids (merge with existing)
    if added_unread_ids:
        raw = list(meta.unread_notifications or [])
        raw_set = set(str(x) for x in raw)
        merged = list(raw_set.union(added_unread_ids))
        meta.unread_notifications = merged
        db.add(meta)
        await db.commit()
        await db.refresh(meta)

    total = len(to_return)
    sliced_items = to_return[offset : offset + limit]
    has_more = (offset + limit) < total

    return sliced_items, total, has_more

async def mark_notification_as_read(notification_id: str, user_id: str, db: AsyncSession) -> bool:
    """
    Remove notification_id from user_meta.unread_notifications and update last_read_at if notification.created_at is newer.
    Returns True if operation succeeded.
    """
    # ensure meta exists
    meta = await _ensure_user_meta(user_id, db)

    notif_res = await db.execute(select(Notification).where(Notification.id == notification_id))
    notif = notif_res.scalars().first()
    if not notif:
        return False

    nid_str = str(notification_id)
    current_unread = list(meta.unread_notifications or [])
    if nid_str in [str(x) for x in current_unread]:
        current_unread = [x for x in current_unread if str(x) != nid_str]
        meta.unread_notifications = current_unread

    # update last_read_at if notification.created_at is newer
    if meta.last_read_at is None or (notif.created_at and notif.created_at > meta.last_read_at):
        meta.last_read_at = notif.created_at

    db.add(meta)
    await db.commit()
    return True

async def create_notification(
    title: str,
    message: str,
    db: AsyncSession,
    user_id: Optional[str] = None,
    course_id: Optional[str] = None,
    track_id: Optional[str] = None,
    created_by: Optional[str] = None,
    notif_type: NotificationType = NotificationType.INFO,
    commit: bool = True,
):
    """
    Create a notification record, optionally scoped to a user, course, or track.

    Args:
        title: Short title for the notification.
        message: Full notification message.
        db: Database session.
        user_id: Optional user to notify.
        course_id: Optional course to notify enrolled users.
        track_id: Optional track to notify enrolled users. 
        created_by: Optional admin ID who created the notification.
        notif_type: NotificationType enum value (default: INFO).
        commit: If False, only adds to session without committing.
                Caller is responsible for committing the transaction.
                Useful for batch operations to avoid N sequential commits.
    """
    provided_scopes = [s for s in (user_id, course_id, track_id) if s is not None]
    if len(provided_scopes) > 1:
        raise ValueError("Only one of user_id, course_id, or track_id may be set.")

    new_notification = Notification(
        title=title,
        type=notif_type,
        message=message,
        user_id=user_id,
        course_id=course_id,
        track_id=track_id,
        created_by=created_by,
    )
    db.add(new_notification)
    if commit:
        await db.commit()
    else:
        await db.flush()  # Ensure ID is generated for the payload
    
    await db.refresh(new_notification)
    
    # Dispatch to active SSE clients based on scope
    active_users = list(sse_manager.connections.keys())
    if active_users:
        payload = {
            "id": str(new_notification.id),
            "type": new_notification.type.name.lower() if hasattr(new_notification.type, 'name') else str(new_notification.type).lower(),
            "title": new_notification.title,
            "message": new_notification.message,
            "created_at": new_notification.created_at.isoformat() if new_notification.created_at else None,
            "is_unread": True
        }
        
        if new_notification.user_id:
            uid_str = str(new_notification.user_id)
            if uid_str in active_users:
                await sse_manager.send_to_user(uid_str, payload)
        elif new_notification.course_id:
            # Determine which active users are enrolled in this course
            from uuid import UUID
            active_uuids = [UUID(u) for u in active_users]
            stmt = select(UserCourse.user_id).where(
                UserCourse.course_id == new_notification.course_id,
                UserCourse.user_id.in_(active_uuids)
            )
            res = await db.execute(stmt)
            for uid in res.scalars().all():
                await sse_manager.send_to_user(str(uid), payload)
        elif new_notification.track_id:
            # Determine which active users belong to this track
            from uuid import UUID
            active_uuids = [UUID(u) for u in active_users]
            stmt = select(LearningPath.user_id).where(
                LearningPath.track_id == new_notification.track_id,
                LearningPath.completed_at.is_(None),
                LearningPath.user_id.in_(active_uuids)
            )
            res = await db.execute(stmt)
            for uid in res.scalars().all():
                await sse_manager.send_to_user(str(uid), payload)
        else:
            # Global notification, broadcast to all active connections
            for uid in active_users:
                await sse_manager.send_to_user(uid, payload)
    
    return new_notification