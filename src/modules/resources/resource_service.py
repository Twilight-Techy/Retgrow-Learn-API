# src/resources/resource_service.py

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import or_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload

from src.models.models import Resource, Track, UserResource

async def get_resources(
    db: AsyncSession,
    q: Optional[str] = None,
    track_slug: Optional[str] = None,
    rtype: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
) -> list:
    """
    Return resources filtered by q (title/description), track_slug and type.
    Returns ORM objects — Pydantic's model_validator handles track_title/track_slug extraction.
    """
    # Use joinedload to eagerly load the track relationship
    stmt = select(Resource).outerjoin(
        Track, Resource.track_id == Track.id
    ).options(joinedload(Resource.track))

    # filters
    conditions = []

    if q:
        q_like = f"%{q}%"
        conditions.append(or_(Resource.title.ilike(q_like), Resource.description.ilike(q_like)))

    if rtype:
        # convert string to enum safely — raises ValueError if invalid
        try:
            from src.models.models import ResourceType as RT  # adjust import path
            rtype_enum = RT(rtype)  # RT("article") -> ResourceType.ARTICLE
            conditions.append(Resource.type == rtype_enum)
        except Exception:
            # invalid rtype — ignore the filter
            pass

    if track_slug:
        conditions.append(Track.slug == track_slug)

    if conditions:
        stmt = stmt.where(*conditions)

    # apply pagination (offset & limit)
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().unique().all()

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