"""Simulation service for the 'What If I Do Nothing' feature."""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from app.models.task import Task, TaskStatus
from app.models.task_step import TaskStep, StepStatus

def simulate_inaction(db: Session, user_id: int) -> Dict[str, Any]:
    """Projects active tasks forward assuming 0 progress today."""
    
    # 1. Fetch active tasks
    active_tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.status.in_([TaskStatus.not_started, TaskStatus.in_progress])
    ).all()
    
    task_ids = [t.id for t in active_tasks]
    
    # 2. Fetch active steps
    active_steps = db.query(TaskStep).filter(
        TaskStep.task_id.in_(task_ids),
        TaskStep.status.in_([StepStatus.pending, StepStatus.in_progress])
    ).all()
    
    now = datetime.now(timezone.utc)
    
    # 3. Current Plan Projection
    # How much time is needed today, tomorrow, etc. based on currently scheduled_dates
    current_plan = {}
    total_remaining_hours = 0
    
    for step in active_steps:
        total_remaining_hours += step.estimated_hours or 0.0
        if step.scheduled_date:
            date_str = step.scheduled_date.strftime("%Y-%m-%d")
            current_plan[date_str] = current_plan.get(date_str, 0) + (step.estimated_hours or 0.0)

    # 4. Inaction Simulation Projection
    # If we do nothing today, what happens?
    # We shift everything scheduled for today (or past due) to tomorrow.
    inaction_plan = {}
    missed_deadlines = []
    
    today_str = now.strftime("%Y-%m-%d")
    tomorrow = now + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    
    for step in active_steps:
        date_str = step.scheduled_date.strftime("%Y-%m-%d") if step.scheduled_date else tomorrow_str
        
        # Inaction logic: anything scheduled for today or earlier gets pushed to tomorrow
        if date_str <= today_str:
            simulated_date_str = tomorrow_str
        else:
            simulated_date_str = date_str
            
        inaction_plan[simulated_date_str] = inaction_plan.get(simulated_date_str, 0) + (step.estimated_hours or 0.0)
        
        # Check if shifting this step causes it to pass the task's due date
        task = next((t for t in active_tasks if t.id == step.task_id), None)
        if task and task.due_date:
            # If the simulated date is AFTER the due date
            task_due_str = task.due_date.strftime("%Y-%m-%d")
            if simulated_date_str > task_due_str:
                if task.id not in [m['task_id'] for m in missed_deadlines]:
                    missed_deadlines.append({
                        "task_id": task.id,
                        "task_title": task.title,
                        "due_date": task_due_str,
                        "missed_by_days": (datetime.strptime(simulated_date_str, "%Y-%m-%d") - datetime.strptime(task_due_str, "%Y-%m-%d")).days
                    })
                    
    # Format the timeline arrays for the frontend
    # Sort dates and fill gaps up to 7 days
    dates_to_show = []
    for i in range(7):
        d = now + timedelta(days=i)
        dates_to_show.append(d.strftime("%Y-%m-%d"))
        
    current_timeline = [{"date": d, "hours": current_plan.get(d, 0)} for d in dates_to_show]
    inaction_timeline = [{"date": d, "hours": inaction_plan.get(d, 0)} for d in dates_to_show]
    
    # Calculate collisions (days where required hours > 6)
    collisions = sum(1 for v in inaction_plan.values() if v > 6.0)
    current_collisions = sum(1 for v in current_plan.values() if v > 6.0)
    
    return {
        "active_tasks_count": len(active_tasks),
        "total_remaining_hours": total_remaining_hours,
        "missed_deadlines": missed_deadlines,
        "collisions_if_inaction": collisions,
        "collisions_in_current_plan": current_collisions,
        "current_timeline": current_timeline,
        "inaction_timeline": inaction_timeline
    }
