"""Scheduling services for tasks and steps.

TEMPORARY SCHEDULER:
Spreads steps evenly across available days between now and the due date.
This naive distributor is intentionally temporary and will be replaced
with a smarter cross-task constraint solver / scheduler in Step 3.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from app.models.task_step import TaskStep


def distribute_steps_across_days(
    steps: List[TaskStep],
    due_date: Optional[datetime],
) -> List[TaskStep]:
    """Naive day distribution helper.

    Spreads task steps roughly evenly across the days leading up to the due date.
    Respects order_index to schedule earlier steps on earlier days.

    If due_date is None or is in the past, all steps are scheduled for today (local/UTC time).
    """
    if not steps:
        return []

    # Sort steps by order_index just to be absolutely sure
    sorted_steps = sorted(steps, key=lambda s: s.order_index)

    # Use current time as start reference
    now = datetime.now(timezone.utc)
    if due_date and due_date.tzinfo is None:
        now = now.replace(tzinfo=None)

    if not due_date or due_date <= now:
        # No valid future due date -> schedule everything for today
        for step in sorted_steps:
            step.scheduled_date = now
        return sorted_steps

    # Calculate the number of available days
    time_delta = due_date - now
    available_days = max(1, time_delta.days)

    num_steps = len(sorted_steps)

    # Distribute steps evenly
    # Example: 5 steps, 3 days
    # step 0: day 0
    # step 1: day 0
    # step 2: day 1
    # step 3: day 1
    # step 4: day 2
    for i, step in enumerate(sorted_steps):
        # Calculate fraction of the available days for this step
        # If we have only 1 step, it lands on day 0
        if num_steps > 1:
            fraction = i / (num_steps - 1)
        else:
            fraction = 0.0

        target_day_offset = int(fraction * (available_days - 1))
        # Schedule step target_day_offset days from now
        step.scheduled_date = now + timedelta(days=target_day_offset)

    return sorted_steps
