from typing import List
import uuid
import enum

from sqlalchemy import (
    ARRAY, JSON, Boolean, Column, Float, ForeignKey, Integer, Numeric, String, Text, DateTime,
    Enum as SAEnum, UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship, backref, Mapped

Base = declarative_base()

class UserRole(enum.Enum):
    STUDENT = "student"
    TUTOR = "tutor"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    verification_code = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(255), nullable=True)
    xp = Column(Integer, default=0)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.STUDENT)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email}, is_verified={self.is_verified} role={self.role.value})>"
    
class UserLogin(Base):
    __tablename__ = "user_logins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    # login_at will be set automatically when the login record is created.
    login_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationship back to the User model (parent)
    user: Mapped[User] = relationship("User", backref=backref("logins", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<UserLogin(id={self.id}, user_id={self.user_id}, login_at={self.login_at})>"

class Track(Base):
    __tablename__ = "tracks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    level = Column(String(50), nullable=False, default="Beginner to Advanced")
    duration = Column(String(50), nullable=True)
    prerequisites = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Courses relationship defined through TrackCourse association table
    courses: Mapped[List["Course"]] = relationship(
        "Course",
        secondary="track_courses",
        backref="tracks"
    )

    def __repr__(self):
        return f"<Track(id={self.id}, title={self.title}, level={self.level})>"

class CourseLevel(enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    level = Column(SAEnum(CourseLevel), nullable=False)
    duration = Column(String(50), nullable=True)
    price = Column(Numeric(10, 2), nullable=False, default=0.00)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # The modules relationship is defined with backref in Course (parent)
    modules: Mapped[List["Module"]] = relationship(
        "Module",        
        order_by="Module.order",
        backref="course",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Course(id={self.id}, title={self.title}>"
    
class TrackCourse(Base):
    __tablename__ = "track_courses"

    # Composite primary key: track_id and course_id together uniquely identify a record.
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), primary_key=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), primary_key=True)
    order = Column(Integer, nullable=False)

    # Define relationships to Track and Course models
    track: Mapped[Track] = relationship("Track", backref=backref("course_associations", cascade="all, delete-orphan"))
    course: Mapped[Course] = relationship("Course", backref=backref("track_associations", cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f"<TrackCourse(track_id={self.track_id}, course_id={self.course_id}, order={self.order})>"

class Module(Base):
    __tablename__ = "modules"

    __table_args__ = (
        UniqueConstraint('course_id', 'order', name='unique_course_module_order'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Lessons relationship (Module is parent)
    lessons: Mapped[List["Lesson"]] = relationship(
        "Lesson",
        order_by="Lesson.order",
        backref="module",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Module(id={self.id}, title={self.title}, order={self.order}, course_id={self.course_id})>"

class Lesson(Base):
    __tablename__ = "lessons"

    __table_args__ = (
        UniqueConstraint('module_id', 'order', name='unique_module_lesson_order'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    video_url = Column(String(255), nullable=True)
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Lesson(id={self.id}, title={self.title}, order={self.order}, module_id={self.module_id})>"

class UserCourse(Base):
    __tablename__ = "user_courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True)
    progress = Column(Float, nullable=False, default=0.0)
    enrolled_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships to the User and Course models
    user: Mapped[User] = relationship("User", backref=backref("user_courses", cascade="all, delete-orphan"))
    course: Mapped[Course] = relationship("Course", backref=backref("user_courses", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<UserCourse(id={self.id}, user_id={self.user_id}, course_id={self.course_id}, progress={self.progress})>"

class UserLesson(Base):
    __tablename__ = "user_lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships to the User and Lesson models
    user: Mapped[User] = relationship("User", backref=backref("user_lessons", cascade="all, delete-orphan"))
    lesson: Mapped[Lesson] = relationship("Lesson", backref=backref("user_lessons", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<UserLesson(id={self.id}, user_id={self.user_id}, lesson_id={self.lesson_id}, completed_at={self.completed_at})>"

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    time_limit = Column(Integer, nullable=False)  # Time limit in minutes
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationship: A Quiz belongs to a Course
    course: Mapped[Course] = relationship("Course", backref="quizzes")

    # QuizQuestion relationship (Quiz is parent)
    quiz_questions = relationship(
        "QuizQuestion",
        backref="quiz",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Quiz(id={self.id}, title={self.title}, course_id={self.course_id})>"

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # Array of option strings stored as JSON
    correct_answer = Column(Integer, nullable=False)  # Index of the correct option
    order = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<QuizQuestion(id={self.id}, quiz_id={self.quiz_id}, order={self.order})>"

class UserQuiz(Base):
    __tablename__ = "user_quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False, index=True)
    score = Column(Float, nullable=False, default=0.0)
    completed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships: A UserQuiz links a User and a Quiz
    user: Mapped[User] = relationship("User", backref=backref("user_quizzes", cascade="all, delete-orphan"))
    quiz: Mapped[Quiz] = relationship("Quiz", backref=backref("user_quizzes", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<UserQuiz(id={self.id}, user_id={self.user_id}, quiz_id={self.quiz_id}, score={self.score})>"
    
class CourseQuiz(Base):
    __tablename__ = "course_quizzes"

    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), primary_key=True)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), primary_key=True)
    order = Column(Integer, nullable=False)

    # Relationships
    quiz: Mapped[Quiz] = relationship("Quiz", backref=backref("course_associations", cascade="all, delete-orphan"))
    course: Mapped[Course] = relationship("Course", backref=backref("quiz_associations", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<CourseQuiz(course_id={self.course_id}, quiz_id={self.quiz_id}, order={self.order})>"

class ResourceType(enum.Enum):
    ARTICLE = "article"
    VIDEO = "video"
    EBOOK = "ebook"
    TUTORIAL = "tutorial"

class Resource(Base):
    __tablename__ = "resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    type = Column(SAEnum(ResourceType), nullable=False)
    url = Column(String(255), nullable=False)
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationship: A Resource optionally belongs to a Track
    track: Mapped[Track] = relationship("Track", backref=backref("resources"))

    def __repr__(self):
        return f"<Resource(id={self.id}, title={self.title}, type={self.type.value}, url={self.url})>"

class UserResource(Base):
    __tablename__ = "user_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resources.id"), nullable=False, index=True)
    last_accessed = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships to the User and Resource models
    user: Mapped[User] = relationship("User", backref=backref("user_resources", cascade="all, delete-orphan"))
    resource: Mapped[Resource] = relationship("Resource", backref=backref("user_resources", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<UserResource(id={self.id}, user_id={self.user_id}, resource_id={self.resource_id}, last_accessed={self.last_accessed})>"

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, 
                        server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Achievement(id={self.id}, title={self.title})>"

class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    achievement_id = Column(UUID(as_uuid=True), ForeignKey("achievements.id"), nullable=False, index=True)
    earned_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships: A UserAchievement links a User and an Achievement
    user: Mapped[User] = relationship("User", backref=backref("user_achievements", cascade="all, delete-orphan"))
    achievement: Mapped[Achievement] = relationship("Achievement", backref=backref("user_achievements", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<UserAchievement(id={self.id}, user_id={self.user_id}, achievement_id={self.achievement_id}, earned_at={self.earned_at})>"

class NotificationType(enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(SAEnum(NotificationType), nullable=False, default=NotificationType.INFO)
    message = Column(Text, nullable=False)
    read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationship: A Notification belongs to a User
    user: Mapped[User] = relationship("User", backref=backref("notifications", cascade="all, delete-orphan"))

    def __repr__(self):
        return (f"<Notification(id={self.id}, user_id={self.user_id}, "
                f"type={self.type.value}, read={self.read}, created_at={self.created_at})>")

class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships: A Discussion is created by a User for a specific Course
    course: Mapped[Course] = relationship("Course", backref=backref("discussions", cascade="all, delete-orphan"))
    user: Mapped[User] = relationship("User", backref=backref("discussions", cascade="all, delete-orphan"))
    
    # DiscussionReply relationship (Discussion is parent)
    discussion_replies = relationship(
        "DiscussionReply",
        backref="discussion",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Discussion(id={self.id}, title={self.title}, course_id={self.course_id}, user_id={self.user_id})>"

class DiscussionReply(Base):
    __tablename__ = "discussion_replies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    discussion_id = Column(UUID(as_uuid=True), ForeignKey("discussions.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, 
                        server_default=func.now(), onupdate=func.now())

    # Relationship: A DiscussionReply is created by a User
    user: Mapped[User] = relationship("User", backref=backref("discussion_replies", cascade="all, delete-orphan"))

    def __repr__(self):
        return (f"<DiscussionReply(id={self.id}, discussion_id={self.discussion_id}, "
                f"user_id={self.user_id}, created_at={self.created_at})>")

class LearningPath(Base):
    __tablename__ = "learning_paths"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False, index=True)
    current_course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True)
    progress = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, 
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped[User] = relationship("User", backref=backref("learning_path", uselist=False, cascade="all, delete-orphan"))
    track: Mapped[Track] = relationship("Track", backref=backref("learning_paths", cascade="all, delete-orphan"))
    current_course: Mapped[Course] = relationship("Course", backref=backref("learning_paths"))

    def __repr__(self):
        return (f"<LearningPath(id={self.id}, user_id={self.user_id}, "
                f"track_id={self.track_id}, current_course_id={self.current_course_id}, progress={self.progress})>")

class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Skill(id={self.id}, name={self.name})>"

class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    proficiency = Column(Float, nullable=False, default=0.0)  # Expected to be within 0-100
    last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships: A UserSkill links a User and a Skill
    user: Mapped[User] = relationship("User", backref=backref("user_skills", cascade="all, delete-orphan"))
    skill: Mapped[Skill] = relationship("Skill", backref=backref("user_skills", cascade="all, delete-orphan"))

    def __repr__(self):
        return (f"<UserSkill(id={self.id}, user_id={self.user_id}, skill_id={self.skill_id}, "
                f"proficiency={self.proficiency}, last_updated={self.last_updated})>")

class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, 
                        server_default=func.now(), onupdate=func.now())

    # Establish a relationship to the Course model (if deadlines are linked to courses)
    course: Mapped[Course] = relationship("Course", backref=backref("deadlines", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<Deadline(id={self.id}, title={self.title}, due_date={self.due_date})>"