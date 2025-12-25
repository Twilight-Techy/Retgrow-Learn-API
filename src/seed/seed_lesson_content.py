"""
Seed script to populate lesson content with rich, educational material.

Usage:
    python scripts/seed_lesson_content.py

Notes:
- This script generates diverse educational content using various block types
- Content is tailored based on lesson titles and order
- Adjust the import path if your DB module lives elsewhere
"""

import asyncio
import uuid
from sqlalchemy import text
from typing import Dict, List, Any
import json

# Adjust this import if your DB file/module path differs
try:
    from src.common.database.database import async_session
except Exception as e:
    raise ImportError(
        "Couldn't import async_session from src.common.database. "
        "Adjust the import path to point to your DB module.\n"
        f"Original error: {e}"
    )


def generate_block_id() -> str:
    """Generate a unique ID for content blocks."""
    return str(uuid.uuid4())


def create_heading(level: int, text: str) -> Dict[str, Any]:
    """Create a heading block."""
    return {
        "id": generate_block_id(),
        "type": "heading",
        "content": {
            "level": level,
            "text": text
        }
    }


def create_text(html: str) -> Dict[str, Any]:
    """Create a text block with HTML content."""
    return {
        "id": generate_block_id(),
        "type": "text",
        "content": {
            "html": html
        }
    }


def create_code(code: str, language: str, caption: str = None) -> Dict[str, Any]:
    """Create a code block."""
    block = {
        "id": generate_block_id(),
        "type": "code",
        "content": {
            "code": code,
            "language": language
        }
    }
    if caption:
        block["content"]["caption"] = caption
    return block


def create_list(items: List[str], ordered: bool = False) -> Dict[str, Any]:
    """Create a list block."""
    return {
        "id": generate_block_id(),
        "type": "list",
        "content": {
            "ordered": ordered,
            "items": items
        }
    }


def create_quote(text: str, author: str = None) -> Dict[str, Any]:
    """Create a quote block."""
    block = {
        "id": generate_block_id(),
        "type": "quote",
        "content": {
            "text": text
        }
    }
    if author:
        block["content"]["author"] = author
    return block


def create_table(headers: List[str], rows: List[List[str]]) -> Dict[str, Any]:
    """Create a table block."""
    return {
        "id": generate_block_id(),
        "type": "table",
        "content": {
            "headers": headers,
            "rows": rows
        }
    }


def create_image(src: str, alt: str, caption: str = None) -> Dict[str, Any]:
    """Create an image block."""
    block = {
        "id": generate_block_id(),
        "type": "image",
        "content": {
            "src": src,
            "alt": alt
        }
    }
    if caption:
        block["content"]["caption"] = caption
    return block


# Content templates for different lesson types
def generate_intro_lesson_content(lesson_num: int) -> List[Dict[str, Any]]:
    """Generate content for introductory lessons."""
    return [
        create_heading(2, f"Welcome to Lesson {lesson_num}"),
        create_text(
            "<p>In this lesson, we'll explore fundamental concepts that form the building blocks "
            "of your learning journey. Understanding these basics is crucial for mastering more "
            "advanced topics later in the course.</p>"
        ),
        create_heading(3, "What You'll Learn"),
        create_list([
            "Core concepts and terminology",
            "Practical applications and real-world examples",
            "Best practices and common pitfalls to avoid",
            "Hands-on exercises to reinforce your understanding"
        ]),
        create_text(
            "<p><strong>Prerequisites:</strong> This lesson assumes you have completed the previous "
            "lessons in this module. If you're new here, we recommend starting from the beginning "
            "of the module for the best learning experience.</p>"
        ),
        create_heading(3, "Key Concepts"),
        create_text(
            "<p>Before we dive deep, let's establish a common understanding of the key terms "
            "we'll be using throughout this lesson. These concepts will serve as reference points "
            "as we explore more complex topics.</p>"
        ),
        create_quote(
            "The only way to learn a new programming language is by writing programs in it.",
            "Dennis Ritchie"
        ),
        create_heading(3, "Getting Started"),
        create_text(
            "<p>Let's begin with a simple example that demonstrates the core concept. "
            "Pay attention to how each component works together to achieve the desired result.</p>"
        ),
    ]


