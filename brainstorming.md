# Achievements and Notifications Brainstorming

## Existing Achievements
1. **First Steps**: Complete your first lesson
2. **Course Champion**: Complete an entire course
3. **Quiz Master**: Score 90% or higher on 5 quizzes
4. **Dedicated Learner**: Log in for 7 consecutive days
5. **Knowledge Seeker**: Enroll in 5 courses
6. **Fast Learner**: Complete 10 lessons in one day
7. **Perfect Score**: Get 100% on a quiz
8. **Discussion Starter**: Create your first discussion topic
9. **Helper**: Reply to 10 discussions
10. **Milestone**: Reach 1000 XP

## Existing Notification Types
- `INFO`
- `SUCCESS`
- `WARNING`
- `ERROR`

## Proposed Triggers
1. **Course Completion**: When a user's progress for a `UserCourse` hits 100%, we award **"Course Champion"** and send a `SUCCESS` notification: *"Congratulations! You have completed [Course Name]."*.
2. **First Lesson Completion**: When a newly enrolled user finishes their very first module/lesson, award **"First Steps"** and send a `SUCCESS` notification.
3. **XP Milestones**: When checking or adding XP, if `total_xp >= 1000`, award **"Milestone"** and notify them.
4. **Quiz Submissions**: After grading a quiz, if it's 100%, award **"Perfect Score"**. If it's their 5th time scoring >90%, award **"Quiz Master"**. Send an `INFO` or `SUCCESS` notification for the quiz result.
5. **Enrollment**: When a user purchases or joins a course, send an `INFO` notification: *"You are now enrolled in [Course Name]. Happy learning!"*. If this is their 5th active course, award **"Knowledge Seeker"**.
