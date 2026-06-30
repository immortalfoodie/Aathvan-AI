"""API tests — auth, task CRUD, step CRUD, and user isolation."""


class TestAuth:
    """Authentication endpoint tests."""

    def test_signup_returns_token(self, client):
        response = client.post(
            "/auth/signup",
            json={"email": "new@example.com", "password": "pass123", "name": "New User"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_signup_duplicate_email(self, client):
        client.post(
            "/auth/signup",
            json={"email": "dup@example.com", "password": "pass123", "name": "User1"},
        )
        response = client.post(
            "/auth/signup",
            json={"email": "dup@example.com", "password": "pass456", "name": "User2"},
        )
        assert response.status_code == 409

    def test_login_returns_token(self, client):
        client.post(
            "/auth/signup",
            json={"email": "login@example.com", "password": "pass123", "name": "Login User"},
        )
        response = client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "pass123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client):
        client.post(
            "/auth/signup",
            json={"email": "wrong@example.com", "password": "correct", "name": "User"},
        )
        response = client.post(
            "/auth/login",
            json={"email": "wrong@example.com", "password": "incorrect"},
        )
        assert response.status_code == 401

    def test_get_me(self, client, auth_headers):
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"

    def test_get_me_no_token(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401  # HTTPBearer returns 401 when no header


class TestTasks:
    """Task CRUD and user-scoping tests."""

    def test_create_task(self, client, auth_headers):
        response = client.post(
            "/tasks",
            headers=auth_headers,
            json={
                "title": "Finish homework",
                "raw_description": "Chapter 5 exercises",
                "task_type": "assignment",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Finish homework"
        assert data["status"] == "not_started"
        assert data["task_type"] == "assignment"

    def test_list_tasks(self, client, auth_headers):
        # Create two tasks
        client.post("/tasks", headers=auth_headers, json={"title": "Task 1"})
        client.post("/tasks", headers=auth_headers, json={"title": "Task 2"})

        response = client.get("/tasks", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_task_isolation(self, client, auth_headers, second_auth_headers):
        """Tasks created by one user should not be visible to another."""
        client.post("/tasks", headers=auth_headers, json={"title": "User1 Task"})
        client.post("/tasks", headers=second_auth_headers, json={"title": "User2 Task"})

        # User 1 should see only their task
        response = client.get("/tasks", headers=auth_headers)
        tasks = response.json()
        assert len(tasks) == 1
        assert tasks[0]["title"] == "User1 Task"

        # User 2 should see only their task
        response = client.get("/tasks", headers=second_auth_headers)
        tasks = response.json()
        assert len(tasks) == 1
        assert tasks[0]["title"] == "User2 Task"

    def test_get_task_detail(self, client, auth_headers):
        create_resp = client.post("/tasks", headers=auth_headers, json={"title": "Detail Task"})
        task_id = create_resp.json()["id"]

        response = client.get(f"/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Detail Task"

    def test_get_other_users_task_returns_404(self, client, auth_headers, second_auth_headers):
        """Attempting to access another user's task should return 404."""
        create_resp = client.post("/tasks", headers=auth_headers, json={"title": "Private Task"})
        task_id = create_resp.json()["id"]

        response = client.get(f"/tasks/{task_id}", headers=second_auth_headers)
        assert response.status_code == 404

    def test_update_task(self, client, auth_headers):
        create_resp = client.post("/tasks", headers=auth_headers, json={"title": "Original"})
        task_id = create_resp.json()["id"]

        response = client.patch(
            f"/tasks/{task_id}",
            headers=auth_headers,
            json={"title": "Updated", "status": "in_progress"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"
        assert response.json()["status"] == "in_progress"

    def test_delete_task(self, client, auth_headers):
        create_resp = client.post("/tasks", headers=auth_headers, json={"title": "To Delete"})
        task_id = create_resp.json()["id"]

        response = client.delete(f"/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify it's gone
        response = client.get(f"/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 404


class TestSteps:
    """TaskStep CRUD tests."""

    def test_create_step(self, client, auth_headers):
        task_resp = client.post("/tasks", headers=auth_headers, json={"title": "My Task"})
        task_id = task_resp.json()["id"]

        response = client.post(
            f"/tasks/{task_id}/steps",
            headers=auth_headers,
            json={"title": "Step 1", "order_index": 0},
        )
        assert response.status_code == 201
        assert response.json()["title"] == "Step 1"
        assert response.json()["status"] == "pending"

    def test_list_steps(self, client, auth_headers):
        task_resp = client.post("/tasks", headers=auth_headers, json={"title": "My Task"})
        task_id = task_resp.json()["id"]

        client.post(f"/tasks/{task_id}/steps", headers=auth_headers, json={"title": "Step 1", "order_index": 0})
        client.post(f"/tasks/{task_id}/steps", headers=auth_headers, json={"title": "Step 2", "order_index": 1})

        response = client.get(f"/tasks/{task_id}/steps", headers=auth_headers)
        assert response.status_code == 200
        steps = response.json()
        assert len(steps) == 2
        assert steps[0]["title"] == "Step 1"
        assert steps[1]["title"] == "Step 2"

    def test_update_step_status(self, client, auth_headers):
        task_resp = client.post("/tasks", headers=auth_headers, json={"title": "My Task"})
        task_id = task_resp.json()["id"]

        step_resp = client.post(
            f"/tasks/{task_id}/steps",
            headers=auth_headers,
            json={"title": "Do the thing", "order_index": 0},
        )
        step_id = step_resp.json()["id"]

        response = client.patch(
            f"/steps/{step_id}",
            headers=auth_headers,
            json={"status": "done"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["step"]["status"] == "done"
        assert "all_steps" in data
        assert "task_at_risk" in data

    def test_step_belongs_to_other_user_task(self, client, auth_headers, second_auth_headers):
        """Cannot update a step on another user's task."""
        task_resp = client.post("/tasks", headers=auth_headers, json={"title": "User1 Task"})
        task_id = task_resp.json()["id"]

        step_resp = client.post(
            f"/tasks/{task_id}/steps",
            headers=auth_headers,
            json={"title": "Private Step", "order_index": 0},
        )
        step_id = step_resp.json()["id"]

        # User 2 tries to update the step
        response = client.patch(
            f"/steps/{step_id}",
            headers=second_auth_headers,
            json={"status": "done"},
        )
        assert response.status_code == 404

    def test_delete_task_cascades_steps(self, client, auth_headers):
        task_resp = client.post("/tasks", headers=auth_headers, json={"title": "Cascade Task"})
        task_id = task_resp.json()["id"]

        client.post(f"/tasks/{task_id}/steps", headers=auth_headers, json={"title": "Step A", "order_index": 0})

        # Delete the task
        client.delete(f"/tasks/{task_id}", headers=auth_headers)

        # Steps should be gone (task is gone, so listing returns 404)
        response = client.get(f"/tasks/{task_id}/steps", headers=auth_headers)
        assert response.status_code == 404
