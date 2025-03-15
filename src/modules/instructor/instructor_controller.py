# src/instructor/course_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.common.utils.global_functions import ensure_instructor_or_admin
from src.modules.instructor import instructor_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user
from src.models.models import User

router = APIRouter(prefix="/instructor", tags=["instructor"])

def verify_instructor(current_user: User):
    if current_user.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not authorized as an instructor."
        )
    return current_user

@router.get("/courses", response_model=List[schemas.CourseResponse])
async def get_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    verify_instructor(current_user)
    courses = await instructor_service.list_courses(db)
    return courses

@router.post("/courses", response_model=schemas.CourseResponse)
async def create_course(
    course_data: schemas.CourseCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    verify_instructor(current_user)
    course = await instructor_service.create_course(course_data.model_dump(), db)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create course."
        )
    return course

@router.get("/courses/{course_id}", response_model=schemas.CourseResponse)
async def get_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    verify_instructor(current_user)
    course = await instructor_service.get_course_by_id(course_id, db)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )
    return course

@router.put("/courses/{course_id}", response_model=schemas.CourseResponse)
async def update_course(
    course_id: str,
    course_data: schemas.CourseUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    verify_instructor(current_user)
    updated_course = await instructor_service.update_course(course_id, course_data.model_dump(), db)
    if not updated_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )
    return updated_course

@router.post("/deadlines", response_model=schemas.DeadlineResponse)
async def create_deadline(
    deadline_request: schemas.DeadlineCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new upcoming deadline.
    This endpoint is restricted to users with the 'instructor' or 'admin' role.
    """
    ensure_instructor_or_admin(current_user)
    # Use model_dump() (Pydantic v2) instead of dict()
    deadline_data = deadline_request.model_dump()
    new_deadline = await instructor_service.create_deadline(deadline_data, db)
    if not new_deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create deadline."
        )
    return new_deadline