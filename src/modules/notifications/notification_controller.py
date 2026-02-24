from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.notifications import notification_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user
from src.models.models import User
from src.events.sse_manager import sse_manager

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/stream")
async def stream_notifications(request: Request, current_user: User = Depends(get_current_user)):
    """
    SSE stream of realtime notifications for the current user.
    """
    user_id = str(current_user.id)
    queue = await sse_manager.connect(user_id)
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    # Wait for message, timeout occasionally to check disconnect status
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield message
                except asyncio.TimeoutError:
                    # Send an SSE comment to keep the connection alive (ping)
                    yield ": ping\n\n"
        finally:
            sse_manager.disconnect(user_id, queue)
            
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    }        
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)

@router.get("", response_model=schemas.NotificationListResponse)
async def get_user_notifications(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve notifications visible to the current user.
    """
    items, total, has_more = await notification_service.get_notifications(
        str(current_user.id), db, limit=limit, offset=offset
    )
    return schemas.NotificationListResponse(
        items=items,
        total=total,
        has_more=has_more
    )

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
