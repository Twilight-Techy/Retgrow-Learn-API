# src/notifications/notification_controller.py

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.modules.notifications import notification_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user  # Assumes this dependency is implemented
from src.models.models import User

router = APIRouter(prefix="/user", tags=["notifications"])

@router.get("/notifications", response_model=List[schemas.NotificationResponse])
async def get_user_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve all notifications for the currently authenticated user.
    """
    notifications = await notification_service.get_notifications(str(current_user.id), db)
    return notifications

@router.put("/notifications/{notificationId}/read", response_model=schemas.NotificationUpdateResponse)
async def mark_notification_read(
    notificationId: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mark a specific notification as read.
    """
    success = await notification_service.mark_notification_as_read(notificationId, str(current_user.id), db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or does not belong to the user."
        )
    return schemas.NotificationUpdateResponse(message="Notification marked as read.")
