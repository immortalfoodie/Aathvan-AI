"""TaskStep request/response schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.models.task_step import StepStatus


class StepCreate(BaseModel):
    title: str
    description: Optional[str] = None
    estimated_hours: Optional[float] = None
    order_index: int = 0
    scheduled_date: Optional[datetime] = None


class StepUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    estimated_hours: Optional[float] = None
    order_index: Optional[int] = None
    scheduled_date: Optional[datetime] = None
    status: Optional[StepStatus] = None
    actual_hours_spent: Optional[float] = None


class StepResponse(BaseModel):
    id: int
    task_id: int
    title: str
    description: Optional[str] = None
    estimated_hours: Optional[float] = None
    order_index: int
    scheduled_date: Optional[datetime] = None
    status: StepStatus
    completed_at: Optional[datetime] = None
    actual_hours_spent: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StepUpdateResponse(BaseModel):
    """Enhanced response from PATCH /steps/{id} — includes re-planned sibling steps."""
    step: StepResponse
    all_steps: List[StepResponse]
    task_at_risk: bool
