"""Notification service module for generating personality-driven, context-aware reminders."""

import logging
from datetime import datetime, timezone
import anthropic

from app.config import settings
from app.models.user import User
from app.models.task import Task
from app.models.notification import Notification
from app.services.prioritizer import build_today_priorities

logger = logging.getLogger(__name__)


def generate_notification_for_user(user: User, db) -> Notification | None:
    """Generate ONE personality-driven daily notification for a single user."""
    # 1. Fetch tasks and steps
    tasks = db.query(Task).filter(Task.user_id == user.id).all()
    tasks_with_steps = [(t, t.steps) for t in tasks]

    # 2. Compute priorities
    priorities = build_today_priorities(tasks_with_steps)
    if not priorities:
        logger.info(f"No priority tasks found for user {user.id}. Skipping notification.")
        return None

    top_item = priorities[0]
    task_title = top_item.task_title
    step_title = top_item.next_step.title if top_item.next_step else "Next Step"
    days_left = top_item.days_until_due
    at_risk = top_item.at_risk

    # 3. Generate content using Claude if API key is present
    message = None
    if settings.ANTHROPIC_API_KEY:
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            system_prompt = (
                "You are an encouraging, slightly playful motivating friend (mentor/TA style). "
                "Your goal is to get the user to take action on their task without guilt-tripping, "
                "shaming, or inducing anxiety. Keep it under 25 words. Be specific, referencing "
                "the task or step directly. Do not use quotation marks."
            )
            
            user_context = (
                f"Top priority task: {task_title}\n"
                f"Next action step: {step_title}\n"
                f"Days until due: {days_left:.1f} days\n"
                f"Is at risk of missing deadline: {'Yes' if at_risk else 'No'}"
            )

            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",  # Standard sonnet model for speed & reliability
                max_tokens=100,
                system=system_prompt,
                messages=[{"role": "user", "content": user_context}],
                temperature=0.7,
            )
            
            message = response.content[0].text.strip()
            # Clean up potential leading/trailing quotes Claude might include
            if message.startswith('"') and message.endswith('"'):
                message = message[1:-1]
        except Exception as e:
            logger.error(f"Failed to generate notification via Claude: {e}")
            message = None

    # 4. Fallback to friendly template if Claude failed or key not configured
    if not message:
        if at_risk:
            message = f"Let's catch up on '{step_title}' for {task_title}. A little focus today makes all the difference! 🚀"
        elif days_left <= 1:
            message = f"Almost there! Let's get '{step_title}' done for {task_title} today. You've got this! 💪"
        else:
            message = f"Hey! Ready to make progress? Let's spend some time on '{step_title}' for {task_title} today. ✨"

    # 5. Save the generated notification
    notification = Notification(
        user_id=user.id,
        message=message,
        read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Note: Service worker web push could be fired here if VAPID keys were configured:
    # # webpush_send(user, message)

    return notification


def run_daily_notifications(db) -> int:
    """Scheduled task to generate daily notifications for all active users."""
    users = db.query(User).all()
    count = 0
    for user in users:
        try:
            notif = generate_notification_for_user(user, db)
            if notif:
                count += 1
        except Exception as e:
            logger.error(f"Error generating daily notification for user {user.id}: {e}")
    return count
