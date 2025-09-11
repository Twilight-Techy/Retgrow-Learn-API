# scripts/seed_resource_images.py
"""
Seed script to update resources' image_url fields with Unsplash images.

Usage:
    python scripts/seed_resource_images.py

Notes:
- This script expects an AsyncSession factory named `async_session` to be importable.
  Adjust the import path below if your DB module lives elsewhere.
- It uses Unsplash Source API (query style) so images are topical. You can replace
  the URLs with specific Unsplash photo URLs if you prefer fixed images.
"""

import asyncio
from sqlalchemy import text
from typing import Dict, List

# Adjust this import if your DB file/module path differs.
# The DB file you shared earlier exposes `async_session` (a sessionmaker).
try:
    from src.common.database.database import async_session
except Exception as e:
    raise ImportError(
        "Couldn't import async_session from src.common.db. "
        "Adjust the import path to point to your DB module.\n"
        f"Original error: {e}"
    )


# Map the exact resource titles to Unsplash "source" URLs (topic-based).
# These use the Unsplash Source API which returns a suitable image for the query.
IMAGE_MAP: Dict[str, str] = {
    "MDN Web Docs": "https://images.unsplash.com/photo-1627398242454-45a1465c2479?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "JavaScript Tutorial": "https://images.unsplash.com/photo-1579468118864-1b9ea3c0db4a?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Python Data Science Handbook": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Machine Learning Course": "https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "React Native Docs": "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "AWS Training": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Docker Getting Started": "https://images.unsplash.com/photo-1518432031352-d6fc5c10da5a?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
    "Clean Code": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=800&h=600&fit=crop&crop=entropy&cs=tinysrgb",
}


async def fetch_existing_titles(session) -> List[str]:
    """Return a list of resource titles currently in the DB (for the ones we care about)."""
    titles = list(IMAGE_MAP.keys())
    placeholders = ", ".join([f":t{i}" for i in range(len(titles))])
    params = {f"t{i}": titles[i] for i in range(len(titles))}
    stmt = text(f"SELECT title FROM resources WHERE title IN ({placeholders})")
    result = await session.execute(stmt, params)
    return [row[0] for row in result.fetchall()]


async def update_images(session):
    """Update image_url for matching resources."""
    titles = list(IMAGE_MAP.keys())

    placeholders = ", ".join([f":t{i}" for i in range(len(titles))])
    params = {f"t{i}": titles[i] for i in range(len(titles))}

    # Fetch matching rows so we can see what's present
    select_stmt = text(f"SELECT id, title, image_url FROM resources WHERE title IN ({placeholders})")
    result = await session.execute(select_stmt, params)
    rows = result.fetchall()

    found_titles = {r.title for r in rows}

    print(f"Found {len(rows)} matching resources in DB.")
    for r in rows:
        new_url = IMAGE_MAP.get(r.title)
        print(f" - {r.title} (id={r.id}) -> setting image_url to: {new_url}")

        # Update statement (set updated_at to current timestamp too)
        upd = text(
            "UPDATE resources "
            "SET image_url = :image_url, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = :id"
        )
        await session.execute(upd, {"image_url": new_url, "id": r.id})

    # Report missing titles
    missing = [t for t in titles if t not in found_titles]
    if missing:
        print("\nThese titles were not found in the `resources` table (no updates performed for them):")
        for m in missing:
            print(" -", m)

    # Commit
    await session.commit()
    print("\nImage URLs updated and transaction committed.")


async def main():
    # Create a session and run the update
    async with async_session() as session:
        try:
            await update_images(session)
        except Exception as exc:
            # rollback and re-raise so the error is visible
            await session.rollback()
            print("Error while running seed script. Rolled back transaction.")
            raise


if __name__ == "__main__":
    asyncio.run(main())
