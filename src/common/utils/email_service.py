import aiosmtplib
from email.message import EmailMessage
from typing import List, Optional, Any, Dict
import jinja2
import os
from datetime import datetime
from src.common.config import settings

# Configure Jinja2 environment
# src/common/utils/email_service.py -> src/templates/emails
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates", "emails")

template_loader = jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
template_env = jinja2.Environment(loader=template_loader, autoescape=True)

def render_template(template_name: str, context: Dict[str, Any]) -> str:
    try:
        template = template_env.get_template(template_name)
        return template.render(**context)
    except Exception as e:
        print(f"Error rendering template {template_name}: {e}")
        return ""

async def send_email(subject: str, body: str, recipients: List[str], html_body: Optional[str] = None) -> None:
    """
    Sends an email asynchronously using aiosmtplib.
    
    Args:
        subject (str): The subject of the email.
        body (str): The plain text content of the email.
        recipients (List[str]): List of recipient email addresses.
    """
    if not settings.SMTP_HOST:
        print(f"[MOCK EMAIL] To: {recipients}, Subject: {subject}\nBody: {body[:100]}...")
        return

    message = EmailMessage()
    message["From"] = settings.EMAIL_SENDER
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    # If HTML content is provided, add it as an alternative.
    if html_body:
        message.add_alternative(html_body, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_USE_TLS,
        start_tls=not settings.SMTP_USE_TLS,
        timeout=120,
    )

async def send_verification_email(recipient_email: str, first_name:str, verification_code: str) -> None:
    """
    Sends a verification email to the specified recipient.
    
    Args:
        recipient_email (str): The email address of the recipient.
        first_name(str): The first name of the user.
        verification_code(str): The code for the verification.
    """
    verification_link = f"{settings.FRONTEND_URL}/auth/verify?code={verification_code}"
    
    context = {
        "first_name": first_name,
        "verification_link": verification_link,
        "verification_code": verification_code
    }
    
    html_body = render_template("verification.html", context)
    text_body = f"Dear {first_name},\n\nPlease verify your email here: {verification_link}\nOr use code: {verification_code}"
    
    await send_email("Verify Your Email - Retgrow Learn", text_body, [recipient_email], html_body=html_body)

async def send_welcome_email(recipient_email: str, first_name: str) -> None:
    context = {
        "first_name": first_name,
        "dashboard_link": f"{settings.FRONTEND_URL}/dashboard"
    }
    html_body = render_template("welcome.html", context)
    text_body = f"Welcome {first_name}! You can now access your dashboard: {settings.FRONTEND_URL}/dashboard"
    
    await send_email("Welcome to Retgrow Learn!", text_body, [recipient_email], html_body=html_body)

async def send_subscription_email(type: str, user_email: str, user_first_name: str, context_data: Dict[str, Any]) -> None:
    template_map = {
        "success": "subscription_success.html",
        "failed": "subscription_failed.html",
        "renewed": "subscription_renewed.html"
    }
    
    subject_map = {
        "success": "Payment Successful - Retgrow Learn",
        "failed": "Action Required: Payment Failed",
        "renewed": "Subscription Renewed Successfully"
    }
    
    template_file = template_map.get(type)
    subject = subject_map.get(type, "Subscription Notification")
    
    if not template_file:
        print(f"Unknown subscription email type: {type}")
        return
        
    # Add common links to context
    context_data["first_name"] = user_first_name
    context_data["dashboard_link"] = f"{settings.FRONTEND_URL}/dashboard"
    context_data["billing_link"] = f"{settings.FRONTEND_URL}/settings/billing"
    
    html_body = render_template(template_file, context_data)
    text_body = f"Subscription Notification: {type}. Please check your dashboard for details."
    
    await send_email(subject, text_body, [user_email], html_body=html_body)
