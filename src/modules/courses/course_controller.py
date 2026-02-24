# src/courses/course_controller.py

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.utils.global_functions import ensure_instructor_or_admin
from src.modules.courses import course_service, schemas
from src.modules.certificates import certificate_service
from src.common.database.database import get_db_session
from fastapi import BackgroundTasks
from src.events.dispatcher import dispatcher
from src.auth.dependencies import get_current_user  # Assumes implementation exists
from src.common.database.database import get_db_session
from fastapi import BackgroundTasks
from src.events.dispatcher import dispatcher
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.models.models import User, Course, TrackCourse

router = APIRouter(prefix="/courses", tags=["courses"])

# GET /courses - Retrieve all courses
@router.get("", response_model=List[schemas.CourseResponse])
async def get_courses(
    q: Optional[str] = None,
    track: Optional[str] = None,  # <-- new filter
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve courses with optional search, track filtering, and pagination.

    Query Parameters:
    - **q**: Optional search query (title or description).
    - **track**: Optional track slug to filter by courses in that track.
    - **skip**: Number of records to skip (pagination).
    - **limit**: Maximum number of records to return.
    """
    courses = await course_service.get_all_courses(db, q, track, skip, limit)
    return courses

# GET /courses/{course_id} - Retrieve course details by ID
@router.get("/{course_id}", response_model=schemas.CourseDetailResponse)
async def get_course(course_id: UUID, db: AsyncSession = Depends(get_db_session)):
    course = await course_service.get_course_by_id(course_id, db)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return course

async def dispatch_course_event_for_all_tracks(course_id: UUID, title: str, action: str, db: AsyncSession):
    # Fetch all track associations for this course
    stmt = select(TrackCourse).where(TrackCourse.course_id == course_id)
    result = await db.execute(stmt)
    track_courses = result.scalars().all()

    if not track_courses:
        # If no tracks yet, dispatch one unscoped notification 
        await dispatcher.dispatch("course_event", course_title=title, track_id=None, action=action)
    else:
        for tc in track_courses:
            await dispatcher.dispatch("course_event", course_title=title, track_id=str(tc.track_id), action=action)

@router.post("", response_model=schemas.CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(   
    course_data: schemas.CourseCreateRequest,
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(dispatch_course_event_for_all_tracks, course.id, course.title, "added", db)
    return course

@router.put("/{course_id}", response_model=schemas.CourseResponse)
async def update_course(
    course_id: UUID,
    course_data: schemas.CourseUpdateRequest,
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(dispatch_course_event_for_all_tracks, updated_course.id, updated_course.title, "updated", db)
    return updated_course

@router.post("/with_content", response_model=schemas.CourseDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_course_with_content(
    course_data: schemas.CourseCreateWithContentRequest,
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(dispatch_course_event_for_all_tracks, course.id, course.title, "added", db)
    return schemas.CourseDetailResponse.model_validate(course)

@router.put("/{course_id}/with_content", response_model=schemas.CourseDetailResponse)
async def update_course_with_content(
    course_id: UUID,
    course_data: schemas.CourseUpdateWithContentRequest,
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(dispatch_course_event_for_all_tracks, updated_course.id, updated_course.title, "updated", db)
    return schemas.CourseDetailResponse.model_validate(updated_course)

@router.delete("/{course_id}", response_model=dict)
async def delete_course(
    course_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    
    # Needs course title to dispatch event
    course_to_delete = await course_service.get_course_by_id(course_id, db)
    if not course_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    try:
        await course_service.delete_course(course_id, db)
        background_tasks.add_task(dispatch_course_event_for_all_tracks, course_id, course_to_delete.title, "deleted", db)
        return {"message": "Course deleted successfully"}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    

# GET /courses/{course_id}/content - Retrieve detailed course content
@router.get("/{course_id}/content", response_model=schemas.CourseDetailResponse)
async def get_course_content(
    course_id: UUID, 
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    course = await course_service.get_course_content(course_id, db, current_user)
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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    try:
        success = await course_service.enroll_in_course(course_id, current_user, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already enrolled in this course!"
            )
        
        background_tasks.add_task(dispatcher.dispatch, "course_enrolled", user_id=str(current_user.id), course_id=str(course_id))

        return schemas.EnrollmentResponse(message="Enrollment successful.")
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
@router.get("/{course_id}/enrolled", response_model=schemas.EnrollmentStatusResponse)
async def get_enrollment_status(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    enrollment = await course_service.get_enrollment_status(course_id, current_user, db)
    return schemas.EnrollmentStatusResponse(is_enrolled=bool(enrollment))

@router.post("/{course_id}/complete", response_model=dict)
async def complete_course(
    course_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mark course as completed for the current user and try to generate a certificate.
    Returns { "certificate_id": uuid|null, "message": str }
    """
    # 1. Check if user is enrolled
    enrollment = await course_service.get_enrollment_status(course_id, current_user, db)
    if not enrollment:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not enrolled in this course."
        )

    # 2. Check if all lessons are completed? 
    # The requirement simplifies this to "mark as completed", but usually we should check progress.
    # However, logic in check_and_mark_course_completion checks if progress >= 100.
    # So we should probably ensure progress is 100 first?
    # Or does the user want a "Force Complete" button?
    # Context: "This should mark the course as completed and generate a certificate if it hasn't already been done."
    # AND "check_and_mark_course_completion" inside service checks for 100%.
    # If the user clicks "View Certificate", they likely have 100%.
    # If they don't, we can either strict check or just try.
    # Let's trust check_and_mark_course_completion.
    
    cert = await course_service.check_and_mark_course_completion(current_user, str(course_id), db)
    
    # If cert is returned, we have success.
    # If None, either not 100% or not eligible.
    # We can fetch existing cert if check_and_mark returned None but maybe they already had it?
    # check_and_mark attempts generation if 100%.
    
    if cert:
        background_tasks.add_task(dispatcher.dispatch, "course_completed", user_id=str(current_user.id), course_id=str(course_id), is_completion=True)
        return {"certificate_id": str(cert.id), "message": "Course completed and certificate generated."}
    
    # Check if a certificate exists anyway (e.g. generated previously)
    existing_cert = await certificate_service.get_certificate_by_user_and_course(current_user.id, course_id, db)
    if existing_cert:
        return {"certificate_id": str(existing_cert.id), "message": "Certificate retrieved."}

    return {"certificate_id": None, "message": "Course mark as completed, but no certificate generated (eligibility or progress issue)."}