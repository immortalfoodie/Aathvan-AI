"""Tests for Google Classroom list and import endpoints."""

from unittest.mock import MagicMock, patch
from app.models.user import User
from app.models.task import Task, TaskType


@patch("app.routers.classroom.get_classroom_service")
def test_list_classroom_courses(mock_get_service, client, db, auth_headers):
    """Test getting classroom courses for a linked user."""
    # Set google_id on test user so request is allowed
    user = db.query(User).filter(User.id == 1).first()
    user.google_id = "google_123"
    db.commit()

    # Mock Classroom API response
    mock_service = MagicMock()
    mock_service.courses().list().execute.return_value = {
        "courses": [
            {
                "id": "c1",
                "name": "Advanced Robotics",
                "section": "Spring 2026",
                "descriptionHeading": "Course Description Heading",
            }
        ]
      }
    mock_get_service.return_value = mock_service

    resp = client.get("/classroom/courses", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Advanced Robotics"
    assert data[0]["section"] == "Spring 2026"


@patch("app.routers.classroom.get_classroom_service")
def test_list_classroom_coursework(mock_get_service, client, db, auth_headers):
    """Test fetching coursework for a specific course."""
    user = db.query(User).filter(User.id == 1).first()
    user.google_id = "google_123"
    db.commit()

    mock_service = MagicMock()
    mock_service.courses().courseWork().list().execute.return_value = {
        "courseWork": [
            {
                "id": "cw1",
                "title": "Lab 1: Particle Filter",
                "description": "Implement localizing particle filters.",
                "dueDate": {"year": 2026, "month": 7, "day": 10},
                "dueTime": {"hours": 23, "minutes": 59},
                "alternateLink": "https://classroom.google.com/cw/1",
                "materials": [
                    {
                        "link": {
                            "title": "Starter Code Zip",
                            "url": "https://github.com/helper/starter.zip",
                        }
                    }
                ],
            }
        ]
    }
    mock_get_service.return_value = mock_service

    resp = client.get("/classroom/courses/c1/coursework", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Lab 1: Particle Filter"
    assert data[0]["materials"][0]["title"] == "Starter Code Zip"
    assert "2026-07-10T23:59:00" in data[0]["due_date"]


def test_import_coursework_to_tasks(client, auth_headers, db):
    """Test import coursework items as tasks."""
    payload = {
        "items": [
            {
                "coursework_id": "cw1",
                "course_id": "c1",
                "title": "Particle Filter Lab",
                "description": "Lab instructions...",
                "due_date": "2026-07-10T23:59:00Z",
                "alternate_link": "https://classroom.google.com/cw/1",
                "materials": [
                    {"title": "Starter Code Zip", "link": "https://github.com/helper/starter.zip"}
                ],
            }
        ]
    }

    resp = client.post("/classroom/import", json=payload, headers=auth_headers)
    assert resp.status_code == 201

    # Verify task row is created
    task = db.query(Task).filter(Task.title == "Particle Filter Lab").first()
    assert task is not None
    assert task.task_type == TaskType.assignment
    # Raw description should contain description instructions + resource links compiled
    assert "Lab instructions..." in task.raw_description
    assert "[Starter Code Zip](https://github.com/helper/starter.zip)" in task.raw_description
