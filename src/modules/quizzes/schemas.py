# src/quizzes/schemas.py

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

class QuizQuestionResponse(BaseModel):
    id: UUID
    question: str
    options: List[str]
    # Typically, you wouldn't send the correct answer in a quiz retrieval endpoint.
    # You may choose to omit this field or set it to None.
    order: int

    class Config:
        from_attributes = True

class QuizResponse(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    description: Optional[str] = None
    time_limit: int  # in minutes
    quiz_questions: List[QuizQuestionResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class QuizSubmissionRequest(BaseModel):
    answers: List[int]  # Each element is the index of the selected option for each question

class QuizSubmissionResponse(BaseModel):
    score: float
    message: str

class QuizCreateRequest(BaseModel):
    course_id: UUID
    title: str
    description: Optional[str] = None
    time_limit: int  # in minutes

    class Config:
        from_attributes = True

class QuizUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    time_limit: Optional[int] = None

    class Config:
        from_attributes = True

class QuizSummaryResponse(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    time_limit: int  # in minutes
    questions_count: int = 0
    completed: bool = False

    class Config:
        from_attributes = True

class CourseQuizzesResponse(BaseModel):
    course_id: UUID
    course_title: str
    quizzes: List[QuizSummaryResponse]

    class Config:
        from_attributes = True