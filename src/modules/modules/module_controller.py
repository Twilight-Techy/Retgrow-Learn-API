from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from src.modules.modules import module_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user
from src.common.utils.global_functions import ensure_instructor_or_admin
from src.models.models import User
from fastapi import BackgroundTasks
from src.events.dispatcher import dispatcher

router = APIRouter(
    prefix="/courses/{course_id}/modules",
    tags=["modules"]
)

@router.post(
    "",
    response_model=schemas.ModuleResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_module(
    course_id: UUID,
    module_data: schemas.ModuleCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    try:
        module = await module_service.create_module(course_id, module_data.model_dump(), db)
        background_tasks.add_task(dispatcher.dispatch, "course_content_event", item_type="Module", item_title=module.title, course_id=str(course_id), action="added")
        return module
    except ValueError as ve:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.put(
    "/{module_id}", # Corrected from PATCH to PUT
    response_model=schemas.ModuleResponse
)
async def update_module(
    course_id: UUID,
    module_id: UUID,
    module_data: schemas.ModuleUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    try:
        module = await module_service.update_module(course_id, module_id, module_data.model_dump(exclude_none=True), db)
        background_tasks.add_task(dispatcher.dispatch, "course_content_event", item_type="Module", item_title=module.title, course_id=str(course_id), action="updated")
        return module
    except ValueError as ve:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.delete(
    "/{module_id}", # Removed status code
    response_model=dict
)
async def delete_module(
    course_id: UUID,
    module_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> dict: # Added return annotation
    ensure_instructor_or_admin(current_user)
    try:
        # Pre-fetch module to get its title for the notification
        from src.models.models import Module
        from sqlalchemy.future import select
        result = await db.execute(select(Module).where(Module.id == module_id, Module.course_id == course_id))
        module = result.scalars().first()
        
        await module_service.delete_module(course_id, module_id, db)
        
        if module:
            background_tasks.add_task(dispatcher.dispatch, "course_content_event", item_type="Module", item_title=module.title, course_id=str(course_id), action="deleted")
        
        return {"message": "Module deleted successfully"}
    except ValueError as ve:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(ve))
