"""Tests for real-time schedule re-planning and data capture."""

from datetime import datetime, timezone, timedelta
from app.models.task_step import StepStatus


def test_real_time_replanning_and_hours_capture(client, auth_headers):
    # Create task with a due date 4 days out
    due_date = datetime.now(timezone.utc) + timedelta(days=4)
    task_resp = client.post(
        "/tasks",
        headers=auth_headers,
        json={
            "title": "AWS Deployment Coursework",
            "due_date": due_date.isoformat(),
            "task_type": "project",
        },
    )
    task_id = task_resp.json()["id"]

    # Manually transition to pending_approval and approve steps
    client.patch(
        f"/tasks/{task_id}",
        headers=auth_headers,
        json={"ai_plan_status": "pending_approval"},
    )

    approve_resp = client.post(
        f"/tasks/{task_id}/approve-plan",
        headers=auth_headers,
        json={
            "steps": [
                {"title": "Step A", "estimated_hours": 2.0, "order_index": 0},
                {"title": "Step B", "estimated_hours": 4.0, "order_index": 1},
                {"title": "Step C", "estimated_hours": 3.0, "order_index": 2},
            ]
        },
    )
    assert approve_resp.status_code == 200
    initial_steps = approve_resp.json()["steps"]

    step_a_id = initial_steps[0]["id"]
    step_b_id = initial_steps[1]["id"]
    step_c_id = initial_steps[2]["id"]

    step_a_initial_date = initial_steps[0]["scheduled_date"]
    step_b_initial_date = initial_steps[1]["scheduled_date"]
    step_c_initial_date = initial_steps[2]["scheduled_date"]

    assert step_a_initial_date is not None
    assert step_b_initial_date is not None
    assert step_c_initial_date is not None

    # Step 1: Mark Step A as done with actual hours logged (e.g. 1.5h)
    patch_resp = client.patch(
        f"/steps/{step_a_id}",
        headers=auth_headers,
        json={
            "status": "done",
            "actual_hours_spent": 1.5,
        },
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()

    # Verify Step A properties
    updated_step_a = patch_data["step"]
    assert updated_step_a["status"] == "done"
    assert updated_step_a["actual_hours_spent"] == 1.5
    assert updated_step_a["completed_at"] is not None
    # Historical date of Step A must be unchanged
    assert updated_step_a["scheduled_date"] == step_a_initial_date

    # Verify other steps were re-scheduled
    updated_steps = {s["id"]: s for s in patch_data["all_steps"]}
    assert updated_steps[step_a_id]["scheduled_date"] == step_a_initial_date
    # Step B and Step C schedule dates should still exist (no crash, they represent remaining steps)
    assert updated_steps[step_b_id]["scheduled_date"] is not None
    assert updated_steps[step_c_id]["scheduled_date"] is not None


def test_task_at_risk_detection(client, auth_headers):
    # Create task with a short due date (1 day out) and large estimated hours (10 hours)
    due_date = datetime.now(timezone.utc) + timedelta(days=1)
    task_resp = client.post(
        "/tasks",
        headers=auth_headers,
        json={
            "title": "Cramming Project",
            "due_date": due_date.isoformat(),
            "task_type": "project",
        },
    )
    task_id = task_resp.json()["id"]

    client.patch(
        f"/tasks/{task_id}",
        headers=auth_headers,
        json={"ai_plan_status": "pending_approval"},
    )

    approve_resp = client.post(
        f"/tasks/{task_id}/approve-plan",
        headers=auth_headers,
        json={
            "steps": [
                {"title": "Cram step", "estimated_hours": 10.0, "order_index": 0},
            ]
        },
    )
    step_id = approve_resp.json()["steps"][0]["id"]

    # Changing status to in_progress triggers recompute of at_risk
    patch_resp = client.patch(
        f"/steps/{step_id}",
        headers=auth_headers,
        json={"status": "in_progress"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["task_at_risk"] is True
