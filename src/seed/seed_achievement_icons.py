# scripts/seed_achievement_icons.py
"""
Seed script to update achievements' icon_url fields with https://fav.farm/ prefix.

Usage:
    python scripts/seed_achievement_icons.py

Notes:
- This script expects an AsyncSession factory named `async_session` to be importable.
  Adjust the import path below if your DB module lives elsewhere.
- Updates all achievements where icon_url is not null and doesn't already have the fav.farm prefix.
"""

import asyncio
from sqlalchemy import text
from typing import List, Tuple

# Adjust this import if your DB file/module path differs.
try:
    from src.common.database.database import async_session
except Exception as e:
    raise ImportError(
        "Couldn't import async_session from src.common.db. "
        "Adjust the import path to point to your DB module.\n"
        f"Original error: {e}"
    )


FAV_FARM_PREFIX = "https://fav.farm/"


async def fetch_achievements_to_update(session) -> List[Tuple[str, str, str]]:
    """Return a list of (id, title, current_icon_url) for achievements that need updating."""
    stmt = text(
        "SELECT id, title, icon_url FROM achievements "
        "WHERE icon_url IS NOT NULL "
        "AND icon_url NOT LIKE :prefix"
    )
    result = await session.execute(stmt, {"prefix": f"{FAV_FARM_PREFIX}%"})
    return [(row.id, row.title, row.icon_url) for row in result.fetchall()]


async def update_achievement_icons(session):
    """Update icon_url for all achievements that need the fav.farm prefix."""
    
    # Fetch achievements that need updating
    achievements = await fetch_achievements_to_update(session)
    
    if not achievements:
        print("No achievements found that need icon URL updates.")
        return
    
    print(f"Found {len(achievements)} achievements to update:")
    
    # Update each achievement
    for achievement_id, title, current_icon_url in achievements:
        new_icon_url = f"{FAV_FARM_PREFIX}{current_icon_url}"
        
        print(f" - {title} (id={achievement_id})")
        print(f"   {current_icon_url} -> {new_icon_url}")
        
        # Update statement
        update_stmt = text(
            "UPDATE achievements "
            "SET icon_url = :new_icon_url, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = :achievement_id"
        )
        await session.execute(update_stmt, {
            "new_icon_url": new_icon_url,
            "achievement_id": achievement_id
        })
    
    # Commit all changes
    await session.commit()
    print(f"\nSuccessfully updated {len(achievements)} achievement icon URLs and committed transaction.")


async def main():
    """Main function to run the seed script."""
    async with async_session() as session:
        try:
            await update_achievement_icons(session)
        except Exception as exc:
            # Rollback and re-raise so the error is visible
            await session.rollback()
            print("Error while running seed script. Rolled back transaction.")
            raise


if __name__ == "__main__":
    asyncio.run(main())