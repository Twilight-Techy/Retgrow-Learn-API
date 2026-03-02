# Achievements & Notifications Documentation

This document outlines the existing achievement milestones and notification event formats implemented in the Retgrow-Learn platform.

## 🏆 Achievements Overview

Achievements are unlocked automatically when users hit specific milestones on the platform. The following are the current implemented achievements:

| Achievement | Description | Trigger |
| :--- | :--- | :--- |
| **First Steps** | Complete your first lesson | Completing 1 total lesson |
| **Course Champion** | Complete an entire course | Reaching 100% progress on a course |
| **Quiz Master** | Score 90% or higher on 5 quizzes | High score performance tracking |
| **Dedicated Learner** | Log in for 7 consecutive days | Daily login streak event |
| **Knowledge Seeker** | Enroll in 5 courses | Active total enrollments |
| **Fast Learner** | Complete 10 lessons in one day | Daily completion rate |
| **Perfect Score** | Get 100% on a quiz | Flawless quiz completion |
| **Discussion Starter**| Create your first discussion topic| Community engagement |
| **Helper** | Reply to 10 discussions | Community assistance count |
| **Milestone** | Reach 1000 XP | Experience points tracker |

---

## 🔔 Notification Types

Notifications are broadcasted to the user via Server-Sent Events (SSE) and fall into four severity categories:
- `INFO`: General system updates or curriculum changes.
- `SUCCESS`: Positive milestones or feature unlocks.
- `WARNING`: Actions requiring user attention.
- `ERROR`: System failures or access issues.

### Global Notification Events

The following standard notification templates are actively structured in the system:

#### Success Events
* **New Features Released!** - We've just launched several new features including enhanced analytics and improved course navigation. Check them out!
* **Achievement Unlocked!** - Congratulations! You've earned the [Name] achievement for [Condition].
* **Track Milestone Achieved** - You're making great progress! You've completed 50% of the courses in this track. Keep up the excellent work!
* **Course Completion Milestone** - Congratulations! Over 1,000 students have completed this course. Join the community of successful learners!

#### Info Events
* **Platform Maintenance Scheduled** - We will be performing scheduled maintenance on Saturday from 2 AM to 4 AM UTC. Some features may be temporarily unavailable.
* **Track Curriculum Updated** - We've updated the learning path for this track based on industry feedback. New courses have been added to enhance your learning experience.
* **Welcome to the Platform!** - We're excited to have you here. Start by exploring your dashboard and enrolling in your first course.
* **New Course Content Available** - Three new lessons have been added to this course. Check out the latest modules in the curriculum section.

#### Warning Events
* **Profile Incomplete** - Your profile is missing some important information. Complete your profile to get personalized course recommendations.
* **System Update Required** - Please update your mobile app to the latest version to ensure compatibility with new features.
* **Assignment Deadline Approaching** - Your final project for this course is due in 3 days. Make sure to submit before the deadline to receive credit.

#### Error Events
* **Course Access Issue** - There was a problem accessing some course materials. Our team is working on a fix. Please try again later.
* **Payment Method Expired** - Your payment method on file has expired. Please update your billing information to continue accessing premium content.
