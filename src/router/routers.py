# src/api/routers.py

from fastapi import FastAPI
from src.auth.auth_controller import router as auth_router
from src.modules.achievements.achievement_controller import router as achievements_router
from src.modules.contact.contact_controller import router as contact_router
from src.modules.courses.course_controller import router as course_router
from src.modules.dashboard.dashboard_controller import router as dashboard_router
from src.modules.deadlines.deadline_controller import router as deadline_router
from src.modules.discussions.discussion_controller import router as discussion_router
from src.modules.leaderboard.leaderboard_controller import router as leaderboard_router
from src.modules.learning_path.learning_path_controller import router as learning_path_router
from src.modules.lessons.lesson_controller import router as lesson_router
from src.modules.modules.module_controller import router as module_router
from src.modules.notifications.notification_controller import router as notification_router
from src.modules.payments.payment_controller import router as payment_router
from src.modules.payments.payment_controller import subscription_router
from src.modules.quizzes.quiz_controller import router as quiz_router
from src.modules.resources.resource_controller import router as resource_router
from src.modules.search.search_controller import router as search_router
from src.modules.tracks.track_controller import router as track_router
from src.modules.user.user_controller import router as user_router

def include_routers(app: FastAPI) -> None:
    app.include_router(auth_router)
    app.include_router(achievements_router)
    app.include_router(contact_router)
    app.include_router(course_router)
    app.include_router(dashboard_router)
    app.include_router(deadline_router)
    app.include_router(discussion_router)
    app.include_router(leaderboard_router)
    app.include_router(learning_path_router)
    app.include_router(lesson_router)
    app.include_router(module_router)
    app.include_router(notification_router)
    app.include_router(payment_router)
    app.include_router(subscription_router)
    app.include_router(quiz_router)
    app.include_router(resource_router)
    app.include_router(search_router)
    app.include_router(track_router)
    app.include_router(user_router)

