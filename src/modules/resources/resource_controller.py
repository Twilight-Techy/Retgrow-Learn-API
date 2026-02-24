# src/resources/resource_controller.py

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from src.auth.dependencies import get_current_user
from src.common.utils.global_functions import ensure_instructor_or_admin
from src.models.models import User
from src.modules.resources import resource_service, schemas
from src.common.database.database import get_db_session
from fastapi import BackgroundTasks
from src.events.dispatcher import dispatcher

router = APIRouter(prefix="/resources", tags=["resources"])

# GET /resources – Retrieve all resources
@router.get("", response_model=List[schemas.ResourceResponse])
async def get_resources(
    q: Optional[str] = Query(None, description="Search query for title/description"),
    track: Optional[str] = Query(None, description="Track slug to filter by"),
    type: Optional[str] = Query(None, description="Resource type (Article, Video, ...)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db_session),
):
    resources = await resource_service.get_resources(db, q=q, track_slug=track, rtype=type, skip=skip, limit=limit)
    return resources

# GET /resources/{resourceId} – Retrieve a specific resource by its ID
@router.get("/{resourceId}", response_model=schemas.ResourceResponse)
async def get_resource(resourceId: UUID, db: AsyncSession = Depends(get_db_session)):
    resource = await resource_service.get_resource_by_id(resourceId, db)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    return resource

@router.post("/{resource_id}/view", response_model=schemas.ResourceViewResponse)
async def record_resource_view(
    resource_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Records that the current user has viewed the specified resource.
    - If the user has already viewed the resource, it updates the timestamp.
    - Ensures that only the last 5 resources viewed by the user are kept.
    """
    success = await resource_service.record_resource_view(str(current_user.id), resource_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not record resource view."
        )
    return schemas.ResourceViewResponse(message="Resource view recorded successfully.")

@router.post("", response_model=schemas.ResourceResponse)
async def create_resource(
    resource_request: schemas.ResourceCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Ensure the current user is either an instructor or an admin.
    ensure_instructor_or_admin(current_user)
    resource_data = resource_request.model_dump()
    new_resource = await resource_service.create_resource(resource_data, db)
    if not new_resource:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create resource."
        )
    background_tasks.add_task(dispatcher.dispatch, "track_content_event", item_type="Resource", item_title=new_resource.title, track_id=str(new_resource.track_id), action="added")
    return new_resource

@router.put("/{resource_id}", response_model=schemas.ResourceResponse)
async def update_resource(
    resource_id: UUID,
    resource_request: schemas.ResourceUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    resource_data = resource_request.model_dump()
    updated_resource = await resource_service.update_resource(resource_id, resource_data, db)
    if not updated_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found."
        )
    background_tasks.add_task(dispatcher.dispatch, "track_content_event", item_type="Resource", item_title=updated_resource.title, track_id=str(updated_resource.track_id), action="updated")
    return updated_resource

@router.delete("/{resource_id}", response_model=dict)
async def delete_resource(
    resource_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    
    resource_to_delete = await resource_service.get_resource_by_id(resource_id, db)
    if not resource_to_delete:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")
         
    success = await resource_service.delete_resource(resource_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found."
        )
    background_tasks.add_task(dispatcher.dispatch, "track_content_event", item_type="Resource", item_title=resource_to_delete.title, track_id=str(resource_to_delete.track_id), action="deleted")
    return {"message": "Resource deleted successfully."}
