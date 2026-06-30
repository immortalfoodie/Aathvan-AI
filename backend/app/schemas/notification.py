"""Notification request/response schemas."""

from datetime import datetime
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    message: str
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
