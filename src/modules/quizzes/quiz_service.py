# src/quizzes/quiz_service.py

from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from src.models.models import Course, CourseQuiz, LearningPath, Quiz, QuizQuestion, TrackCourse, UserQuiz, User

async def get_all_quizzes(db: AsyncSession) -> List[Quiz]:
    result = await db.execute(select(Quiz))
    quizzes = result.scalars().all()
    return quizzes

async def get_quizzes_by_track(user_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Retrieve quizzes for the track the user is enrolled in.
    
    Steps:
      1. Get the active learning path for the user (i.e. where completed_at is None).
      2. Retrieve courses for the track via the TrackCourse association, ordered by TrackCourse.order.
      3. For each course, retrieve CourseQuiz records (ordered by CourseQuiz.order) and, via that, the associated quizzes.
      4. Group the quizzes by course.
    """
    # 1. Get the active learning path.
    lp_result = await db.execute(
        select(LearningPath).where(
            LearningPath.user_id == user_id,
            LearningPath.completed_at.is_(None)
        )
    )
    learning_path = lp_result.scalars().first()
    if not learning_path:
        return []

    # 2. Retrieve courses for the track using the TrackCourse association.
    tc_stmt = (
        select(TrackCourse)
        .where(TrackCourse.track_id == learning_path.track_id)
        .order_by(TrackCourse.order.asc())
    )
    tc_result = await db.execute(tc_stmt)
    track_course_records = tc_result.scalars().all()

    # Build a mapping for each course using the order from TrackCourse.
    course_quiz_map = {}
    for tc in track_course_records:
        course = tc.course  # Assumes TrackCourse has a relationship to Course.
        course_quiz_map[str(course.id)] = {
            "course_id": course.id,
            "course_title": course.title,
            "order": tc.order,
            "quizzes": []
        }

    # 3. For each course, retrieve quizzes via the CourseQuiz association, ordered by CourseQuiz.order.
    for course_id_str in course_quiz_map.keys():
        cq_stmt = (
            select(CourseQuiz)
            .where(CourseQuiz.course_id == course_id_str)
            .order_by(CourseQuiz.order.asc())
        )
        cq_result = await db.execute(cq_stmt)
        course_quiz_records = cq_result.scalars().all()
        for cq in course_quiz_records:
            # Each CourseQuiz record contains a relationship to Quiz.
            quiz = cq.quiz
            course_quiz_map[course_id_str]["quizzes"].append(quiz)

    # 4. Convert the mapping to a list sorted by the course order.
    courses_quizzes = sorted(list(course_quiz_map.values()), key=lambda x: x["order"])
    return courses_quizzes

async def get_quiz_by_id(quiz_id: str, db: AsyncSession) -> Optional[Quiz]:
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalars().first()
    return quiz

async def submit_quiz(quiz_id: str, current_user: User, answers: List[int], db: AsyncSession) -> Optional[float]:
    """
    Process quiz submission for the given quiz and user.
    - Retrieve quiz questions ordered by their defined order.
    - Compare the submitted answers with the correct answers.
    - Compute a score as a percentage.
    - Save the submission in the UserQuiz table.
    """
    # Retrieve quiz questions for the given quiz, ordered by the 'order' field.
    result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.order)
    )
    questions = result.scalars().all()
    if not questions or len(answers) != len(questions):
        return None  # Either quiz not found or submission does not match question count.

    correct_count = 0
    for question, submitted_answer in zip(questions, answers):
        if question.correct_answer == submitted_answer:
            correct_count += 1

    score = (correct_count / len(questions)) * 100.0

    # Save the quiz submission record
    new_submission = UserQuiz(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=score,
        completed_at=datetime.now(timezone.utc)
    )
    db.add(new_submission)
    await db.commit()
    return score

async def create_quiz(quiz_data: dict, db: AsyncSession) -> Quiz:
    new_quiz = Quiz(
        id=uuid.uuid4(),  # Omit if your model auto-generates the id.
        course_id=quiz_data["course_id"],
        title=quiz_data["title"],
        description=quiz_data.get("description"),
        time_limit=quiz_data["time_limit"],
    )
    db.add(new_quiz)
    await db.commit()
    await db.refresh(new_quiz)
    return new_quiz

async def update_quiz(quiz_id: str, quiz_data: dict, db: AsyncSession) -> Optional[Quiz]:
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalars().first()
    if not quiz:
        return None
    for key, value in quiz_data.items():
        if value is not None:
            setattr(quiz, key, value)
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)
    return quiz

async def delete_quiz(quiz_id: str, db: AsyncSession) -> bool:
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalars().first()
    if not quiz:
        return False
    await db.delete(quiz)
    await db.commit()
    return True
