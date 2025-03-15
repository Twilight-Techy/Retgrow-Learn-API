# src/resources/resource_service.py

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.models import Resource, UserResource

async def get_all_resources(db: AsyncSession) -> List[Resource]:
    """
    Retrieve all resources from the database.
    """
    result = await db.execute(select(Resource))
    resources = result.scalars().all()
    return resources

async def get_resource_by_id(resource_id: str, db: AsyncSession) -> Optional[Resource]:
    """
    Retrieve a single resource by its ID.
    """
    result = await db.execute(select(Resource).where(Resource.id == resource_id))
    resource = result.scalars().first()
    return resource

async def record_resource_view(user_id: str, resource_id: str, db: AsyncSession) -> bool:
    """
    Records a resource view for a user.
    - If the user has already viewed the resource, update the last_accessed timestamp.
    - If not, and the user already has 5 records, delete the oldest one and insert the new record.
    """
    # Check if the user already has a record for this resource.
    result = await db.execute(
        select(UserResource).where(
            UserResource.user_id == user_id,
            UserResource.resource_id == resource_id
        )
    )
    existing_record = result.scalars().first()

    if existing_record:
        # Update the last_accessed timestamp.
        existing_record.last_accessed = datetime.now(timezone.utc)
        db.add(existing_record)
        await db.commit()
        return True
    else:
        # Retrieve all recent resource view records for the user, ordered by last_accessed ascending (oldest first).
        result = await db.execute(
            select(UserResource)
            .where(UserResource.user_id == user_id)
            .order_by(UserResource.last_accessed.asc())
        )
        records = result.scalars().all()
        if len(records) >= 5:
            # Delete the oldest record.
            oldest_record = records[0]
            await db.delete(oldest_record)
            await db.commit()
        # Create a new record.
        new_record = UserResource(user_id=user_id, resource_id=resource_id)
        db.add(new_record)
        await db.commit()
        return True

async def create_resource(resource_data: dict, db: AsyncSession) -> Resource:
    new_resource = Resource(
        id=uuid.uuid4(),  # Omit if your model auto-generates the ID
        title=resource_data["title"],
        description=resource_data.get("description"),
        type=resource_data["type"],
        url=resource_data["url"],
        track_id=resource_data.get("track_id")
    )
    db.add(new_resource)
    await db.commit()
    await db.refresh(new_resource)
    return new_resource

async def update_resource(resource_id: str, resource_data: dict, db: AsyncSession) -> Optional[Resource]:
    result = await db.execute(select(Resource).where(Resource.id == resource_id))
    resource = result.scalars().first()
    if not resource:
        return None
    for key, value in resource_data.items():
        if value is not None:
            setattr(resource, key, value)
    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return resource

async def delete_resource(resource_id: str, db: AsyncSession) -> bool:
    result = await db.execute(select(Resource).where(Resource.id == resource_id))
    resource = result.scalars().first()
    if not resource:
        return False
    await db.delete(resource)
    await db.commit()
    return True