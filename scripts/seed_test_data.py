#!/usr/bin/env python3
"""
Database Seed Script for Learning Management System

This script populates the database with sample data including users, tracks, 
courses, modules, lessons, quizzes, and all associated relationships.

Usage:
    python seed_data.py

Make sure to have your database connection configured before running.
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Add the project root directory to Python path
project_root = Path(__file__).resolve().parents[3]  # Go up 3 levels from utils folder
sys.path.insert(0, str(project_root))

# Import your database and models
try:
    from src.common.database.database import async_session, engine, connect_to_db, close_db_connection
    from src.models.models import (  # Adjust based on your actual structure
        Base, User, UserRole, Track, Course, CourseLevel, TrackCourse,
        Module, Lesson, Quiz, QuizQuestion, UserCourse, UserLesson,
        UserQuiz, Resource, ResourceType, Skill, UserSkill, Achievement,
        UserAchievement, Notification, NotificationType, Discussion,
        DiscussionReply, LearningPath, Deadline
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Please check your import paths and make sure you're running from the correct directory")
    sys.exit(1)

async def seed_users(session):
    """Create sample users"""
    print("Seeding users...")
    
    users = [
        User(
            username="john_doe",
            email="john@example.com",
            password_hash="hashedpassword123",
            first_name="John",
            last_name="Doe",
            bio="Lifelong learner, interested in Python.",
            role=UserRole.STUDENT,
            is_verified=True,
            xp=150
        ),
        User(
            username="jane_tutor",
            email="jane@example.com",
            password_hash="hashedpassword456",
            first_name="Jane",
            last_name="Smith",
            bio="Tutor with 5+ years in Data Science.",
            role=UserRole.TUTOR,
            is_verified=True,
            xp=500
        ),
        User(
            username="admin_guy",
            email="admin@example.com",
            password_hash="hashedpassword789",
            first_name="Adam",
            last_name="Admin",
            bio="System admin.",
            role=UserRole.ADMIN,
            is_verified=True,
            xp=1000
        )
    ]
    
    session.add_all(users)
    await session.flush()  # Flush to get IDs without committing
    return users

async def seed_tracks(session):
    """Create sample tracks"""
    print("Seeding tracks...")
    
    tracks = [
        Track(
            slug="python-data-science",
            title="Python for Data Science",
            description="Learn Python, NumPy, Pandas, and Machine Learning.",
            level="Beginner to Advanced",
            duration="6 months",
            prerequisites=["Basic math", "Logical reasoning"]
        ),
        Track(
            slug="web-dev-bootcamp",
            title="Fullstack Web Development",
            description="HTML, CSS, JavaScript, React, and Django.",
            level="Beginner",
            duration="4 months",
            prerequisites=["Basic computer literacy"]
        )
    ]
    
    session.add_all(tracks)
    await session.flush()
    return tracks

async def seed_courses(session):
    """Create sample courses"""
    print("Seeding courses...")
    
    courses = [
        Course(
            title="Intro to Python",
            description="Python basics: variables, loops, functions.",
            level=CourseLevel.BEGINNER,
            duration="4 weeks",
            price=0.00
        ),
        Course(
            title="Machine Learning Foundations",
            description="Regression, classification, clustering.",
            level=CourseLevel.INTERMEDIATE,
            duration="8 weeks",
            price=49.99
        ),
        Course(
            title="Frontend Development",
            description="HTML, CSS, and modern JavaScript.",
            level=CourseLevel.BEGINNER,
            duration="6 weeks",
            price=29.99
        )
    ]
    
    session.add_all(courses)
    await session.flush()
    return courses

async def seed_track_courses(session, tracks, courses):
    """Create track-course associations"""
    print("Seeding track-course associations...")
    
    track_courses = [
        TrackCourse(track_id=tracks[0].id, course_id=courses[0].id, order=1),
        TrackCourse(track_id=tracks[0].id, course_id=courses[1].id, order=2),
        TrackCourse(track_id=tracks[1].id, course_id=courses[2].id, order=1),
    ]
    
    session.add_all(track_courses)
    await session.flush()
    return track_courses

async def seed_modules(session, courses):
    """Create sample modules"""
    print("Seeding modules...")
    
    modules = [
        Module(course_id=courses[0].id, title="Python Basics", order=1),
        Module(course_id=courses[0].id, title="Control Flow", order=2),
        Module(course_id=courses[2].id, title="HTML & CSS", order=1),
    ]
    
    session.add_all(modules)
    await session.flush()
    return modules

async def seed_lessons(session, modules):
    """Create sample lessons"""
    print("Seeding lessons...")
    
    lessons = [
        Lesson(
            module_id=modules[0].id, 
            title="Intro to Python", 
            content="What is Python? Python is a high-level programming language...", 
            order=1
        ),
        Lesson(
            module_id=modules[0].id, 
            title="Variables & Types", 
            content="Learn about variables. Variables are containers for data...", 
            order=2
        ),
        Lesson(
            module_id=modules[1].id, 
            title="If Statements", 
            content="Conditional logic. If statements allow you to make decisions...", 
            order=1
        ),
        Lesson(
            module_id=modules[2].id, 
            title="HTML Basics", 
            content="Tags and structure. HTML uses tags to define elements...", 
            order=1
        ),
    ]
    
    session.add_all(lessons)
    await session.flush()
    return lessons

async def seed_quizzes(session, courses):
    """Create sample quizzes"""
    print("Seeding quizzes...")
    
    quizzes = [
        Quiz(
            course_id=courses[0].id, 
            title="Python Basics Quiz", 
            description="Test your knowledge of Python fundamentals.", 
            time_limit=30
        )
    ]
    
    session.add_all(quizzes)
    await session.flush()
    return quizzes

async def seed_quiz_questions(session, quizzes):
    """Create sample quiz questions"""
    print("Seeding quiz questions...")
    
    quiz_questions = [
        QuizQuestion(
            quiz_id=quizzes[0].id, 
            question="What is Python?", 
            options=["A snake", "A programming language", "A car brand", "A type of food"], 
            correct_answer=1, 
            order=1
        ),
        QuizQuestion(
            quiz_id=quizzes[0].id, 
            question="Which keyword defines a function in Python?", 
            options=["func", "def", "lambda", "function"], 
            correct_answer=1, 
            order=2
        )
    ]
    
    session.add_all(quiz_questions)
    await session.flush()
    return quiz_questions

async def seed_resources(session, tracks):
    """Create sample resources"""
    print("Seeding resources...")
    
    resources = [
        Resource(
            title="NumPy Documentation", 
            description="Official NumPy documentation and tutorials",
            type=ResourceType.ARTICLE, 
            url="https://numpy.org/doc/", 
            track_id=tracks[0].id
        ),
        Resource(
            title="CSS Tricks Video Series", 
            description="Comprehensive CSS tutorials and tricks",
            type=ResourceType.VIDEO, 
            url="https://youtube.com/css_tricks", 
            track_id=tracks[1].id
        ),
    ]
    
    session.add_all(resources)
    await session.flush()
    return resources

async def seed_skills(session):
    """Create sample skills"""
    print("Seeding skills...")
    
    skills = [
        Skill(name="Python", description="General-purpose programming language"),
        Skill(name="Machine Learning", description="Predictive modeling and artificial intelligence"),
        Skill(name="Web Development", description="Frontend and backend web technologies")
    ]
    
    session.add_all(skills)
    await session.flush()
    return skills

async def seed_achievements(session):
    """Create sample achievements"""
    print("Seeding achievements...")
    
    achievements = [
        Achievement(
            title="First Login", 
            description="You logged in for the first time!",
            icon_url="https://example.com/icons/first_login.png"
        ),
        Achievement(
            title="Course Complete", 
            description="You completed your first course.",
            icon_url="https://example.com/icons/course_complete.png"
        ),
        Achievement(
            title="Quiz Master", 
            description="You scored 100% on a quiz.",
            icon_url="https://example.com/icons/quiz_master.png"
        )
    ]
    
    session.add_all(achievements)
    await session.flush()
    return achievements

async def seed_user_progress(session, users, courses, lessons, quizzes, skills, achievements):
    """Create user progress records"""
    print("Seeding user progress...")
    
    # User course enrollments
    user_courses = [
        UserCourse(user_id=users[0].id, course_id=courses[0].id, progress=50.0),
        UserCourse(user_id=users[0].id, course_id=courses[2].id, progress=20.0),
    ]
    session.add_all(user_courses)
    
    # User lesson completions
    user_lessons = [
        UserLesson(user_id=users[0].id, lesson_id=lessons[0].id),
        UserLesson(user_id=users[0].id, lesson_id=lessons[1].id),
    ]
    session.add_all(user_lessons)
    
    # User quiz attempts
    user_quizzes = [
        UserQuiz(user_id=users[0].id, quiz_id=quizzes[0].id, score=80.0)
    ]
    session.add_all(user_quizzes)
    
    # User skills
    user_skills = [
        UserSkill(user_id=users[0].id, skill_id=skills[0].id, proficiency=60.0),
        UserSkill(user_id=users[0].id, skill_id=skills[1].id, proficiency=30.0),
        UserSkill(user_id=users[1].id, skill_id=skills[0].id, proficiency=90.0),
        UserSkill(user_id=users[1].id, skill_id=skills[1].id, proficiency=85.0),
    ]
    session.add_all(user_skills)
    
    # User achievements
    user_achievements = [
        UserAchievement(user_id=users[0].id, achievement_id=achievements[0].id),
        UserAchievement(user_id=users[1].id, achievement_id=achievements[0].id),
        UserAchievement(user_id=users[1].id, achievement_id=achievements[1].id),
    ]
    session.add_all(user_achievements)
    
    await session.flush()

async def seed_notifications(session, users):
    """Create sample notifications"""
    print("Seeding notifications...")
    
    notifications = [
        Notification(
            user_id=users[0].id, 
            type=NotificationType.SUCCESS, 
            message="You completed your first lesson! Keep up the great work."
        ),
        Notification(
            user_id=users[0].id, 
            type=NotificationType.INFO, 
            message="New course available in your track: Advanced Python Techniques"
        ),
        Notification(
            user_id=users[1].id, 
            type=NotificationType.WARNING, 
            message="Don't forget to update your course materials"
        )
    ]
    
    session.add_all(notifications)
    await session.flush()
    return notifications

async def seed_discussions(session, courses, users):
    """Create sample discussions"""
    print("Seeding discussions...")
    
    discussions = [
        Discussion(
            course_id=courses[0].id, 
            user_id=users[0].id, 
            title="Question about loops", 
            content="Can someone explain the difference between while loops and for loops?"
        )
    ]
    session.add_all(discussions)
    await session.flush()
    
    # Discussion replies
    discussion_replies = [
        DiscussionReply(
            discussion_id=discussions[0].id, 
            user_id=users[1].id, 
            content="Sure! While loops repeat until a condition is false, whereas for loops iterate over a sequence."
        )
    ]
    session.add_all(discussion_replies)
    await session.flush()
    
    return discussions, discussion_replies

async def seed_learning_paths(session, users, tracks, courses):
    """Create sample learning paths"""
    print("Seeding learning paths...")
    
    learning_paths = [
        LearningPath(
            user_id=users[0].id,
            track_id=tracks[0].id,
            current_course_id=courses[0].id,
            progress=25.0
        )
    ]
    
    session.add_all(learning_paths)
    await session.flush()
    return learning_paths

async def seed_deadlines(session, courses):
    """Create sample deadlines"""
    print("Seeding deadlines...")
    
    deadlines = [
        Deadline(
            title="Python Basics Assignment",
            description="Complete all exercises in the Python Basics module",
            due_date=datetime(2025, 10, 15, 23, 59, 59, tzinfo=timezone.utc),
            course_id=courses[0].id
        ),
        Deadline(
            title="Frontend Project Submission",
            description="Submit your final frontend project",
            due_date=datetime(2025, 11, 30, 23, 59, 59, tzinfo=timezone.utc),
            course_id=courses[2].id
        )
    ]
    
    session.add_all(deadlines)
    await session.flush()
    return deadlines

async def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully!")

async def main():
    """Main seeding function"""
    print("Starting database seeding...")
    
    try:
        # Connect to database
        await connect_to_db()
        
        # Create tables if they don't exist
        await create_tables()
        
        # Create session and seed data
        async with async_session() as session:
            try:
                # Seed data in order of dependencies
                users = await seed_users(session)
                tracks = await seed_tracks(session)
                courses = await seed_courses(session)
                track_courses = await seed_track_courses(session, tracks, courses)
                modules = await seed_modules(session, courses)
                lessons = await seed_lessons(session, modules)
                quizzes = await seed_quizzes(session, courses)
                quiz_questions = await seed_quiz_questions(session, quizzes)
                resources = await seed_resources(session, tracks)
                skills = await seed_skills(session)
                achievements = await seed_achievements(session)
                
                # Seed user progress and relationships
                await seed_user_progress(session, users, courses, lessons, quizzes, skills, achievements)
                notifications = await seed_notifications(session, users)
                discussions, discussion_replies = await seed_discussions(session, courses, users)
                learning_paths = await seed_learning_paths(session, users, tracks, courses)
                deadlines = await seed_deadlines(session, courses)
                
                # Commit all changes
                await session.commit()
                print("✅ Database seeding completed successfully!")
                
                # Print summary
                print(f"\nSeeded data summary:")
                print(f"- Users: {len(users)}")
                print(f"- Tracks: {len(tracks)}")
                print(f"- Courses: {len(courses)}")
                print(f"- Modules: {len(modules)}")
                print(f"- Lessons: {len(lessons)}")
                print(f"- Quizzes: {len(quizzes)}")
                print(f"- Quiz Questions: {len(quiz_questions)}")
                print(f"- Resources: {len(resources)}")
                print(f"- Skills: {len(skills)}")
                print(f"- Achievements: {len(achievements)}")
                print(f"- Notifications: {len(notifications)}")
                print(f"- Discussions: {len(discussions)}")
                print(f"- Learning Paths: {len(learning_paths)}")
                print(f"- Deadlines: {len(deadlines)}")
                
            except Exception as e:
                print(f"❌ Error during seeding: {e}")
                await session.rollback()
                raise
                
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        # Close database connection
        await close_db_connection()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())