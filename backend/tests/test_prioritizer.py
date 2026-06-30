"""Tests for cross-task prioritization service and endpoints."""

from datetime import datetime, timezone, timedelta
from app.models.task import AIPlanStatus
from app.models.task_step import StepStatus
from app.services.prioritizer import (
    compute_urgency_score,
    compute_days_until_due,
    is_task_at_risk,
    generate_reason,
)


def test_compute_days_until_due():
    now = datetime.now(timezone.utc)
    due = now + timedelta(days=5)
    days = compute_days_until_due(due, now)
    assert 4.9 < days <= 5.0

    days_none = compute_days_until_due(None, now)
    assert days_none == 365.0


def test_urgency_score_calculation():
    # 10 hours left, 2 days until due
    assert compute_urgency_score(10.0, 2.0) == 5.0

    # Overdue task (clamped to 0.5 minimum days)
    assert compute_urgency_score(10.0, -1.0) == 20.0
    assert compute_urgency_score(10.0, 0.0) == 20.0

    # Done task
    assert compute_urgency_score(0.0, 5.0) == 0.0


def test_at_risk_detection():
    # 10h remaining / 2 days left = 5.0 urgency (> 4.0 threshold) -> at risk
    assert is_task_at_risk(10.0, 2.0, daily_capacity=4.0) is True

    # 6h remaining / 2 days left = 3.0 urgency (<= 4.0 threshold) -> not at risk
    assert is_task_at_risk(6.0, 2.0, daily_capacity=4.0) is False


def test_generate_reason():
    # Overdue
    assert "Overdue" in generate_reason(5.0, -0.5, False)
    # Urgent
    assert "highest urgency" in generate_reason(8.0, 1.5, False)
    # At risk
    assert "needs more time" in generate_reason(10.0, 2.0, True)


def test_priority_endpoints(client, auth_headers):
    # Setup: Create two tasks
    task_a = client.post(
        "/tasks",
        headers=auth_headers,
        json={
            "title": "Task A (High Urgency)",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "task_type": "project",
        },
    ).json()

    task_b = client.post(
        "/tasks",
        headers=auth_headers,
        json={
            "title": "Task B (Low Urgency)",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
            "task_type": "assignment",
        },
    ).json()

    # Move both tasks to pending_approval and then approved
    for t_id in (task_a["id"], task_b["id"]):
        # Simulate AI plan generation by updating fields
        client.patch(
            f"/tasks/{t_id}",
            headers=auth_headers,
            json={"ai_plan_status": "pending_approval"},
        )
        # Approve plan with mock steps
        client.post(
            f"/tasks/{t_id}/approve-plan",
            headers=auth_headers,
            json={
                "steps": [
                    {
                        "title": "Step 1",
                        "estimated_hours": 6.0 if t_id == task_a["id"] else 2.0,
                        "order_index": 0,
                    }
                ]
            },
        )

    # Call today priority list
    response = client.get("/priority/today", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    # Should return both tasks ordered by urgency score (Task A higher than Task B)
    assert len(data) == 2
    assert data[0]["task_title"] == "Task A (High Urgency)"
    assert data[1]["task_title"] == "Task B (Low Urgency)"
    assert data[0]["urgency_score"] > data[1]["urgency_score"]

    # Call overview endpoint
    overview_resp = client.get("/priority/overview", headers=auth_headers)
    assert overview_resp.status_code == 200
    ov_data = overview_resp.json()
    assert len(ov_data) == 2
    assert ov_data[0]["task_title"] == "Task A (High Urgency)"
    assert ov_data[0]["total_steps"] == 1
    assert ov_data[0]["completed_steps"] == 0
