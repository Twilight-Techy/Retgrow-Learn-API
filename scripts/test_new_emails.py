import asyncio
import sys
import os
from datetime import datetime

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.common.utils.email_service import (
    send_verification_email,
    send_welcome_email,
    send_subscription_email
)

# Mocks
class MockUser:
    def __init__(self, email, first_name):
        self.email = email
        self.first_name = first_name
        self.last_name = "User"

async def main():
    recipient = "mzone7325@gmail.com"
    user = MockUser(recipient, "Michael")
    plan_name = "Pro Plan"
    amount = "NGN 5,000"
    billing_cycle = "monthly"
    next_renewal = "Dec 31, 2026"

    # 1. Verification
    print("Sending Verification...")
    await send_verification_email(recipient, "123456", "123456")
    
    # 2. Welcome
    print("Sending Welcome...")
    await send_welcome_email(user.email, user.first_name)
    
    # Common Context
    sub_context = {
        "plan_name": plan_name,
        "billing_cycle": billing_cycle,
        "amount": amount,
        "date": datetime.now().strftime("%B %d, %Y"),
        "next_renewal_date": next_renewal,
        "failure_reason": "Card Expired"
    }

    # 3. Success
    print("Sending Sub Success...")
    # Check signature: async def send_subscription_email(type: str, user_email: str, user_first_name: str, context_data: Dict[str, Any])
    await send_subscription_email("success", user.email, user.first_name, sub_context)
    
    # 4. Failed
    print("Sending Sub Failed...")
    await send_subscription_email("failed", user.email, user.first_name, sub_context)

    # 5. Renewed
    print("Sending Sub Renewed...")
    await send_subscription_email("renewed", user.email, user.first_name, sub_context)

    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
