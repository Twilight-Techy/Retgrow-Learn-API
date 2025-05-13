# src/courses/course_controller.py

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.utils.global_functions import ensure_instructor_or_admin
from src.modules.courses import course_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user  # Assumes implementation exists
from src.models.models import User

router = APIRouter(prefix="/courses", tags=["courses"])

# GET /courses - Retrieve all courses
@router.get("", response_model=List[schemas.CourseResponse])
async def get_courses(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve courses with optional search filtering and pagination.
    
    Query Parameters:
    - **q**: Optional search query to filter courses by title or description.
    - **skip**: Number of records to skip for pagination.
    - **limit**: Maximum number of records to return.
    """
    courses = await course_service.get_all_courses(db, q, skip, limit)
    return courses

# GET /courses/{course_id} - Retrieve course details by ID
@router.get("/{course_id}", response_model=schemas.CourseResponse)
async def get_course(course_id: UUID, db: AsyncSession = Depends(get_db_session)):
    course = await course_service.get_course_by_id(course_id, db)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return course

@router.post("", response_model=schemas.CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(   
    course_data: schemas.CourseCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    course = await course_service.create_course(course_data.model_dump(), db)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create course."
        )
    return course

@router.put("/{course_id}", response_model=schemas.CourseResponse)
async def update_course(
    course_id: UUID,
    course_data: schemas.CourseUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    updated_course = await course_service.update_course(course_id, course_data.model_dump(), db)
    if not updated_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )
    return updated_course

@router.post("/with_content", response_model=schemas.CourseDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_course_with_content(
    course_data: schemas.CourseCreateWithContentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    course = await course_service.create_course_with_content(course_data.model_dump(), db)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create course with content."
        )
    return schemas.CourseDetailResponse.model_validate(course)

@router.put("/{course_id}/with_content", response_model=schemas.CourseDetailResponse)
async def update_course_with_content(
    course_id: UUID,
    course_data: schemas.CourseUpdateWithContentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    updated_course = await course_service.update_course_with_content(course_id, course_data.model_dump(), db)
    if not updated_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )
    return schemas.CourseDetailResponse.model_validate(updated_course)

@router.delete("/{course_id}", response_model=dict)
async def delete_course(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    try:
        await course_service.delete_course(course_id, db)
        return {"message": "Course deleted successfully"}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    

# GET /courses/{course_id}/content - Retrieve detailed course content
@router.get("/{course_id}/content", response_model=schemas.CourseDetailResponse)
async def get_course_content(course_id: UUID, db: AsyncSession = Depends(get_db_session)):
    course = await course_service.get_course_content(course_id, db)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course content not found"
        )
    return course

# POST /courses/{course_id}/enroll - Enroll the current user in a course
@router.post("/{course_id}/enroll", response_model=schemas.EnrollmentResponse)
async def enroll_course(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    success = await course_service.enroll_in_course(course_id, current_user, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already enrolled in this course"
        )
    return schemas.EnrollmentResponse(message="Enrollment successful.")