# src/search/search_controller.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.search import search_service, schemas
from src.common.database.database import get_db_session

router = APIRouter(prefix="/search", tags=["search"])

@router.get("", response_model=schemas.SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Global search endpoint.
    
    Performs a case-insensitive search for courses, tracks, and resources where the title
    or description contains the provided query.
    """
    results = await search_service.search(q, db)
    # If no results are found, you may choose to return an empty result set.
    return results
