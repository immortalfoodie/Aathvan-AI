"""Service to synchronize tasks and steps with Google Calendar."""

from datetime import datetime, timezone, timedelta
from googleapiclient.errors import HttpError
from app.models.user import User
from app.models.task import Task
from app.models.task_step import TaskStep
from app.services.google_service import get_calendar_service


def build_calendar_event_body(task: Task, step: TaskStep) -> dict:
    """Helper to build a Google Calendar event dictionary for a step."""
    date_str = step.scheduled_date.strftime("%Y-%m-%d")
    
    # Event starts at 9:00 AM and ends 1 hour later (or estimated hours)
    start_time = f"{date_str}T09:00:00Z"
    duration = max(1.0, step.estimated_hours or 1.0)
    end_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=duration)
    end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "summary": f"⚡ {step.title}",
        "description": (
            f"Step Details: {step.description or 'No details'}\n\n"
            f"Task: {task.title}\n"
            f"Estimated Hours: {step.estimated_hours or 0.0}h\n"
            f"Status: {step.status.value}"
        ),
        "start": {
            "dateTime": start_time,
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "UTC",
        },
    }


def sync_task_to_calendar(user: User, task: Task, steps: list[TaskStep], db) -> list[TaskStep]:
    """Sync all scheduled steps of a task to the user's Google Calendar."""
    if not user.google_id:
        return steps

    try:
        service = get_calendar_service(user, db)
    except Exception:
        # If API initialization fails, return steps silently without throwing
        return steps

    for step in steps:
        if not step.scheduled_date:
            continue

        event_body = build_calendar_event_body(task, step)
        
        # If the step already has a calendar event, try updating it
        if step.calendar_event_id:
            try:
                service.events().update(
                    calendarId="primary",
                    eventId=step.calendar_event_id,
                    body=event_body,
                ).execute()
            except HttpError as e:
                if e.resp.status == 404:
                    # Event was deleted in Calendar; recreate it
                    try:
                        new_event = service.events().insert(
                            calendarId="primary",
                            body=event_body,
                        ).execute()
                        step.calendar_event_id = new_event.get("id")
                    except Exception:
                        pass
                else:
                    pass
            except Exception:
                pass
        else:
            # Create a new event
            try:
                new_event = service.events().insert(
                    calendarId="primary",
                    body=event_body,
                ).execute()
                step.calendar_event_id = new_event.get("id")
            except Exception:
                pass

    db.commit()
    return steps


def update_calendar_events_on_replan(user: User, task: Task, steps: list[TaskStep], db):
    """Update calendar events when step scheduled dates are shifted during re-planning."""
    if not user.google_id:
        return

    try:
        service = get_calendar_service(user, db)
    except Exception:
        return

    for step in steps:
        if not step.calendar_event_id or not step.scheduled_date:
            continue

        event_body = build_calendar_event_body(task, step)
        try:
            service.events().update(
                calendarId="primary",
                eventId=step.calendar_event_id,
                body=event_body,
            ).execute()
        except Exception:
            # Silently ignore errors during automatic background update
            pass
