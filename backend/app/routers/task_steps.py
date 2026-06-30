"""Task steps router — create, list, and update steps within a task.

Step 3 enhancement: PATCH /steps/{id} now triggers re-planning on status
changes and returns updated scheduled dates for all sibling steps.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.task_step import TaskStep, StepStatus
from app.schemas.task_step import StepCreate, StepUpdate, StepResponse, StepUpdateResponse
from app.services.task_service import (
    get_task,
    list_steps,
    get_step,
    create_step,
)
from app.services.scheduler import distribute_steps_across_days
from app.services.prioritizer import get_remaining_hours, compute_days_until_due, is_task_at_risk
from app.services.calendar_sync import update_calendar_events_on_replan

router = APIRouter(tags=["steps"])


@router.get("/tasks/{task_id}/steps", response_model=list[StepResponse])
def get_task_steps(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all steps for a task (must belong to authenticated user)."""
    task = get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return list_steps(db, task_id)


@router.post(
    "/tasks/{task_id}/steps",
    response_model=StepResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task_step(
    task_id: int,
    data: StepCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a step to a task."""
    task = get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return create_step(db, task_id, data)


@router.patch("/steps/{step_id}", response_model=StepUpdateResponse)
def update_task_step(
    step_id: int,
    data: StepUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a step (e.g. mark as done). Triggers re-planning if status changes.

    Returns the updated step, all re-planned sibling steps, and an at_risk flag.
    """
    step = get_step(db, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found",
        )
    # Verify ownership through the parent task
    task = get_task(db, step.task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found",
        )

    # Track whether status is changing
    old_status = step.status
    update_data = data.model_dump(exclude_unset=True)

    # Apply all field updates
    for field, value in update_data.items():
        setattr(step, field, value)

    new_status = step.status

    # Auto-set completed_at when status transitions to done
    if new_status == StepStatus.done and old_status != StepStatus.done:
        step.completed_at = datetime.now(timezone.utc)
    # Clear completed_at if status moves away from done (undo)
    elif new_status != StepStatus.done and old_status == StepStatus.done:
        step.completed_at = None

    # Determine if re-planning is needed
    status_changed = (
        "status" in update_data
        and old_status != new_status
        and new_status in (StepStatus.done, StepStatus.skipped, StepStatus.in_progress)
    )

    # Load all sibling steps for re-planning and response
    all_steps = list_steps(db, task.id)

    if status_changed:
        # Re-plan: redistribute only the remaining (non-done, non-skipped) steps
        remaining_steps = [
            s for s in all_steps
            if s.status not in (StepStatus.done, StepStatus.skipped)
        ]
        # Apply new scheduled dates — done/skipped steps keep their historical dates
        distribute_steps_across_days(remaining_steps, task.due_date)
        db.commit()
        # Update calendar events if synced
        update_calendar_events_on_replan(current_user, task, all_steps, db)
    else:
        db.commit()

    # Refresh all steps to get updated values
    for s in all_steps:
        db.refresh(s)
    db.refresh(step)

    # Compute at_risk
    remaining_hours = get_remaining_hours(all_steps)
    days = compute_days_until_due(task.due_date)
    at_risk = is_task_at_risk(remaining_hours, days)

    return StepUpdateResponse(
        step=StepResponse.model_validate(step),
        all_steps=[StepResponse.model_validate(s) for s in sorted(all_steps, key=lambda s: s.order_index)],
        task_at_risk=at_risk,
    )
