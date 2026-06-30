"""Tests for AI task decomposition endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.models.task import AIPlanStatus
from app.models.task_step import TaskStep, StepStatus


@pytest.fixture()
def mock_anthropic():
    """Mock the Anthropic Async Client to return structured tool output."""
    with patch("anthropic.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_messages = AsyncMock()
        mock_client.messages = mock_messages
        mock_cls.return_value = mock_client

        # Mock tool use response block
        mock_tool_use = MagicMock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "create_task_decomposition"
        mock_tool_use.input = {
            "task_summary": "Decompose the AWS deployment task.",
            "steps": [
                {
                    "title": "Configure AWS account",
                    "description": "Log into console and configure IAM user credentials.",
                    "estimated_hours": 1.0,
                    "suggested_order": 0,
                },
                {
                    "title": "Launch EC2 Instance",
                    "description": "Launch Ubuntu EC2 instance and set up security groups.",
                    "estimated_hours": 2.5,
                    "suggested_order": 1,
                },
            ],
            "total_estimated_hours": 3.5,
            "confidence_note": "Assumes basic AWS familiarity.",
        }

        mock_response = MagicMock()
        mock_response.content = [mock_tool_use]
        mock_messages.create.return_value = mock_response

        yield mock_messages


class TestAIPlan:
    """Plan generation and approval tests."""

    def test_generate_plan_success(self, client, auth_headers, mock_anthropic):
        # Create a task first
        task_resp = client.post(
            "/tasks",
            headers=auth_headers,
            json={
                "title": "Deploy AWS EC2",
                "raw_description": "Set up server",
                "task_type": "project",
            },
        )
        task_id = task_resp.json()["id"]

        # Call generate plan
        # Temporarily pass a dummy key via settings update to bypass key checks
        from app.config import settings
        original_key = settings.ANTHROPIC_API_KEY
        settings.ANTHROPIC_API_KEY = "test-key"

        try:
            response = client.post(f"/tasks/{task_id}/generate-plan", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Verify task fields updated
            task_data = data["task"]
            assert task_data["ai_plan_status"] == "pending_approval"
            assert task_data["task_summary"] == "Decompose the AWS deployment task."
            assert task_data["ai_confidence_note"] == "Assumes basic AWS familiarity."

            # Verify proposed steps created
            steps_data = data["steps"]
            assert len(steps_data) == 2
            assert steps_data[0]["title"] == "Configure AWS account"
            assert steps_data[0]["estimated_hours"] == 1.0
            assert steps_data[0]["order_index"] == 0
            assert steps_data[0]["status"] == "pending"

            assert steps_data[1]["title"] == "Launch EC2 Instance"
            assert steps_data[1]["estimated_hours"] == 2.5
            assert steps_data[1]["order_index"] == 1
            assert steps_data[1]["status"] == "pending"
        finally:
            settings.ANTHROPIC_API_KEY = original_key

    def test_generate_plan_missing_api_key(self, client, auth_headers):
        task_resp = client.post(
            "/tasks",
            headers=auth_headers,
            json={"title": "Test Task"},
        )
        task_id = task_resp.json()["id"]

        from app.config import settings
        original_key = settings.ANTHROPIC_API_KEY
        original_fallback = settings.ALLOW_MOCK_FALLBACK
        settings.ANTHROPIC_API_KEY = ""
        settings.ALLOW_MOCK_FALLBACK = False

        try:
            response = client.post(f"/tasks/{task_id}/generate-plan", headers=auth_headers)
            assert response.status_code == 502
            assert "Anthropic API key is not configured" in response.json()["detail"]
        finally:
            settings.ANTHROPIC_API_KEY = original_key
            settings.ALLOW_MOCK_FALLBACK = original_fallback

    def test_generate_plan_handles_rate_limit(self, client, auth_headers):
        # Create a task
        task_resp = client.post("/tasks", headers=auth_headers, json={"title": "AWS Deploy"})
        task_id = task_resp.json()["id"]

        # Mock rate limit exception
        import anthropic
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_client = MagicMock()
            mock_messages = AsyncMock()
            mock_messages.create.side_effect = anthropic.RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(),
                body={}
            )
            mock_client.messages = mock_messages
            mock_cls.return_value = mock_client

            from app.config import settings
            original_key = settings.ANTHROPIC_API_KEY
            settings.ANTHROPIC_API_KEY = "test-key"

            try:
                response = client.post(f"/tasks/{task_id}/generate-plan", headers=auth_headers)
                assert response.status_code == 502
                assert "rate limit exceeded" in response.json()["detail"].lower()
            finally:
                settings.ANTHROPIC_API_KEY = original_key

    def test_approve_plan_success(self, client, auth_headers, mock_anthropic):
        # Create task, generate plan, then approve with user edits
        task_resp = client.post(
            "/tasks",
            headers=auth_headers,
            json={
                "title": "AWS EC2 App",
                "due_date": "2026-07-10T23:59:59Z", # set due date for scheduler
            },
        )
        task_id = task_resp.json()["id"]

        from app.config import settings
        original_key = settings.ANTHROPIC_API_KEY
        settings.ANTHROPIC_API_KEY = "test-key"

        try:
            # Step 1: Generate plan
            client.post(f"/tasks/{task_id}/generate-plan", headers=auth_headers)

            # Step 2: Approve the plan with customized steps
            response = client.post(
                f"/tasks/{task_id}/approve-plan",
                headers=auth_headers,
                json={
                    "steps": [
                        {
                            "title": "Step A (User Edit)",
                            "description": "User custom instructions",
                            "estimated_hours": 1.5,
                            "order_index": 0,
                        },
                        {
                            "title": "Step B",
                            "description": "Second step",
                            "estimated_hours": 3.0,
                            "order_index": 1,
                        },
                    ]
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Task status is approved
            assert data["task"]["ai_plan_status"] == "approved"

            # Check steps
            steps = data["steps"]
            assert len(steps) == 2
            assert steps[0]["title"] == "Step A (User Edit)"
            assert steps[0]["estimated_hours"] == 1.5
            assert steps[0]["scheduled_date"] is not None

            assert steps[1]["title"] == "Step B"
            assert steps[1]["estimated_hours"] == 3.0
            assert steps[1]["scheduled_date"] is not None
        finally:
            settings.ANTHROPIC_API_KEY = original_key

    def test_approve_plan_requires_pending_approval(self, client, auth_headers):
        # Create task but don't generate plan
        task_resp = client.post("/tasks", headers=auth_headers, json={"title": "Unprepared Task"})
        task_id = task_resp.json()["id"]

        response = client.post(
            f"/tasks/{task_id}/approve-plan",
            headers=auth_headers,
            json={"steps": []},
        )
        assert response.status_code == 400
        assert "not been generated or is already approved" in response.json()["detail"]
