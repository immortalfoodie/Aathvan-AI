"""Estimation Learner service for 'Deadline Autopsy'."""

from sqlalchemy.orm import Session
from app.models.task import Task, TaskStatus
from app.models.task_step import TaskStep, StepStatus
from app.models.estimation_profile import UserEstimationProfile
from pydantic import BaseModel
from typing import List, Optional

class StepAutopsy(BaseModel):
    title: str
    estimated_hours: float
    actual_hours: float
    difference: float

class AutopsyResult(BaseModel):
    task_id: int
    task_title: str
    total_estimated: float
    total_actual: float
    adjustment_factor_before: float
    adjustment_factor_after: float
    steps: List[StepAutopsy]
    takeaway: str

def get_adjustment_factor(db: Session, user_id: int, task_type) -> float:
    profile = db.query(UserEstimationProfile).filter(
        UserEstimationProfile.user_id == user_id,
        UserEstimationProfile.task_type == task_type
    ).first()
    if profile and profile.sample_count >= 3:
        return profile.adjustment_factor
    return 1.0

def update_estimation_profile(db: Session, task: Task) -> Optional[AutopsyResult]:
    """Calculate ratio of actual to estimated hours for completed steps, update profile."""
    # Find all steps for this task that have both estimated and actual hours
    steps = db.query(TaskStep).filter(
        TaskStep.task_id == task.id,
        TaskStep.status == StepStatus.done,
        TaskStep.estimated_hours.isnot(None),
        TaskStep.actual_hours_spent.isnot(None)
    ).all()

    if not steps:
        return None

    total_est = 0.0
    total_act = 0.0
    step_autopsies = []

    for step in steps:
        if step.estimated_hours > 0:
            total_est += step.estimated_hours
            total_act += step.actual_hours_spent
            step_autopsies.append(StepAutopsy(
                title=step.title,
                estimated_hours=step.estimated_hours,
                actual_hours=step.actual_hours_spent,
                difference=step.actual_hours_spent - step.estimated_hours
            ))

    if total_est == 0:
        return None

    # This task's ratio
    task_ratio = total_act / total_est

    # Update or create profile
    profile = db.query(UserEstimationProfile).filter(
        UserEstimationProfile.user_id == task.user_id,
        UserEstimationProfile.task_type == task.task_type
    ).first()

    factor_before = profile.adjustment_factor if profile else 1.0

    if not profile:
        profile = UserEstimationProfile(
            user_id=task.user_id,
            task_type=task.task_type,
            adjustment_factor=task_ratio,
            sample_count=1
        )
        db.add(profile)
    else:
        # Simple weighted running average
        new_factor = ((profile.adjustment_factor * profile.sample_count) + task_ratio) / (profile.sample_count + 1)
        profile.adjustment_factor = new_factor
        profile.sample_count += 1
    
    db.commit()

    factor_after = profile.adjustment_factor

    # Generate a simple takeaway
    percent = abs((factor_after - 1.0) * 100)
    if factor_after > 1.05:
        takeaway = f"{task.task_type.value.capitalize()}-type steps take about {percent:.0f}% longer than initially estimated — future plans will account for this."
    elif factor_after < 0.95:
        takeaway = f"{task.task_type.value.capitalize()}-type steps take about {percent:.0f}% less time than initially estimated — future plans will account for this."
    else:
        takeaway = f"Your estimates for {task.task_type.value} tasks are highly accurate! Keeping adjustments steady."

    return AutopsyResult(
        task_id=task.id,
        task_title=task.title,
        total_estimated=total_est,
        total_actual=total_act,
        adjustment_factor_before=factor_before,
        adjustment_factor_after=factor_after,
        steps=step_autopsies,
        takeaway=takeaway
    )

def get_task_autopsy(db: Session, task_id: int, user_id: int) -> Optional[AutopsyResult]:
    """Retrieves an autopsy report for an already completed task by re-calculating (or just returning the current state)."""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
    if not task or task.status != TaskStatus.completed:
        return None
    # We can just re-run the calculation without modifying the profile if it's already done.
    # To be safe, we just calculate the summary on the fly.
    
    steps = db.query(TaskStep).filter(
        TaskStep.task_id == task.id,
        TaskStep.status == StepStatus.done,
        TaskStep.estimated_hours.isnot(None),
        TaskStep.actual_hours_spent.isnot(None)
    ).all()

    if not steps:
        return None

    total_est = sum(s.estimated_hours for s in steps)
    total_act = sum(s.actual_hours_spent for s in steps)
    
    profile = db.query(UserEstimationProfile).filter(
        UserEstimationProfile.user_id == task.user_id,
        UserEstimationProfile.task_type == task.task_type
    ).first()

    factor = profile.adjustment_factor if profile else 1.0
    
    step_autopsies = [
        StepAutopsy(
            title=step.title,
            estimated_hours=step.estimated_hours,
            actual_hours=step.actual_hours_spent,
            difference=step.actual_hours_spent - step.estimated_hours
        ) for step in steps if step.estimated_hours > 0
    ]
    
    if total_est > 0:
        task_ratio = total_act / total_est
        percent = abs((factor - 1.0) * 100)
        if factor > 1.05:
            takeaway = f"{task.task_type.value.capitalize()}-heavy steps took about {percent:.0f}% longer than estimated — future plans will account for this."
        elif factor < 0.95:
            takeaway = f"{task.task_type.value.capitalize()}-heavy steps took about {percent:.0f}% less time than estimated — future plans will account for this."
        else:
            takeaway = "Your estimates were highly accurate! Keeping adjustments steady."
    else:
        takeaway = "Not enough data to calculate an adjustment."

    return AutopsyResult(
        task_id=task.id,
        task_title=task.title,
        total_estimated=total_est,
        total_actual=total_act,
        adjustment_factor_before=1.0, # Approximate for stateless getter
        adjustment_factor_after=factor,
        steps=step_autopsies,
        takeaway=takeaway
    )
