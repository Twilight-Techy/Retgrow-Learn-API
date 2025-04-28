from uuid import UUID
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from src.models.models import Course, Module

async def create_module(course_id: UUID, data: dict, db: AsyncSession) -> Module:
    # 1) Verify course exists
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalars().first()
    if not course:
        raise ValueError("Course not found")

    # 2) Create module
    new_module = Module(course_id=course_id, title=data["title"], order=data["order"])
    db.add(new_module)
    try:
        await db.commit()
        await db.refresh(new_module)
    except IntegrityError:
        await db.rollback()
        raise ValueError("Failed to create module (possible duplicate order)")
    return new_module

async def update_module(course_id: UUID, module_id: UUID, data: dict, db: AsyncSession) -> Module:
    # 1) Load module and ensure it belongs to the course
    result = await db.execute(
        select(Module).where(Module.id == module_id, Module.course_id == course_id)
    )
    module = result.scalars().first()
    if not module:
        raise ValueError("Module not found for this course")

    # 2) Apply updates
    if data.get("title") is not None:
        module.title = data["title"]
    if data.get("order") is not None:
        module.order = data["order"]

    db.add(module)
    try:
        await db.commit()
        await db.refresh(module)
    except IntegrityError:
        await db.rollback()
        raise ValueError("Failed to update module (possible order conflict)")
    return module

async def delete_module(course_id: UUID, module_id: UUID, db: AsyncSession) -> None:
    # 1) Load module
    result = await db.execute(
        select(Module).where(Module.id == module_id, Module.course_id == course_id)
    )
    module = result.scalars().first()
    if not module:
        raise ValueError("Module not found for this course")

    # 2) Delete
    await db.delete(module)
    await db.commit()
