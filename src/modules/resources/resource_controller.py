# src/resources/resource_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.auth.dependencies import get_current_user
from src.common.utils.global_functions import ensure_instructor_or_admin
from src.models.models import User
from src.modules.resources import resource_service, schemas
from src.common.database.database import get_db_session

router = APIRouter(prefix="/resources", tags=["resources"])

# GET /resources – Retrieve all resources
@router.get("", response_model=List[schemas.ResourceResponse])
async def get_resources(db: AsyncSession = Depends(get_db_session)):
    resources = await resource_service.get_all_resources(db)
    return resources

# GET /resources/{resourceId} – Retrieve a specific resource by its ID
@router.get("/{resourceId}", response_model=schemas.ResourceResponse)
async def get_resource(resourceId: str, db: AsyncSession = Depends(get_db_session)):
    resource = await resource_service.get_resource_by_id(resourceId, db)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    return resource

@router.post("/{resource_id}/view", response_model=schemas.ResourceViewResponse)
async def record_resource_view(
    resource_id: str,
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
    return new_resource

@router.put("/{resource_id}", response_model=schemas.ResourceResponse)
async def update_resource(
    resource_id: str,
    resource_request: schemas.ResourceUpdateRequest,
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
    return updated_resource

@router.delete("/{resource_id}", response_model=dict)
async def delete_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    success = await resource_service.delete_resource(resource_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found."
        )
    return {"message": "Resource deleted successfully."}
