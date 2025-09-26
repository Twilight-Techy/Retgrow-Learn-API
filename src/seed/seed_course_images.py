# scripts/seed_course_images.py
"""
Seed script to update courses' image_url fields with Unsplash images.

Usage:
    python scripts/seed_course_images.py

Notes:
- This script expects an AsyncSession factory named `async_session` to be importable.
  Adjust the import path below if your DB module lives elsewhere.
- It fetches all courses from the database and assigns appropriate Unsplash images
  based on course titles or general programming/education themes.
"""

import asyncio
from sqlalchemy import text
from typing import Dict, List
import re

# Adjust this import if your DB file/module path differs.
try:
    from src.common.database.database import async_session
except Exception as e:
    raise ImportError(
        "Couldn't import async_session from src.common.database. "
        "Adjust the import path to point to your DB module.\n"
        f"Original error: {e}"
    )


# Specific mappings for exact course titles (takes priority)
EXACT_COURSE_MAPPINGS: Dict[str, str] = {
    # Web Development Courses
    "HTML & CSS Fundamentals": "https://images.unsplash.com/photo-1627398242454-45a1465c2479?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "JavaScript Mastery": "https://images.unsplash.com/photo-1579468118864-1b9ea3c0db4a?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "React.js Complete Guide": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Node.js Backend Development": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    
    # Data Science Courses  
    "Python for Data Science": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Statistical Analysis": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Machine Learning Basics": "https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Deep Learning with TensorFlow": "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    
    # Mobile Development Courses
    "React Native Fundamentals": "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Flutter Development": "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Mobile UI/UX Design": "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    
    # Cloud Computing Courses
    "AWS Essentials": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Docker & Containerization": "https://images.unsplash.com/photo-1518432031352-d6fc5c10da5a?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Kubernetes Orchestration": "https://images.unsplash.com/photo-1518432031352-d6fc5c10da5a?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "CI/CD Pipeline Design": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
}

# Fallback images for different course categories/keywords
CATEGORY_KEYWORDS: Dict[str, str] = {
    "python": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "javascript": "https://images.unsplash.com/photo-1579468118864-1b9ea3c0db4a?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "react": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "web": "https://images.unsplash.com/photo-1627398242454-45a1465c2479?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "mobile": "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "data": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "machine learning": "https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "ai": "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "cloud": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "aws": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "docker": "https://images.unsplash.com/photo-1518432031352-d6fc5c10da5a?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "database": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "security": "https://images.unsplash.com/photo-1555949963-f7fe5b4b6c0a?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "devops": "https://images.unsplash.com/photo-1518432031352-d6fc5c10da5a?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "design": "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "ui": "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "ux": "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
}

# Default fallback image for programming/education
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb"


def get_image_for_course(title: str, description: str = "") -> str:
    """
    Determine the best Unsplash image for a course based on its title and description.
    Priority: 
    1. Exact title match
    2. Keyword matching in title/description
    3. Default fallback
    """
    
    # First, check for exact course title matches
    if title in EXACT_COURSE_MAPPINGS:
        return EXACT_COURSE_MAPPINGS[title]
    
    # If no exact match, fall back to keyword matching
    content = f"{title} {description}".lower()
    
    # Check for specific keywords in title and description
    for keyword, image_url in CATEGORY_KEYWORDS.items():
        if keyword in content:
            return image_url
    
    # Return default programming/education image
    return DEFAULT_IMAGE


async def fetch_all_courses(session) -> List[tuple]:
    """Fetch all courses from the database."""
    stmt = text("SELECT id, title, description, image_url FROM courses ORDER BY created_at")
    result = await session.execute(stmt)
    return result.fetchall()


async def update_course_images(session):
    """Update image_url for all courses."""
    
    # Fetch all courses
    courses = await fetch_all_courses(session)
    
    if not courses:
        print("No courses found in the database.")
        return
    
    print(f"Found {len(courses)} courses in the database.")
    print("Updating course images...\n")
    
    updated_count = 0
    
    for course in courses:
        course_id, title, description, current_image_url = course
        
        # Get appropriate image for this course
        new_image_url = get_image_for_course(title, description or "")
        
        # Skip if image is already set to avoid unnecessary updates
        if current_image_url == new_image_url:
            print(f"✓ {title} - Image already up to date")
            continue
        
        print(f"📝 {title}")
        print(f"   Setting image: {new_image_url}")
        
        # Update the course image
        update_stmt = text(
            "UPDATE courses "
            "SET image_url = :image_url, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = :course_id"
        )
        
        await session.execute(update_stmt, {
            "image_url": new_image_url,
            "course_id": course_id
        })
        
        updated_count += 1
    
    # Commit all changes
    await session.commit()
    
    print(f"\n✅ Successfully updated {updated_count} courses with new images.")
    print("All changes have been committed to the database.")


async def main():
    """Main function to run the course image seeding."""
    print("🚀 Starting course image seeding process...\n")
    
    async with async_session() as session:
        try:
            await update_course_images(session)
        except Exception as exc:
            await session.rollback()
            print("❌ Error occurred while updating course images. Transaction rolled back.")
            print(f"Error details: {exc}")
            raise
        finally:
            print("\n🏁 Course image seeding process completed.")


if __name__ == "__main__":
    asyncio.run(main())