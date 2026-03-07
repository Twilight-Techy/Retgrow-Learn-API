# src/contact/schemas.py

from pydantic import ConfigDict, BaseModel, EmailStr

class ContactFormRequest(BaseModel):
    name: str
    email: EmailStr
    message: str
    model_config = ConfigDict(from_attributes=True)

class ContactFormResponse(BaseModel):
    message: str
    model_config = ConfigDict(from_attributes=True)
