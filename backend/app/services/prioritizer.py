"""Cross-task prioritization engine — deterministic, explainable urgency scoring.

This module is NOT an LLM call. It uses a simple, transparent formula so that
users and evaluators can understand and trust why something is ranked first.

Urgency formula:
    urgency_score = remaining_estimated_hours / max(days_until_due, 0.5)

Higher score = more urgent (more work crammed into less time).
Overdue tasks get maximum urgency (days_until_due clamped to 0.5).
"""

from datetime import datetime, timezone
from typing import List, Optional
from dataclasses import dataclass

from app.models.task import Task, AIPlanStatus
from app.models.task_step import TaskStep, StepStatus

# Realistic daily work capacity for a student — used for at_risk detection.
# This is a named constant so it can easily be extracted to user settings later.
DEFAULT_DAILY_CAPACITY_HOURS = 4.0


@dataclass
class PriorityItem:
    """A single ranked "what to work on next" item."""
    task_id: int
    task_title: str
    urgency_score: float
    at_risk: bool
    reason: str
    remaining_hours: float
    days_until_due: float
    next_step: Optional[TaskStep]


@dataclass
class OverviewItem:
    """Summary view of a single task's urgency and progress."""
    task_id: int
    task_title: str
    urgency_score: float
    remaining_hours: float
    days_until_due: float
    at_risk: bool
    total_steps: int
    completed_steps: int


def get_remaining_hours(steps: List[TaskStep]) -> float:
    """Sum estimated_hours for all non-done, non-skipped steps."""
    return sum(
        (s.estimated_hours or 0.0)
        for s in steps
        if s.status not in (StepStatus.done, StepStatus.skipped)
    )


def get_next_actionable_step(steps: List[TaskStep]) -> Optional[TaskStep]:
    """Return the first step by order_index that is pending or in_progress."""
    actionable = [
        s for s in steps
        if s.status in (StepStatus.pending, StepStatus.in_progress)
    ]
    if not actionable:
        return None
    actionable.sort(key=lambda s: s.order_index)
    return actionable[0]


def compute_days_until_due(due_date: Optional[datetime], now: Optional[datetime] = None) -> float:
    """Calculate days until due date. Returns float; negative means overdue."""
    if not due_date:
        # No due date = low urgency — treat as far away
        return 365.0

    if now is None:
        now = datetime.now(timezone.utc)

    # Normalize timezone awareness
    if due_date.tzinfo is None:
        now = now.replace(tzinfo=None)

    delta = due_date - now
    return delta.total_seconds() / 86400.0  # fractional days


def compute_urgency_score(remaining_hours: float, days_until_due: float) -> float:
    """Compute urgency score: higher = more urgent.

    Formula: remaining_hours / max(days_until_due, 0.5)

    - Overdue tasks (days <= 0): denominator clamped to 0.5 → maximum urgency
    - Zero remaining hours: score = 0.0 (task is effectively done)
    """
    if remaining_hours <= 0:
        return 0.0
    return remaining_hours / max(days_until_due, 0.5)


def is_task_at_risk(
    remaining_hours: float,
    days_until_due: float,
    daily_capacity: float = DEFAULT_DAILY_CAPACITY_HOURS,
) -> bool:
    """True when the remaining work can't comfortably fit in the remaining days.

    at_risk = remaining_hours / max(days_until_due, 0.5) > daily_capacity
    """
    if remaining_hours <= 0:
        return False
    return (remaining_hours / max(days_until_due, 0.5)) > daily_capacity


def generate_reason(
    remaining_hours: float,
    days_until_due: float,
    at_risk: bool,
) -> str:
    """Generate a plain-language reason string explaining the urgency ranking.

    Template-based (deterministic), not LLM-generated.
    """
    hours_str = f"{remaining_hours:.1f}h"

    if days_until_due <= 0:
        return f"Overdue! {hours_str} of work still remaining"

    days_int = int(round(days_until_due))
    day_word = "day" if days_int == 1 else "days"

    if at_risk:
        return f"Due in {days_int} {day_word} with {hours_str} of work left — needs more time per day than planned"

    if days_until_due <= 2:
        return f"Due in {days_int} {day_word} with {hours_str} of work left — highest urgency right now"

    if days_until_due <= 5:
        return f"Due in {days_int} {day_word} with {hours_str} of work left — keep momentum"

    return f"Due in {days_int} {day_word} with {hours_str} left — on track"


def build_today_priorities(
    tasks_with_steps: List[tuple],
    now: Optional[datetime] = None,
) -> List[PriorityItem]:
    """Build ranked list of "what to work on next" across all approved tasks.

    Args:
        tasks_with_steps: List of (Task, List[TaskStep]) tuples
        now: Override for current time (useful for testing)

    Returns:
        List of PriorityItem sorted descending by urgency_score
    """
    if now is None:
        now = datetime.now(timezone.utc)

    items = []
    for task, steps in tasks_with_steps:
        # Only consider tasks with approved AI plans
        if task.ai_plan_status != AIPlanStatus.approved:
            continue

        next_step = get_next_actionable_step(steps)
        if next_step is None:
            continue  # All steps done/skipped — nothing actionable

        remaining = get_remaining_hours(steps)
        days = compute_days_until_due(task.due_date, now)
        score = compute_urgency_score(remaining, days)
        risk = is_task_at_risk(remaining, days)
        reason = generate_reason(remaining, days, risk)

        items.append(PriorityItem(
            task_id=task.id,
            task_title=task.title,
            urgency_score=round(score, 2),
            at_risk=risk,
            reason=reason,
            remaining_hours=round(remaining, 1),
            days_until_due=round(days, 1),
            next_step=next_step,
        ))

    # Sort descending by urgency_score
    items.sort(key=lambda item: item.urgency_score, reverse=True)
    return items


def build_overview(
    tasks_with_steps: List[tuple],
    now: Optional[datetime] = None,
) -> List[OverviewItem]:
    """Build overview of all active tasks with urgency data.

    Args:
        tasks_with_steps: List of (Task, List[TaskStep]) tuples
        now: Override for current time (useful for testing)

    Returns:
        List of OverviewItem sorted descending by urgency_score
    """
    if now is None:
        now = datetime.now(timezone.utc)

    items = []
    for task, steps in tasks_with_steps:
        if task.ai_plan_status != AIPlanStatus.approved:
            continue

        remaining = get_remaining_hours(steps)
        days = compute_days_until_due(task.due_date, now)
        score = compute_urgency_score(remaining, days)
        risk = is_task_at_risk(remaining, days)

        total = len(steps)
        completed = sum(1 for s in steps if s.status == StepStatus.done)

        items.append(OverviewItem(
            task_id=task.id,
            task_title=task.title,
            urgency_score=round(score, 2),
            remaining_hours=round(remaining, 1),
            days_until_due=round(days, 1),
            at_risk=risk,
            total_steps=total,
            completed_steps=completed,
        ))

    items.sort(key=lambda item: item.urgency_score, reverse=True)
    return items
