import asyncio
import random
from sqlalchemy.future import select

from src.common.database.database import async_session, engine
from src.models.models import Resource

UNSPLASH_TECH_IMAGES = [
    "https://images.unsplash.com/photo-1498050108023-c5249f4df085", 
    "https://images.unsplash.com/photo-1555066931-4365d14bab8c", 
    "https://images.unsplash.com/photo-1517694712202-14dd9538aa97", 
    "https://images.unsplash.com/photo-1522071820081-009f0129c71c", 
    "https://images.unsplash.com/photo-1461749280684-dccba630e2f6", 
    "https://images.unsplash.com/photo-1542831371-32f555c86880", 
    "https://images.unsplash.com/photo-1504639725590-34d0984388bd", 
    "https://images.unsplash.com/photo-1555099962-4199c345e5dd", 
    "https://images.unsplash.com/photo-1534972195531-d756b9bfa9f2", 
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5"  
]

async def seed_images():
    async with engine.begin() as conn:
        print("Starting resource image seed...")
        
    async with async_session() as db:
        result = await db.execute(select(Resource).where(Resource.image_url == None))
        resources_without_images = result.scalars().all()
        
        if not resources_without_images:
            print("No resources found missing an image_url. Exiting.")
            return

        print(f"Found {len(resources_without_images)} resources without an image.")

        for resource in resources_without_images:
            random_image = random.choice(UNSPLASH_TECH_IMAGES)
            resource.image_url = random_image
            print(f"Assigned image to resource ID: {resource.id}")

        await db.commit()
        print("Database commit successful. Images seeded.")

if __name__ == '__main__':
    asyncio.run(seed_images())
