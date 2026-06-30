"""Auth request/response schemas."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, model_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime
    google_connected: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    @model_validator(mode="before")
    def compute_google_connected(cls, value: any) -> any:
        if hasattr(value, "google_id") and not isinstance(value, dict):
            return {
                "id": value.id,
                "email": value.email,
                "name": value.name,
                "created_at": value.created_at,
                "google_connected": value.google_id is not None
            }
        return value


