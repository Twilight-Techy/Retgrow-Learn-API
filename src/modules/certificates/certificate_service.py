
from datetime import datetime, timezone
import io
import logging
import os
import uuid
import sys
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import UploadFile

from sqlalchemy.orm import selectinload

from src.models.models import Certificate, User, Course, UserRole
from src.modules.subscriptions import access_control_service
import httpx
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Vercel Blob API configuration
VERCEL_BLOB_API_URL = "https://blob.vercel-storage.com"
BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN")

from src.modules.subscriptions import subscription_service
from src.models.models import SubscriptionPlan

logger = logging.getLogger(__name__)

# Path to assets
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
CUSTOM_FONT_DIR = os.path.join(ASSETS_DIR, "fonts")

# Try to find fonts
VENV_LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), "venv", "Lib", "site-packages")
FONT_DIR = os.path.join(VENV_LIB, "reportlab", "fonts")

# Register Vera Fonts (Sans-Serif)
try:
    if os.path.exists(os.path.join(FONT_DIR, "Vera.ttf")):
        pdfmetrics.registerFont(TTFont('Vera', os.path.join(FONT_DIR, "Vera.ttf")))
        pdfmetrics.registerFont(TTFont('VeraBd', os.path.join(FONT_DIR, "VeraBd.ttf")))
except Exception as e:
    logger.warning("Error registering Vera font: %s", e)

# Register GreatVibes (Script font for "Certificate of Completion")
GREAT_VIBES_PATH = os.path.join(CUSTOM_FONT_DIR, "GreatVibes-Regular.ttf")
HAS_GREAT_VIBES = False
try:
    if os.path.exists(GREAT_VIBES_PATH):
        pdfmetrics.registerFont(TTFont('GreatVibes', GREAT_VIBES_PATH))
        HAS_GREAT_VIBES = True
except Exception as e:
    logger.warning("Error registering GreatVibes font: %s", e)

# Font Constants
BRAND_FONT = "VeraBd" if "VeraBd" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
TITLE_FONT = "GreatVibes" if HAS_GREAT_VIBES else "Times-BoldItalic"
SUBTITLE_FONT = "Vera" if "Vera" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
NAME_FONT = "Times-BoldItalic"
BODY_FONT = "Vera" if "Vera" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
COURSE_FONT = "Times-Bold"
DATE_FONT = "Vera" if "Vera" in pdfmetrics.getRegisteredFontNames() else "Helvetica"


async def generate_certificate(user: User, course: Course, db: AsyncSession) -> Optional[Certificate]:
    """
    Generates a PDF certificate for the user and course, uploads it to Vercel Blob,
    and stores the record in the database.
    """
    subscription = await subscription_service.get_active_subscription(user.id, db)
    if not subscription or subscription.plan not in [SubscriptionPlan.FOCUSED, SubscriptionPlan.PRO]:
        return None

    stmt = select(Certificate).where(
        Certificate.user_id == user.id,
        Certificate.course_id == course.id
    )
    result = await db.execute(stmt)
    existing_cert = result.scalars().first()
    if existing_cert:
        return existing_cert

    pdf_buffer = await _create_certificate_pdf(user, course)
    
    filename = f"certificates/{user.id}_{course.id}.pdf"
    blob_url = await _upload_to_blob(pdf_buffer, filename)
    
    if not blob_url:
        raise Exception("Failed to upload certificate to storage.")

    logger.debug("Generating certificate for User %s, Course %s", user.id, course.id)
    new_cert = Certificate(
        user_id=user.id,
        course_id=course.id,
        certificate_url=blob_url,
        issued_at=datetime.now(timezone.utc)
    )
    db.add(new_cert)
    try:
        await db.commit()
        await db.refresh(new_cert)
        logger.debug("Certificate saved to DB: %s", new_cert.id)
    except IntegrityError:
        # If unique constraint violated (race condition), return the existing one
        await db.rollback()
        logger.debug("IntegrityError - certificate likely exists. Fetching existing.")
        
        stmt = select(Certificate).where(
            Certificate.user_id == user.id,
            Certificate.course_id == course.id
        )
        result = await db.execute(stmt)
        existing_cert = result.scalars().first()
        if existing_cert:
            return existing_cert
        else:
            # Should not happen if IntegrityError was due to duplicate
            logger.warning("IntegrityError caught but no existing certificate found")
            return None
            
    except Exception as e:
        logger.error("Failed to save certificate to DB: %s", e)
        await db.rollback()
        raise e
    
    return new_cert

