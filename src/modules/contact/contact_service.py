from src.common.config import settings
from src.common.utils.email_service import send_email  # Reuse the existing email utility

async def process_contact_form(form_data: dict) -> bool:
    """
    Compose and send an email based on the contact form data.
    
    Args:
        form_data (dict): Contains 'name', 'email', and 'message'.
        
    Returns:
        bool: True if the email was sent successfully.
    """
    subject = "New Contact Form Submission"
    body = (
        f"Name: {form_data['name']}\n"
        f"Email: {form_data['email']}\n\n"
        f"Message:\n{form_data['message']}"
    )
    # Use the contact recipient from settings or another dynamic source.
    recipients = [settings.CONTACT_RECIPIENT]
    await send_email(subject, body, recipients)
    return True
