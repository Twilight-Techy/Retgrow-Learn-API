
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.database import get_db_session as get_db
from src.auth.dependencies import get_current_user
from src.models.models import User, Certificate
from src.modules.certificates import certificate_service
from src.modules.dashboard.schemas import CertificateBrief

router = APIRouter(prefix="/certificates", tags=["Certificates"])

@router.get("", response_model=List[CertificateBrief])
async def get_my_certificates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all certificates earned by the current user.
    """
    return await certificate_service.get_user_certificates(current_user.id, db)

@router.get("/{certificate_id}", response_model=CertificateBrief)
async def get_certificate(
    certificate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific certificate.
    """
    cert = await certificate_service.get_certificate_by_id(certificate_id, db)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    if cert.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this certificate")
        
    return cert
