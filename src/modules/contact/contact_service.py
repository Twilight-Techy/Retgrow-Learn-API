# src/contact/contact_service.py

# from sqlalchemy.ext.asyncio import AsyncSession
# from src.models.models import ContactForm
from typing import List
import aiosmtplib
from email.message import EmailMessage
from src.common.config import settings  # Assumes settings contains email configuration

# async def submit_contact_form(form_data: dict, db: AsyncSession) -> ContactForm:
#     """
#     Save the contact form submission to the database.
#     """
#     new_contact = ContactForm(
#         name=form_data["name"],
#         email=form_data["email"],
#         message=form_data["message"]
#     )
#     db.add(new_contact)
#     await db.commit()
#     await db.refresh(new_contact)
#     return new_contact

async def send_email(subject: str, body: str, recipients: List[str]):
    message = EmailMessage()
    message["From"] = settings.EMAIL_SENDER
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)
    
    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True
    )

async def process_contact_form(form_data: dict) -> bool:
    """
    Compose and send an email based on the contact form data.
    """
    subject = "New Contact Form Submission"
    body = (
        f"Name: {form_data['name']}\n"
        f"Email: {form_data['email']}\n\n"
        f"Message:\n{form_data['message']}"
    )
    # The recipient can be a support email address defined in your settings.
    recipients = [settings.CONTACT_RECIPIENT]
    await send_email(subject, body, recipients)
    return True
