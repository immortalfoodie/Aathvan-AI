"""Priority router — cross-task urgency ranking and overview endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task, AIPlanStatus
from app.models.task_step import TaskStep
from app.schemas.priority import PriorityItemResponse, OverviewItemResponse
from app.schemas.task_step import StepResponse
from app.services.prioritizer import build_today_priorities, build_overview

router = APIRouter(prefix="/priority", tags=["priority"])


def _load_user_tasks_with_steps(db: Session, user_id: int):
    """Load all approved tasks and their steps for a user."""
    tasks = (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.ai_plan_status == AIPlanStatus.approved)
        .all()
    )
    result = []
    for task in tasks:
        steps = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task.id)
            .order_by(TaskStep.order_index)
            .all()
        )
        result.append((task, steps))
    return result


@router.get("/today", response_model=list[PriorityItemResponse])
def get_today_priorities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return ranked list of 'what to work on next' across all approved tasks.

    Each item represents the single next actionable step from a task,
    sorted by urgency_score descending (most urgent first).
    """
    tasks_with_steps = _load_user_tasks_with_steps(db, current_user.id)
    items = build_today_priorities(tasks_with_steps)

    # Convert dataclass items to Pydantic response models
    response = []
    for item in items:
        next_step_data = None
        if item.next_step:
            next_step_data = StepResponse.model_validate(item.next_step)

        response.append(PriorityItemResponse(
            task_id=item.task_id,
            task_title=item.task_title,
            urgency_score=item.urgency_score,
            at_risk=item.at_risk,
            reason=item.reason,
            remaining_hours=item.remaining_hours,
            days_until_due=item.days_until_due,
            next_step=next_step_data,
        ))
    return response


@router.get("/overview", response_model=list[OverviewItemResponse])
def get_priority_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return urgency and progress overview for every active approved task.

    Used by the dashboard summary widget to show the user's overall load.
    """
    tasks_with_steps = _load_user_tasks_with_steps(db, current_user.id)
    items = build_overview(tasks_with_steps)

    return [
        OverviewItemResponse(
            task_id=item.task_id,
            task_title=item.task_title,
            urgency_score=item.urgency_score,
            remaining_hours=item.remaining_hours,
            days_until_due=item.days_until_due,
            at_risk=item.at_risk,
            total_steps=item.total_steps,
            completed_steps=item.completed_steps,
        )
        for item in items
    ]
