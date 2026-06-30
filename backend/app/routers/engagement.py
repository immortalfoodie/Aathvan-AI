"""Engagement router for Voice Check-ins, Simulations, and Streaks."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List
from datetime import date, datetime

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task, TaskStatus
from app.models.task_step import TaskStep, StepStatus
from app.services.voice_service import process_voice_checkin, VoiceCheckinResult
from app.services.simulation_service import simulate_inaction

router = APIRouter(prefix="/engagement", tags=["engagement"])

class VoiceTranscript(BaseModel):
    transcript: str

@router.post("/checkin/voice", response_model=VoiceCheckinResult)
async def voice_checkin(
    data: VoiceTranscript,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Process a voice check-in transcript and return proposed status updates."""
    # Fetch all active steps for this user
    active_tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.status.in_([TaskStatus.not_started, TaskStatus.in_progress])
    ).all()
    
    task_ids = [t.id for t in active_tasks]
    
    active_steps = db.query(TaskStep).filter(
        TaskStep.task_id.in_(task_ids),
        TaskStep.status.in_([StepStatus.pending, StepStatus.in_progress])
    ).all()
    
    # Needs tasks joined or eagerly loaded for the context, we will attach it manually
    for step in active_steps:
        step.task = next((t for t in active_tasks if t.id == step.task_id), None)
        
    result = await process_voice_checkin(data.transcript, active_steps)
    return result

@router.post("/momentum/streak")
def update_streak(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the user's check-in streak quietly."""
    today = date.today()
    
    if current_user.last_active_date == today:
        # Already checked in today
        return {"streak": current_user.current_streak_days}
        
    if current_user.last_active_date:
        delta = (today - current_user.last_active_date).days
        if delta == 1:
            current_user.current_streak_days += 1
        else:
            # Streak broken
            current_user.current_streak_days = 1
    else:
        current_user.current_streak_days = 1
        
    current_user.last_active_date = today
    db.commit()
    
    return {"streak": current_user.current_streak_days}

@router.get("/momentum/today")
def get_momentum_today(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the percentage of users who have made progress today."""
    today = date.today()
    total_users = db.query(User).count()
    
    if total_users < 3:
        # Graceful fallback for small demo environments
        return {
            "has_data": False,
            "message": "Start building your momentum today!",
            "percentage": 0
        }
        
    # Count users who have last_active_date == today
    active_users = db.query(User).filter(User.last_active_date == today).count()
    
    percentage = int((active_users / total_users) * 100) if total_users > 0 else 0
    
    return {
        "has_data": True,
        "message": f"{percentage}% of students have already checked in today.",
        "percentage": percentage
    }

@router.get("/simulate/inaction")
def get_inaction_simulation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the 'What if I do nothing' simulation."""
    return simulate_inaction(db, current_user.id)
