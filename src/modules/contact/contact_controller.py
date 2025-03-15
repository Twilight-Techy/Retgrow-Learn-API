# src/contact/contact_controller.py

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.contact import contact_service, schemas
from src.common.database.database import get_db_session

router = APIRouter(prefix="/contact", tags=["contact"])

@router.post("", response_model=schemas.ContactFormResponse)
async def submit_contact_form(
    form: schemas.ContactFormRequest,
    background_tasks: BackgroundTasks
    # db: AsyncSession = Depends(get_db_session)
):
    """
    Process a contact form submission by sending an email.
    The email is sent asynchronously in a background task.
    """
    # contact = await contact_service.submit_contact_form(form.model_dump(), db)
    # if not contact:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Failed to submit contact form."
    #     )
    # return schemas.ContactFormResponse(message="Contact form submitted successfully.")
    try:
        # Schedule the email sending as a background task.
        background_tasks.add_task(contact_service.process_contact_form, form.model_dump())
        return schemas.ContactFormResponse(message="Contact form submitted successfully.")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to submit contact form."
        )