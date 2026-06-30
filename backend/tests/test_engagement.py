from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

def test_simulation_inaction(client: TestClient, auth_headers, db):
    # Create an active task and some steps
    from app.models.task import Task, TaskStatus, TaskType
    from app.models.task_step import TaskStep, StepStatus
    from app.models.user import User
    
    user = db.query(User).filter(User.email == "test@example.com").first()
    
    task = Task(
        user_id=user.id,
        title="Test Inaction",
        status=TaskStatus.in_progress,
        due_date=datetime.now(timezone.utc) + timedelta(days=2),
        task_type=TaskType.assignment
    )
    db.add(task)
    db.commit()
    
    step1 = TaskStep(
        task_id=task.id,
        title="Step 1",
        status=StepStatus.pending,
        estimated_hours=2.0,
        scheduled_date=datetime.now(timezone.utc) - timedelta(days=1) # Past due
    )
    step2 = TaskStep(
        task_id=task.id,
        title="Step 2",
        status=StepStatus.pending,
        estimated_hours=6.0,
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db.add_all([step1, step2])
    db.commit()

    # Call endpoint
    response = client.get(
        "/engagement/simulate/inaction",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["active_tasks_count"] >= 1
    assert data["total_remaining_hours"] >= 8.0
    
    # Check that collisions_if_inaction is > 0 because 2.0 (shifted) + 6.0 = 8.0 > 6.0
    assert data["collisions_if_inaction"] >= 1

def test_momentum_streak(client: TestClient, auth_headers):
    # Test updating streak
    res = client.post("/engagement/momentum/streak", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["streak"] >= 1
    
    # Test momentum percentage
    res2 = client.get("/engagement/momentum/today", headers=auth_headers)
    assert res2.status_code == 200
    assert "percentage" in res2.json()