def generate_practical_lesson_content(lesson_num: int) -> List[Dict[str, Any]]:
    """Generate content for practical/coding lessons."""
    return [
        create_heading(2, "Practical Application"),
        create_text(
            "<p>Now that you understand the theory, it's time to put it into practice. "
            "In this lesson, we'll work through real-world examples and build something tangible.</p>"
        ),
        create_heading(3, "Example Implementation"),
        create_text(
            "<p>Let's start with a basic implementation. Follow along and try to understand "
            "each line of code and its purpose.</p>"
        ),
        create_code(
            """// Example: Basic implementation
function exampleFunction(param) {
    // Initialize variables
    let result = null;
    
    // Process the parameter
    if (param && typeof param === 'string') {
        result = param.toUpperCase();
    }
    
    // Return the result
    return result;
}

// Usage
const output = exampleFunction('hello world');
console.log(output); // Outputs: HELLO WORLD""",
            "javascript",
            "Basic function implementation example"
        ),
        create_heading(3, "Breaking It Down"),
        create_list([
            "We define a function that takes a single parameter",
            "We check if the parameter is a valid string",
            "We transform the input using built-in methods",
            "We return the processed result"
        ], ordered=True),
        create_text(
            "<p><strong>Important:</strong> Always validate your inputs before processing them. "
            "This prevents unexpected errors and makes your code more robust.</p>"
        ),
        create_heading(3, "Common Patterns"),
        create_table(
            ["Pattern", "Use Case", "Example"],
            [
                ["Guard Clause", "Early validation", "if (!param) return null;"],
                ["Default Values", "Handle missing data", "param = param || 'default';"],
                ["Type Checking", "Ensure data types", "typeof param === 'string'"]
            ]
        ),
        create_heading(3, "Try It Yourself"),
        create_text(
            "<p>Now it's your turn! Try modifying the code above to add additional functionality. "
            "Can you make it handle numbers as well as strings? What about arrays?</p>"
        ),
    ]


def generate_advanced_lesson_content(lesson_num: int) -> List[Dict[str, Any]]:
    """Generate content for advanced lessons."""
    return [
        create_heading(2, "Advanced Concepts"),
        create_text(
            "<p>Welcome to the advanced section! Here we'll explore sophisticated techniques "
            "and patterns used by experienced developers in production environments.</p>"
        ),
        create_heading(3, "Complex Implementation"),
        create_text(
            "<p>This example demonstrates a more complex use case that combines multiple "
            "concepts we've covered in previous lessons.</p>"
        ),
        create_code(
            """// Advanced pattern: Factory with dependency injection
class ServiceFactory {
    constructor(dependencies) {
        this.dependencies = dependencies;
        this.services = new Map();
    }
    
    register(name, ServiceClass) {
        this.services.set(name, ServiceClass);
    }
    
    create(name, ...args) {
        const ServiceClass = this.services.get(name);
        if (!ServiceClass) {
            throw new Error(`Service ${name} not found`);
        }
        return new ServiceClass(this.dependencies, ...args);
    }
}

// Usage
const factory = new ServiceFactory({ logger: console });
factory.register('api', ApiService);
const apiService = factory.create('api', 'https://api.example.com');""",
            "javascript",
            "Factory pattern with dependency injection"
        ),
        create_heading(3, "Design Considerations"),
        create_text(
            "<p>When implementing advanced patterns, consider the following trade-offs:</p>"
        ),
        create_table(
            ["Approach", "Pros", "Cons"],
            [
                ["Dependency Injection", "Flexible, testable", "More complex setup"],
                ["Singleton Pattern", "Single instance", "Global state issues"],
                ["Factory Pattern", "Centralized creation", "Additional abstraction layer"]
            ]
        ),
        create_quote(
            "Simplicity is prerequisite for reliability.",
            "Edsger W. Dijkstra"
        ),
        create_heading(3, "Performance Optimization"),
        create_list([
            "Use lazy initialization for expensive operations",
            "Implement caching strategies where appropriate",
            "Consider memory management and cleanup",
            "Profile your code to identify bottlenecks"
        ]),
        create_text(
            "<p><strong>Remember:</strong> Premature optimization is the root of all evil. "
            "Focus on writing clear, maintainable code first, then optimize based on measured performance data.</p>"
        ),
    ]


