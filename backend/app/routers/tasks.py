"""Tasks router — CRUD for user tasks."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.task import AIPlanStatus, TaskStatus
from app.models.task_step import TaskStep, StepStatus
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    GeneratePlanResponse,
    ApprovePlanRequest,
    ApprovePlanResponse,
)
from app.services.task_service import (
    list_tasks,
    get_task,
    create_task,
    update_task,
    delete_task,
)
from app.services.ai_service import generate_task_plan, AIServiceException
from app.services.scheduler import distribute_steps_across_days
from app.services.calendar_sync import sync_task_to_calendar
from app.services.estimation_learner import get_adjustment_factor, update_estimation_profile, get_task_autopsy, AutopsyResult

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
def get_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all tasks for the authenticated user."""
    return list_tasks(db, current_user.id)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_new_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new task."""
    return create_task(db, current_user.id, data)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task_by_id(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific task by ID (must belong to the authenticated user)."""
    task = get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task_by_id(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a task's fields."""
    task = get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    old_status = task.status
    updated_task = update_task(db, task, data)
    
    if data.status and old_status != TaskStatus.completed and updated_task.status == TaskStatus.completed:
        update_estimation_profile(db, updated_task)
        
    return updated_task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_by_id(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a task and its steps."""
    task = get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    delete_task(db, task)


@router.post("/{task_id}/generate-plan", response_model=GeneratePlanResponse)
async def generate_plan(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Call the AI service to decompose the task and store proposed steps."""
    task = get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Clean out any existing steps (if regenerating or already generated)
    db.query(TaskStep).filter(TaskStep.task_id == task_id).delete()

    try:
        # Fetch the user's adjustment factor for this task type
        adjustment_factor = get_adjustment_factor(db, current_user.id, task.task_type)

        # Call AI service (async)
        ai_result = await generate_task_plan(
            title=task.title,
            raw_description=task.raw_description,
            task_type=task.task_type.value,
            due_date=task.due_date,
            adjustment_factor=adjustment_factor,
        )
    except AIServiceException as e:
        # Return 502 Bad Gateway with details for the frontend
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )

    # Create the proposed steps in the database
    new_steps = []
    for step_data in ai_result.steps:
        step = TaskStep(
            task_id=task_id,
            title=step_data.title,
            description=step_data.description,
            estimated_hours=step_data.estimated_hours,
            order_index=step_data.suggested_order,
            status=StepStatus.pending,
        )
        db.add(step)
        new_steps.append(step)

    # Update Task state to pending_approval
    task.ai_plan_status = AIPlanStatus.pending_approval
    task.task_summary = ai_result.task_summary
    task.ai_confidence_note = ai_result.confidence_note

    db.commit()

    # Sort new_steps to match Response expectation
    new_steps.sort(key=lambda s: s.order_index)

    return GeneratePlanResponse(task=task, steps=new_steps)


@router.post("/{task_id}/approve-plan", response_model=ApprovePlanResponse)
def approve_plan(
    task_id: int,
    data: ApprovePlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve the proposed task plan (accepting edits) and assign scheduled dates."""
    task = get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if task.ai_plan_status != AIPlanStatus.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task plan has not been generated or is already approved.",
        )

    # Clear previous proposed steps
    db.query(TaskStep).filter(TaskStep.task_id == task_id).delete()

    # Create steps from the approved payload
    approved_steps = []
    for i, step_data in enumerate(data.steps):
        step = TaskStep(
            task_id=task_id,
            title=step_data.title,
            description=step_data.description,
            estimated_hours=step_data.estimated_hours,
            order_index=step_data.order_index,
            status=StepStatus.pending,
        )
        db.add(step)
        approved_steps.append(step)

    # Apply naive scheduling distribution
    distribute_steps_across_days(approved_steps, task.due_date)

    # Update Task state to approved
    task.ai_plan_status = AIPlanStatus.approved

    db.commit()

    # Refresh steps to load automatic fields like IDs
    for s in approved_steps:
        db.refresh(s)

    approved_steps.sort(key=lambda s: s.order_index)

    return ApprovePlanResponse(task=task, steps=approved_steps)


@router.post("/{task_id}/sync-calendar", response_model=ApprovePlanResponse)
def sync_calendar(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync an approved task plan to the user's Google Calendar."""
    if not current_user.google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected. Please link Google first.",
        )

    task = get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if task.ai_plan_status != AIPlanStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task plan must be approved before calendar sync.",
        )

    # Sync steps to calendar
    synced_steps = sync_task_to_calendar(current_user, task, task.steps, db)
    synced_steps.sort(key=lambda s: s.order_index)

    return ApprovePlanResponse(task=task, steps=synced_steps)


@router.get("/{task_id}/autopsy", response_model=AutopsyResult)
def get_autopsy_for_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the deadline autopsy details for a completed task."""
    result = get_task_autopsy(db, task_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Autopsy not available. Task may not exist, may not be completed, or lacked hours data.",
        )
    return result


