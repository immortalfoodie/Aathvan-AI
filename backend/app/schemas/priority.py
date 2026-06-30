"""Priority response schemas for the prioritization API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.schemas.task_step import StepResponse


class PriorityItemResponse(BaseModel):
    """A single ranked priority item — one per active task."""
    task_id: int
    task_title: str
    urgency_score: float
    at_risk: bool
    reason: str
    remaining_hours: float
    days_until_due: float
    next_step: Optional[StepResponse] = None


class OverviewItemResponse(BaseModel):
    """Summary view of a single task's urgency and progress."""
    task_id: int
    task_title: str
    urgency_score: float
    remaining_hours: float
    days_until_due: float
    at_risk: bool
    total_steps: int
    completed_steps: int
