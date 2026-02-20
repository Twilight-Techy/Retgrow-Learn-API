import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.utils.email_service import send_verification_email, send_welcome_email, send_subscription_email
from src.common.config import settings

async def test_emails():
    print("Testing Email Service...")
    recipient = "mzone7325@gmail.com"
    first_name = "Mzone"
    
    print(f"\n1. Sending Verification Email to {recipient}...")
    await send_verification_email(recipient, first_name, "123456")
    
    print(f"\n2. Sending Welcome Email to {recipient}...")
    await send_welcome_email(recipient, first_name)
    
    print(f"\n3. Sending Subscription Success Email...")
    context = {
        "plan_name": "Pro Plan",
        "billing_cycle": "Monthly",
        "amount": "NGN 5,000.00",
        "date": "February 20, 2026",
        "next_renewal_date": "March 20, 2026"
    }
    await send_subscription_email("success", recipient, first_name, context)

    print("\nDone!")

if __name__ == "__main__":
    # Use real settings from .env
    asyncio.run(test_emails())
