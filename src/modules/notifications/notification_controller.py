from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.notifications import notification_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user
from src.models.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("", response_model=List[schemas.NotificationResponse])
async def get_user_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve notifications visible to the current user.
    """
    notifications = await notification_service.get_notifications(str(current_user.id), db)
    return notifications

@router.put("/{notificationId}/read", response_model=schemas.NotificationUpdateResponse)
async def mark_notification_read(
    notificationId: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mark a specific notification as read for the current user.
    """
    success = await notification_service.mark_notification_as_read(str(notificationId), str(current_user.id), db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found."
        )
    return schemas.NotificationUpdateResponse(message="Notification marked as read.")
