from fastapi.testclient import TestClient
from datetime import datetime, timezone

def test_estimation_learning(client: TestClient, auth_headers, db):
    from app.models.task import Task, TaskStatus, TaskType
    from app.models.task_step import TaskStep, StepStatus
    from app.models.user import User
    
    user = db.query(User).filter(User.email == "test@example.com").first()
    
    # Create task
    task = Task(
        user_id=user.id,
        title="Learning Task",
        status=TaskStatus.in_progress,
        due_date=datetime.now(timezone.utc),
        task_type=TaskType.project
    )
    db.add(task)
    db.commit()
    
    # Create steps with est and actual hours
    step1 = TaskStep(
        task_id=task.id,
        title="Step A",
        status=StepStatus.done,
        estimated_hours=2.0,
        actual_hours_spent=4.0 # Took 2x as long
    )
    db.add(step1)
    db.commit()
    
    # Update task to completed, which should trigger the profile update
    res = client.patch(
        f"/tasks/{task.id}",
        json={"status": "completed"},
        headers=auth_headers
    )
    assert res.status_code == 200
    
    # Check autopsy
    res_autopsy = client.get(
        f"/tasks/{task.id}/autopsy",
        headers=auth_headers
    )
    assert res_autopsy.status_code == 200
    data = res_autopsy.json()
    assert data["adjustment_factor_after"] == 2.0
