
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.database import get_db_session as get_db
from src.auth.dependencies import get_current_user
from src.models.models import User, Certificate
from src.modules.certificates import certificate_service

router = APIRouter(prefix="/certificates", tags=["Certificates"])

@router.get("", response_model=List[dict])
async def get_my_certificates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all certificates earned by the current user.
    """
    certs = await certificate_service.get_user_certificates(current_user.id, db)
    # Return simple dict or define a schema. Using dict for speed now.
    return [
        {
            "id": str(c.id),
            "course_id": str(c.course_id),
            "course_title": c.course.title if c.course else "Unknown Course",
            "certificate_url": c.certificate_url,
            "issued_at": c.issued_at
        }
        for c in certs
    ]

@router.get("/{certificate_id}")
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
        
    return {
        "id": str(cert.id),
        "course_id": str(cert.course_id),
        "course_title": cert.course.title if cert.course else "Unknown Course",
        "certificate_url": cert.certificate_url,
        "issued_at": cert.issued_at
    }
