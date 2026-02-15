
from datetime import datetime
import io
import os
import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import UploadFile

from src.models.models import Certificate, User, Course, UserRole
from src.modules.subscriptions import access_control_service
import httpx
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Vercel Blob API configuration
VERCEL_BLOB_API_URL = "https://blob.vercel-storage.com"
BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN")

from src.modules.subscriptions import subscription_service
from src.models.models import SubscriptionPlan

async def generate_certificate(user: User, course: Course, db: AsyncSession) -> Optional[Certificate]:
    """
    Generates a PDF certificate for the user and course, uploads it to Vercel Blob,
    and stores the record in the database.
    """
    # 1. Check eligibility
    # Only FOCUSED and PRO users can get certificates.
    # Check active subscription
    subscription = await subscription_service.get_active_subscription(user.id, db)
    if not subscription or subscription.plan not in [SubscriptionPlan.FOCUSED, SubscriptionPlan.PRO]:
        # User is not eligible for a certificate
        return None

    # Check if certificate already exists
    stmt = select(Certificate).where(
        Certificate.user_id == user.id,
        Certificate.course_id == course.id
    )
    result = await db.execute(stmt)
    existing_cert = result.scalars().first()
    if existing_cert:
        return existing_cert

    # 2. Generate PDF
    pdf_buffer = await _create_certificate_pdf(user, course)
    
    # 3. Upload to Vercel Blob
    filename = f"certificates/{user.id}_{course.id}.pdf"
    blob_url = await _upload_to_blob(pdf_buffer, filename)
    
    if not blob_url:
        # Fallback or error handling? For now, raise.
        raise Exception("Failed to upload certificate to storage.")

    # 4. Save to DB
    new_cert = Certificate(
        user_id=user.id,
        course_id=course.id,
        certificate_url=blob_url,
        issued_at=datetime.utcnow()
    )
    db.add(new_cert)
    await db.commit()
    await db.refresh(new_cert)
    
    return new_cert

async def get_user_certificates(user_id: uuid.UUID, db: AsyncSession) -> List[Certificate]:
    stmt = select(Certificate).where(Certificate.user_id == user_id).order_by(Certificate.issued_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_certificate_by_id(cert_id: uuid.UUID, db: AsyncSession) -> Optional[Certificate]:
    stmt = select(Certificate).where(Certificate.id == cert_id)
    result = await db.execute(stmt)
    return result.scalars().first()

# --- Helper Functions ---

async def _create_certificate_pdf(user: User, course: Course) -> bytes:
    """
    Creates a simple PDF certificate using ReportLab.
    Returns the bytes of the PDF.
    """
    buffer = io.BytesIO()
    
    # Landscape letter size
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)
    
    # distinct background color or border
    c.setStrokeColor(colors.purple)
    c.setLineWidth(5)
    c.rect(30, 30, width-60, height-60)
    
    # Title
    c.setFont("Helvetica-Bold", 40)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, height - 150, "Certificate of Completion")
    
    # Subtitle
    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 200, "This is to certify that")
    
    # Name
    c.setFont("Helvetica-Bold", 30)
    c.setFillColor(colors.purple)
    user_name = f"{user.first_name} {user.last_name}"
    c.drawCentredString(width / 2, height - 250, user_name)
    
    # Course
    c.setFont("Helvetica", 16)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, height - 300, "has successfully completed the course")
    
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 350, course.title)
    
    # Date
    c.setFont("Helvetica", 14)
    date_str = datetime.utcnow().strftime("%B %d, %Y")
    c.drawCentredString(width / 2, height - 420, f"Issued on {date_str}")
    
    # Footer / Retgrow Branding
    c.setFont("Helvetica-Oblique", 12)
    c.setFillColor(colors.gray)
    c.drawCentredString(width / 2, 60, "Retgrow Learning Platform")
    
    c.save()
    
    buffer.seek(0)
    return buffer.getvalue()

async def _upload_to_blob(file_data: bytes, filename: str) -> Optional[str]:
    """
    Uploads the file data to Vercel Blob using the HTTP API.
    """
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        print("BLOB_READ_WRITE_TOKEN not set")
        return None

    # Vercel Blob HTTP API (Reverse engineered from SDK/Docs)
    # Endpoint: PUT https://blob.vercel-storage.com/{pathname}
    # Headers: 
    #   Authorization: Bearer <token>
    #   x-api-version: 1
    
    url = f"{VERCEL_BLOB_API_URL}/{filename}"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-version": "1",
        # "x-add-random-suffix": "false", # We want deterministic or clean names if possible
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, content=file_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # Response format: { "url": "...", "pathname": "...", "contentType": "...", ... }
                return data.get("url")
            else:
                print(f"Blob upload failed: {response.status_code} {response.text}")
                # For debugging, check if we need to handle 409 or others
                raise Exception(f"Blob upload failed: {response.text}")
        except Exception as e:
            print(f"Blob upload error: {e}")
            raise e

