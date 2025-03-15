# src/contact/schemas.py

from pydantic import BaseModel, EmailStr

class ContactFormRequest(BaseModel):
    name: str
    email: EmailStr
    message: str

    class Config:
        from_attributes = True

class ContactFormResponse(BaseModel):
    message: str

    class Config:
        from_attributes = True