def generate_summary_lesson_content(lesson_num: int) -> List[Dict[str, Any]]:
    """Generate content for summary/review lessons."""
    return [
        create_heading(2, "Module Summary"),
        create_text(
            "<p>Congratulations on reaching the end of this module! Let's review what "
            "we've covered and consolidate your learning.</p>"
        ),
        create_heading(3, "Key Takeaways"),
        create_list([
            "Understanding fundamental concepts and their applications",
            "Practical implementation techniques and best practices",
            "Common patterns and when to use them",
            "Performance considerations and optimization strategies"
        ]),
        create_heading(3, "Concept Map"),
        create_text(
            "<p>Here's how the concepts we've learned relate to each other:</p>"
        ),
        create_image(
            "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800&h=400&fit=crop",
            "Concept relationship diagram",
            "Visual representation of how concepts connect"
        ),
        create_heading(3, "Quick Reference"),
        create_table(
            ["Concept", "Description", "When to Use"],
            [
                ["Basic Pattern", "Simple implementation", "Small projects, learning"],
                ["Intermediate Pattern", "Structured approach", "Medium-sized applications"],
                ["Advanced Pattern", "Complex architecture", "Large-scale systems"]
            ]
        ),
        create_heading(3, "Next Steps"),
        create_text(
            "<p>You're now ready to move forward! In the next module, we'll build upon "
            "these foundations and explore more advanced topics. Make sure you're comfortable "
            "with the material covered here before proceeding.</p>"
        ),
        create_quote(
            "Learning never exhausts the mind.",
            "Leonardo da Vinci"
        ),
        create_heading(3, "Practice Exercises"),
        create_list([
            "Review the code examples from each lesson",
            "Try to implement a small project using what you've learned",
            "Experiment with different approaches and patterns",
            "Share your work with the community for feedback"
        ], ordered=True),
    ]


def get_content_for_lesson(order: int, total_lessons: int) -> List[Dict[str, Any]]:
    """
    Determine appropriate content based on lesson order in module.
    
    Args:
        order: Lesson order (1-based)
        total_lessons: Total number of lessons in the module
    
    Returns:
        List of content blocks
    """
    # First lesson - introduction
    if order == 1:
        return generate_intro_lesson_content(order)
    # Last lesson - summary
    elif order == total_lessons:
        return generate_summary_lesson_content(order)
    # Middle lessons - alternate between practical and advanced
    elif order % 2 == 0:
        return generate_practical_lesson_content(order)
    else:
        return generate_advanced_lesson_content(order)


async def fetch_lessons_by_module(session) -> Dict[str, List[tuple]]:
    """Fetch all lessons grouped by module."""
    stmt = text("""
        SELECT id, title, module_id, "order", content
        FROM lessons
        ORDER BY module_id, "order"
    """)
    result = await session.execute(stmt)
    rows = result.fetchall()
    
    # Group by module_id
    modules = {}
    for row in rows:
        module_id = str(row[2])
        if module_id not in modules:
            modules[module_id] = []
        modules[module_id].append(row)
    
    return modules


async def update_lesson_content(session):
    """Update content for all lessons."""
    
    # Fetch lessons grouped by module
    modules = await fetch_lessons_by_module(session)
    
    if not modules:
        print("No lessons found in the database.")
        return
    
    total_lessons = sum(len(lessons) for lessons in modules.values())
    print(f"Found {total_lessons} lessons across {len(modules)} modules.")
    print("Generating and updating lesson content...\n")
    
    updated_count = 0
    
    for module_id, lessons in modules.items():
        print(f"\n📚 Processing module {module_id} ({len(lessons)} lessons)")
        
        for lesson in lessons:
            lesson_id, title, _, order, current_content = lesson
            
            # Generate content based on lesson order
            content_blocks = get_content_for_lesson(order, len(lessons))
            content_json = json.dumps(content_blocks, indent=2)
            
            print(f"  ✏️  Lesson {order}: {title}")
            print(f"     Generated {len(content_blocks)} content blocks")
            
            # Update the lesson content
            update_stmt = text("""
                UPDATE lessons
                SET content = :content, updated_at = CURRENT_TIMESTAMP
                WHERE id = :lesson_id
            """)
            
            await session.execute(update_stmt, {
                "content": content_json,
                "lesson_id": lesson_id
            })
            
            updated_count += 1
    
    # Commit all changes
    await session.commit()
    
    print(f"\n✅ Successfully updated {updated_count} lessons with rich content.")
    print("All changes have been committed to the database.")


async def main():
    """Main function to run the lesson content seeding."""
    print("🚀 Starting lesson content seeding process...\n")
    
    async with async_session() as session:
        try:
            await update_lesson_content(session)
        except Exception as exc:
            await session.rollback()
            print("❌ Error occurred while updating lesson content. Transaction rolled back.")
            print(f"Error details: {exc}")
            raise
        finally:
            print("\n🏁 Lesson content seeding process completed.")


if __name__ == "__main__":
    asyncio.run(main())