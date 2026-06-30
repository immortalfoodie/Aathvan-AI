"""Task request/response schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.models.task import TaskType, TaskStatus, AIPlanStatus
from app.schemas.task_step import StepResponse


class TaskCreate(BaseModel):
    title: str
    raw_description: Optional[str] = None
    task_type: TaskType = TaskType.other
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    raw_description: Optional[str] = None
    task_type: Optional[TaskType] = None
    due_date: Optional[datetime] = None
    status: Optional[TaskStatus] = None
    ai_plan_status: Optional[AIPlanStatus] = None
    task_summary: Optional[str] = None
    ai_confidence_note: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    raw_description: Optional[str] = None
    task_type: TaskType
    due_date: Optional[datetime] = None
    status: TaskStatus
    ai_plan_status: AIPlanStatus
    task_summary: Optional[str] = None
    ai_confidence_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GeneratePlanResponse(BaseModel):
    task: TaskResponse
    steps: List[StepResponse]


class ApprovePlanStep(BaseModel):
    title: str
    description: Optional[str] = None
    estimated_hours: Optional[float] = None
    order_index: int


class ApprovePlanRequest(BaseModel):
    steps: List[ApprovePlanStep]


class ApprovePlanResponse(BaseModel):
    task: TaskResponse
    steps: List[StepResponse]

