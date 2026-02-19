from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.database.database import get_db_session as get_db
from src.modules.subscriptions import recurring_service
from src.common.config import settings
from typing import Optional, Dict, Any

router = APIRouter(prefix="/cron", tags=["Cron Jobs"])

@router.post("/renew-subscriptions")
async def renew_subscriptions(
    x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Trigger recurring subscription renewal.
    Protected by X-Cron-Secret header.
    """
    if x_cron_secret != settings.CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid cron secret")
    
    # Process synchronously to ensure DB session is valid
    result = await recurring_service.process_due_subscriptions(db)
    return result
