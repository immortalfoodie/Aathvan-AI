"""Task and TaskStep CRUD service layer.

Business logic lives here — routers stay thin.
AI-powered task decomposition will be added to this module in Step 2.
"""

from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.task_step import TaskStep
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.task_step import StepCreate, StepUpdate


# ── Task CRUD ──────────────────────────────────────────────────────────

def list_tasks(db: Session, user_id: int) -> list[Task]:
    """Return all tasks belonging to a user, ordered by creation date."""
    return (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .order_by(Task.created_at.desc())
        .all()
    )


def get_task(db: Session, task_id: int, user_id: int) -> Task | None:
    """Get a single task, scoped to the owning user."""
    return (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id)
        .first()
    )


def create_task(db: Session, user_id: int, data: TaskCreate) -> Task:
    """Create a new task for the given user."""
    task = Task(
        user_id=user_id,
        title=data.title,
        raw_description=data.raw_description,
        task_type=data.task_type,
        due_date=data.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task: Task, data: TaskUpdate) -> Task:
    """Apply partial updates to an existing task."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    """Delete a task (steps cascade-delete automatically)."""
    db.delete(task)
    db.commit()


# ── TaskStep CRUD ──────────────────────────────────────────────────────

def list_steps(db: Session, task_id: int) -> list[TaskStep]:
    """Return all steps for a task, ordered by order_index."""
    return (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id)
        .order_by(TaskStep.order_index)
        .all()
    )


def get_step(db: Session, step_id: int) -> TaskStep | None:
    """Get a single step by ID."""
    return db.query(TaskStep).filter(TaskStep.id == step_id).first()


def create_step(db: Session, task_id: int, data: StepCreate) -> TaskStep:
    """Create a new step for the given task."""
    step = TaskStep(
        task_id=task_id,
        title=data.title,
        description=data.description,
        estimated_hours=data.estimated_hours,
        order_index=data.order_index,
        scheduled_date=data.scheduled_date,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def update_step(db: Session, step: TaskStep, data: StepUpdate) -> TaskStep:
    """Apply partial updates to a step (e.g. status change)."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(step, field, value)
    db.commit()
    db.refresh(step)
    return step
