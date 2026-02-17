
import asyncio
import os
import sys
from datetime import datetime

# Add the project root to the python path
sys.path.append(os.getcwd())

# Mock the database models to avoid importing SQLAlchemy if possible, 
# but the service imports them. 
# We'll rely on the venv being used correctly.

from src.models.models import User, Course
from src.modules.certificates.certificate_service import _create_certificate_pdf

async def main():
    # Mock user and course
    user = User(first_name="Test", last_name="User", id="123")
    course = Course(title="Advanced Python Programming", id="456")

    print("Generating certificate...")
    try:
        pdf_bytes = await _create_certificate_pdf(user, course)
        
        output_path = "test_certificate_current.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        
        print(f"Certificate generated at {output_path}")
    except Exception as e:
        print(f"Error generating certificate: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
