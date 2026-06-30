"""Tests for daily notification alerts, Claude prompt copy, and mark-as-read API."""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from app.models.notification import Notification
from app.models.task import AIPlanStatus
from app.services.notifier import generate_notification_for_user, run_daily_notifications


def create_task_and_steps(client, auth_headers):
    """Helper to create a task and approved plan for testing."""
    task_resp = client.post(
        "/tasks",
        headers=auth_headers,
        json={
            "title": "Machine Learning Exam",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "task_type": "project",
        },
    )
    task_id = task_resp.json()["id"]

    client.patch(
        f"/tasks/{task_id}",
        headers=auth_headers,
        json={"ai_plan_status": "pending_approval"},
    )

    client.post(
        f"/tasks/{task_id}/approve-plan",
        headers=auth_headers,
        json={
            "steps": [
                {"title": "Review linear regression math", "estimated_hours": 2.0, "order_index": 0}
            ]
        },
    )
    return task_id


def test_notification_api_lifecycle(client, auth_headers, db):
    """Test generating a notification, listing notifications, and marking read."""
    create_task_and_steps(client, auth_headers)

    # 1. Trigger generate-now endpoint
    resp = client.post("/notifications/generate-now", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["read"] is False
    assert "Review linear regression math" in data["message"]
    assert "Machine Learning Exam" in data["message"]

    notification_id = data["id"]

    # 2. Get notifications list
    list_resp = client.get("/notifications", headers=auth_headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert len(list_data) >= 1
    assert list_data[0]["id"] == notification_id

    # 3. Mark notification as read
    patch_resp = client.patch(f"/notifications/{notification_id}", headers=auth_headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["read"] is True

    # 4. Verify in DB
    db_notif = db.query(Notification).filter(Notification.id == notification_id).first()
    assert db_notif.read is True


@patch("anthropic.Anthropic")
def test_notification_uses_claude_when_key_configured(mock_anthropic_class, client, auth_headers, db):
    """Test that notifications use Claude if ANTHROPIC_API_KEY is configured."""
    create_task_and_steps(client, auth_headers)

    from app.config import settings
    original_key = settings.ANTHROPIC_API_KEY
    settings.ANTHROPIC_API_KEY = "mock_key_present"

    # Setup mock Claude response
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=' "Hey friend, focus on reviewing linear regression math today! You got this." ')]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic_class.return_value = mock_client

    try:
        # Call generate-now (Task A from previous test exists in SQLite db)
        resp = client.post("/notifications/generate-now", headers=auth_headers)
        assert resp.status_code == 200
        # Should be stripped of quotes
        assert resp.json()["message"] == "Hey friend, focus on reviewing linear regression math today! You got this."
        mock_client.messages.create.assert_called_once()
    finally:
        settings.ANTHROPIC_API_KEY = original_key


def test_run_daily_notifications_background_job(client, auth_headers, db):
    """Test running the daily notification cron-style runner across all users."""
    create_task_and_steps(client, auth_headers)

    # Ensure there's a notification generated for user ID 1
    count = run_daily_notifications(db)
    assert count >= 1

    # Verify notifications table has the entries
    entries = db.query(Notification).all()
    assert len(entries) >= 1
