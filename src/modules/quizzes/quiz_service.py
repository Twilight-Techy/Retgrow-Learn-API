# src/quizzes/quiz_service.py

from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import and_, func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from src.models.models import Course, CourseQuiz, LearningPath, Quiz, QuizQuestion, TrackCourse, UserCourse, UserQuiz, User

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

async def get_user_relevant_quizzes(current_user, db: AsyncSession) -> List[Dict[str, Any]]:
    user_id = current_user.id

    # A helper set to avoid duplicate quiz ids
    quiz_ids_set = set()
    # map course_id -> {course_title, order (optional), quizzes: [quiz_summary...]}
    course_map: Dict[str, Dict] = {}

    # 1) Active learning path -> track -> courses -> course_quizzes
    lp_stmt = select(LearningPath).where(LearningPath.user_id == user_id, LearningPath.completed_at.is_(None))
    lp_res = await db.execute(lp_stmt)
    learning_path = lp_res.scalars().first()

    track_course_order = {}
    if learning_path:
        tc_stmt = select(TrackCourse).where(TrackCourse.track_id == learning_path.track_id).order_by(TrackCourse.order.asc())
        tc_res = await db.execute(tc_stmt)
        tc_rows = tc_res.scalars().all()
        for tc in tc_rows:
            # Ensure the course appears in ordering map so grouping keeps the track order
            if tc.course_id:
                track_course_order[str(tc.course_id)] = tc.order

        # gather course ids from track
        track_course_ids = [tc.course_id for tc in tc_rows]
    else:
        track_course_ids = []

    # 2) User enrolled/finished courses (UserCourse)
    uc_stmt = select(UserCourse).where(UserCourse.user_id == user_id)
    uc_res = await db.execute(uc_stmt)
    uc_rows = uc_res.scalars().all()
    enrolled_course_ids = [uc.course_id for uc in uc_rows]

    # Combine course ids to fetch CourseQuiz records
    combined_course_ids = list(dict.fromkeys(track_course_ids + enrolled_course_ids))  # preserve order, unique

    # 3) Quizzes explicitly completed by user (user_quizzes) — we still need to include them even if course isn't in above lists
    uq_stmt = select(UserQuiz).where(UserQuiz.user_id == user_id)
    uq_res = await db.execute(uq_stmt)
    uq_rows = uq_res.scalars().all()
    completed_quiz_ids = [uq.quiz_id for uq in uq_rows]

    # We'll collect quiz ids from CourseQuiz for combined_course_ids
    if combined_course_ids:
        cq_stmt = select(CourseQuiz).where(CourseQuiz.course_id.in_(combined_course_ids)).order_by(CourseQuiz.order.asc())
        cq_res = await db.execute(cq_stmt)
        cq_rows = cq_res.scalars().all()
        for cq in cq_rows:
            quiz_ids_set.add(str(cq.quiz_id))

    # include completed quiz ids
    for qid in completed_quiz_ids:
        quiz_ids_set.add(str(qid))

    # If we still have no quiz ids, short-circuit with [].
    if not quiz_ids_set:
        return []

    # Convert quiz_ids_set into actual UUID objects if required by DB — dependency on DB driver, keep strings ok for comparison.
    quiz_ids_list = [uuid.UUID(qid) if isinstance(qid, str) else qid for qid in quiz_ids_set]

    # Fetch quiz metadata and question counts and course mapping
    # We'll fetch: Quiz, Course.id, Course.title, count(QuizQuestion.id), and whether user completed
    q_stmt = (
        select(
            Quiz,
            Course.id.label("course_id"),
            Course.title.label("course_title"),
            func.count(QuizQuestion.id).label("questions_count"),
        )
        .join(Course, Quiz.course_id == Course.id)
        .outerjoin(QuizQuestion, QuizQuestion.quiz_id == Quiz.id)
        .where(Quiz.id.in_(quiz_ids_list))
        .group_by(Quiz.id, Course.id, Course.title)
    )
    q_res = await db.execute(q_stmt)
    q_rows = q_res.all()

    # Fetch set of completed quiz ids for quick lookup (already have completed_quiz_ids but do canonicalization)
    completed_set = {str(x) for x in completed_quiz_ids}

    # Build course_map
    for row in q_rows:
        quiz_obj = row[0]
        course_id = str(row.course_id)
        course_title = row.course_title
        questions_count = int(row.questions_count or 0)

        quiz_summary = {
            "id": str(quiz_obj.id),
            "course_id": str(quiz_obj.course_id),
            "title": quiz_obj.title,
            "time_limit": int(quiz_obj.time_limit),
            "questions_count": questions_count,
            "completed": str(quiz_obj.id) in completed_set,
        }

        if course_id not in course_map:
            # order: prefer track order if present else 9999 so they appear after track courses
            course_map[course_id] = {
                "course_id": quiz_summary["course_id"],
                "course_title": course_title,
                "order": track_course_order.get(course_id, 9999),
                "quizzes": [quiz_summary],
            }
        else:
            course_map[course_id]["quizzes"].append(quiz_summary)

    # Sort quizzes inside each course by ??? (we'll leave as the order from CourseQuiz if present).
    # Optionally sort course_map into a list ordered by "order" then course_title
    courses_list = sorted(list(course_map.values()), key=lambda x: (x["order"], x["course_title"] or ""))

    # For each course, sort quizzes by title (or keep as-is). Here we leave as-is.
    # Convert to the shape expected by Pydantic: CourseQuizzesResponse
    result = []
    for c in courses_list:
        result.append({
            "course_id": c["course_id"],
            "course_title": c["course_title"],
            "quizzes": c["quizzes"],
        })

    return result

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