async def get_user_certificates(user_id: uuid.UUID, db: AsyncSession) -> List[Certificate]:
    stmt = (
        select(Certificate)
        .options(selectinload(Certificate.course))
        .where(Certificate.user_id == user_id)
        .order_by(Certificate.issued_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_certificate_by_user_and_course(user_id: uuid.UUID, course_id: uuid.UUID, db: AsyncSession) -> Optional[Certificate]:
    """Get a specific certificate for a user and course combination."""
    stmt = (
        select(Certificate)
        .where(Certificate.user_id == user_id, Certificate.course_id == course_id)
    )
    result = await db.execute(stmt)
    return result.scalars().first()

async def get_certificate_by_id(cert_id: uuid.UUID, db: AsyncSession) -> Optional[Certificate]:
    stmt = (
        select(Certificate)
        .options(selectinload(Certificate.course))
        .where(Certificate.id == cert_id)
    )
    result = await db.execute(stmt)
    return result.scalars().first()

# --- Helper Functions ---

def _find_asset(filenames: List[str]) -> Optional[str]:
    """Helper to find an asset file with case-insensitive matching."""
    if not os.path.exists(ASSETS_DIR):
        return None
    available_files = os.listdir(ASSETS_DIR)
    for target in filenames:
        if target in available_files:
            return os.path.join(ASSETS_DIR, target)
        for f in available_files:
            if f.lower() == target.lower():
                return os.path.join(ASSETS_DIR, f)
    return None

def _draw_background_pattern(c, width, height):
    """Draws a fallback vector background with purple waves and gold accents."""
    c.saveState()
    c.setStrokeColorRGB(0.85, 0.65, 0.13)
    c.setLineWidth(4)
    c.rect(20, 20, width-40, height-40)
    c.setLineWidth(1)
    c.rect(25, 25, width-50, height-50)

    path = c.beginPath()
    path.moveTo(20, height-20)
    path.lineTo(20, height-150)
    path.curveTo(100, height-150, 300, height-50, width/2, height-20)
    path.lineTo(20, height-20)
    c.setFillColorRGB(0.29, 0.0, 0.51)
    c.setStrokeColor(colors.transparent)
    c.drawPath(path, fill=1, stroke=0)

    path = c.beginPath()
    path.moveTo(width-20, 150)
    path.curveTo(width-100, 150, width-300, 50, width/2, 20)
    path.lineTo(width/2 + 20, 20)
    path.curveTo(width-280, 60, width-90, 160, width-20, 160)
    path.close()
    c.setFillColorRGB(0.85, 0.65, 0.13)
    c.drawPath(path, fill=1, stroke=0)
    c.restoreState()

def _draw_text_centered(c, text, font, size, x, y, color, char_space=0):
    """Helper to draw centered text with optional character spacing."""
    c.setFont(font, size)
    c.setFillColor(color)
    if char_space == 0:
        c.drawCentredString(x, y, text)
    else:
        text_obj = c.beginText()
        text_obj.setFont(font, size)
        text_obj.setFillColor(color)
        text_obj.setCharSpace(char_space)
        width = c.stringWidth(text, font, size) + (len(text) - 1) * char_space
        text_obj.setTextOrigin(x - width / 2, y)
        text_obj.textOut(text)
        c.drawText(text_obj)

def _draw_seal(c, x, y, size):
    """Draws a fallback gold seal."""
    c.saveState()
    center_x, center_y = x + size/2, y + size/2
    c.setFillColorRGB(0.85, 0.65, 0.13)
    c.circle(center_x, center_y, size/2, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont(BRAND_FONT, 8)
    c.drawCentredString(center_x, center_y - 3, "RETGROW")
    c.setFont(BODY_FONT, 6)
    c.drawCentredString(center_x, center_y - 10, "CERTIFIED")
    c.restoreState()

async def _create_certificate_pdf(user: User, course: Course) -> bytes:
    """
    Creates a professional PDF certificate matching the provided sample design.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter) 
    # width ~792, height ~612
    
    # 1. Background
    bg_path = _find_asset(["background.png", "background.jpg", "background.jpeg"])
    if bg_path:
        try:
            c.drawImage(bg_path, 0, 0, width=width, height=height, preserveAspectRatio=False, mask='auto')
        except Exception as e:
            logger.error("Error loading background image: %s", e)
            _draw_background_pattern(c, width, height)
    else:
        _draw_background_pattern(c, width, height)

    # 2. Content Layout
    mid_x = width / 2
    
    # Colors
    RETGROW_PURPLE = colors.Color(0.29, 0.0, 0.51)
    RETGROW_GOLD = colors.Color(0.83, 0.69, 0.22)
    DARK_GRAY = colors.Color(0.2, 0.2, 0.2)
    MEDIUM_GRAY = colors.Color(0.4, 0.4, 0.4)

    # -----------------------------------------------------------
    # "RETGROW" - Top branding, purple, spaced
    # -----------------------------------------------------------
    current_y = height - 140
    _draw_text_centered(c, "RETGROW", BRAND_FONT, 18, mid_x, current_y, RETGROW_PURPLE, char_space=4)
    
    # -----------------------------------------------------------
    # "Certificate of Completion" - Script font, gold, compact
    # GreatVibes is a proper script font now
    # Reduced from 54 -> 48 for more compact feel
    # -----------------------------------------------------------
    current_y -= 65
    c.setFont(TITLE_FONT, 52)
    c.setFillColor(RETGROW_GOLD)
    # Offset left to compensate for GreatVibes glyph metrics
    c.drawCentredString(mid_x - 55, current_y, "Certificate of Completion")

    # -----------------------------------------------------------
    # "THIS CERTIFICATE IS PROUDLY PRESENTED TO" 
    # Increased from 10 -> 13 (user: "supporting text should be bigger")
    # -----------------------------------------------------------
    current_y -= 45
    _draw_text_centered(c, "THIS CERTIFICATE IS PROUDLY PRESENTED TO", SUBTITLE_FONT, 13, mid_x, current_y, MEDIUM_GRAY, char_space=1)

    # -----------------------------------------------------------
    # User Name - Italic serif, slightly smaller (60 -> 44)
    # Changed to Times-Italic per user feedback
    # -----------------------------------------------------------
    current_y -= 55
    c.setFont(NAME_FONT, 44)
    c.setFillColor(DARK_GRAY)
    user_name = f"{user.first_name} {user.last_name}"
    c.drawCentredString(mid_x, current_y, user_name)

    # Thin line under name
    current_y -= 12
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.5)
    c.line(mid_x - 180, current_y, mid_x + 180, current_y)

    # -----------------------------------------------------------
    # "For successfully completing the course"
    # Increased from 12 -> 14 (user: "supporting text should be bigger")
    # -----------------------------------------------------------
    current_y -= 30
    c.setFont(BODY_FONT, 14)
    c.setFillColor(MEDIUM_GRAY)
    c.drawCentredString(mid_x, current_y, "For successfully completing the course")

    # -----------------------------------------------------------
    # Course Title - Less bold (Times-Bold -> Times-Roman), slightly smaller (32 -> 26)
    # -----------------------------------------------------------
    current_y -= 40
    c.setFont(COURSE_FONT, 26)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(mid_x, current_y, course.title)

    # -----------------------------------------------------------
    # Date - Increased from 12 -> 14
    # -----------------------------------------------------------
    current_y -= 40
    c.setFont(DATE_FONT, 14)
    c.setFillColor(MEDIUM_GRAY)
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    c.drawCentredString(mid_x, current_y, f"on {date_str}.")

    # -----------------------------------------------------------
    # Footer: Signature (Left) and Seal (Right)
    # -----------------------------------------------------------
    
    sign_x = 85
    sign_img_bottom = 60   # bottom of image (moved up)
    sign_img_height = 75
    sign_line_y = 95       # moved up from 85
    
    sign_path = _find_asset(["signature.png", "signature.jpg", "signature.PNG"])
    
    # Draw line first (behind signature)
    c.setStrokeColor(DARK_GRAY)
    c.setLineWidth(1)
    c.line(sign_x, sign_line_y, sign_x + 220, sign_line_y)
    
    if sign_path:
        # Signature overlays the line
        c.drawImage(sign_path, sign_x + 10, sign_img_bottom, width=200, height=sign_img_height, mask='auto', preserveAspectRatio=True)
    
    # "Director of Programs" centered under the line
    c.setFont(BODY_FONT, 15)
    c.setFillColor(MEDIUM_GRAY)
    c.drawCentredString(sign_x + 100, sign_line_y - 20, "Director of Programs")

    # Seal - BIGGER (110 -> 150)
    seal_path = _find_asset(["seal.png", "seal.jpg"])
    seal_size = 150
    seal_x = width - 200
    seal_y = 30
    
    if seal_path:
        c.drawImage(seal_path, seal_x, seal_y, width=seal_size, height=seal_size, mask='auto', preserveAspectRatio=True)
    else:
        _draw_seal(c, seal_x, seal_y, seal_size)
        
    c.save()
    
    buffer.seek(0)
    return buffer.getvalue()

async def _upload_to_blob(file_data: bytes, filename: str) -> Optional[str]:
    """
    Uploads the file data to Vercel Blob using the HTTP API.
    """
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        logger.error("BLOB_READ_WRITE_TOKEN not set")
        return None

    url = f"{VERCEL_BLOB_API_URL}/{filename}"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-version": "1",
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.put(url, content=file_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("url")
            else:
                logger.error("Blob upload failed: %s %s", response.status_code, response.text)
                raise Exception(f"Blob upload failed: {response.text}")
        except Exception as e:
            logger.exception("Blob upload error")
            raise e
