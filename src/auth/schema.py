from datetime import date, datetime
from pydantic import BaseModel,EmailStr
from uuid import UUID
from typing import List,Optional

class UserCreate(BaseModel):
    user_name: str
    user_email: EmailStr
    password: str

class UserResponse(BaseModel):
    user_id: str
    user_name: str
    user_email: EmailStr

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    user_email: EmailStr
    password: str

class CurrentUser(BaseModel):
    user_id: UUID
    user_name: str
    user_email: EmailStr

class UserProfileUpdate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    location: str
    date_of_birth: date

class UserProfileResponse(BaseModel):
    user_id: UUID
    profile_id: UUID
    first_name: str
    last_name: str
    phone: str
    location: str
    date_of_birth: date
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class HealthInfoUpdate(BaseModel):
    height_cm: float
    weight_kg: float
    blood_type: str
    emergency_contact: str
    allergies: List[str]
    current_medications: List[str]

class HealthInfoResponse(BaseModel):
    health_id: UUID
    user_id: UUID
    height_cm: float
    weight_kg: float
    blood_type: str
    emergency_contact: str
    allergies: List[str]
    current_medications: List[str]

    class Config:
        orm_mode = True