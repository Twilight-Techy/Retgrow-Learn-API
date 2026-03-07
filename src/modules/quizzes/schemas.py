# src/quizzes/schemas.py

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import ConfigDict, BaseModel

class QuizQuestionResponse(BaseModel):
    id: UUID
    question: str
    options: List[str]
    # Typically, you wouldn't send the correct answer in a quiz retrieval endpoint.
    # You may choose to omit this field or set it to None.
    order: int
    model_config = ConfigDict(from_attributes=True)

class QuizResponse(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    description: Optional[str] = None
    time_limit: int  # in minutes
    quiz_questions: List[QuizQuestionResponse] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class QuizSubmissionRequest(BaseModel):
    answers: List[int]  # Each element is the index of the selected option for each question

class QuizQuestionAnswerResponse(BaseModel):
    question_id: UUID
    correct_answer: int
    model_config = ConfigDict(from_attributes=True)

class QuizSubmissionResponse(BaseModel):
    score: float
    message: str
    # ordered list of correct answers (matching question order returned by the quiz)
    correct_answers: List[QuizQuestionAnswerResponse]
    model_config = ConfigDict(from_attributes=True)

class QuizCreateRequest(BaseModel):
    course_id: UUID
    title: str
    description: Optional[str] = None
    time_limit: int  # in minutes
    model_config = ConfigDict(from_attributes=True)

class QuizUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    time_limit: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class QuizSummaryResponse(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    time_limit: int  # in minutes
    questions_count: int = 0
    completed: bool = False
    model_config = ConfigDict(from_attributes=True)

class CourseQuizzesResponse(BaseModel):
    course_id: UUID
    course_title: str
    quizzes: List[QuizSummaryResponse]
    model_config = ConfigDict(from_attributes=True)