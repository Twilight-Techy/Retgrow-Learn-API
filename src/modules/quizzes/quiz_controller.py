# src/quizzes/quiz_controller.py

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.common.utils.global_functions import ensure_instructor_or_admin
from src.modules.quizzes import quiz_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user  # Assumes this dependency is implemented
from src.models.models import User

router = APIRouter(prefix="/quizzes", tags=["quizzes"])

@router.get("", response_model=List[schemas.QuizResponse])
async def get_quizzes(db: AsyncSession = Depends(get_db_session)):
    """
    Retrieve a list of all quizzes.
    """
    quizzes = await quiz_service.get_all_quizzes(db)
    return quizzes

@router.get("/track", response_model=List[schemas.CourseQuizzesResponse])
async def get_quizzes_for_track(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve all quizzes for the track in which the current user is enrolled.
    Quizzes are grouped by course and each quiz is returned as a summary.
    """
    quizzes_by_track = await quiz_service.get_quizzes_by_track(str(current_user.id), db)
    if not quizzes_by_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No quizzes found for your enrolled track."
        )
    return quizzes_by_track

@router.get("/{quiz_id}", response_model=schemas.QuizResponse)
async def get_quiz(quiz_id: UUID, db: AsyncSession = Depends(get_db_session)):
    """
    Retrieve a specific quiz by its ID.
    """
    quiz = await quiz_service.get_quiz_by_id(quiz_id, db)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    return quiz

@router.post("/{quiz_id}/submit", response_model=schemas.QuizSubmissionResponse)
async def submit_quiz(
    quiz_id: UUID,
    submission: schemas.QuizSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Submit answers for a quiz and receive a score.
    
    The `answers` field should contain a list of integers corresponding to the selected
    option index for each question in order.
    """
    score = await quiz_service.submit_quiz(quiz_id, current_user, submission.answers, db)
    if score is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission error: Check that the quiz exists and all questions have been answered."
        )
    return schemas.QuizSubmissionResponse(score=score, message="Quiz submitted successfully.")

@router.post("", response_model=schemas.QuizResponse)
async def create_quiz(
    quiz_request: schemas.QuizCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    quiz_data = quiz_request.model_dump()
    new_quiz = await quiz_service.create_quiz(quiz_data, db)
    if not new_quiz:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create quiz."
        )
    return new_quiz

@router.put("/{quiz_id}", response_model=schemas.QuizResponse)
async def update_quiz(
    quiz_id: UUID,
    quiz_request: schemas.QuizUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    quiz_data = quiz_request.model_dump()
    updated_quiz = await quiz_service.update_quiz(quiz_id, quiz_data, db)
    if not updated_quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found."
        )
    return updated_quiz

@router.delete("/{quiz_id}", response_model=dict)
async def delete_quiz(
    quiz_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    ensure_instructor_or_admin(current_user)
    success = await quiz_service.delete_quiz(quiz_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found."
        )
    return {"message": "Quiz deleted successfully."}
