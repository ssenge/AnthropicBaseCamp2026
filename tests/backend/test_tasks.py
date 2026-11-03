"""
Tests for tasks API endpoints.
"""
import pytest

from main import tasks

VALID_TASK = {"title": "Review stock", "priority": "high", "dueDate": "2025-10-08"}


@pytest.fixture(autouse=True)
def clear_tasks():
    """Tasks live in module memory, so isolate each test."""
    tasks.clear()
    yield
    tasks.clear()


class TestTasksEndpoints:
    """Test suite for task-related endpoints."""

    def test_get_all_tasks_empty(self, client):
        """Test the empty list that App.vue loads on every page."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_task(self, client):
        """Test that a new task starts pending and is listed newest first."""
        client.post("/api/tasks", json={**VALID_TASK, "title": "First"})
        response = client.post("/api/tasks", json=VALID_TASK)
        assert response.status_code == 201
        task = response.json()
        assert task["status"] == "pending"
        assert task["dueDate"] == "2025-10-08"
        assert isinstance(task["id"], str)
        assert [t["title"] for t in client.get("/api/tasks").json()] == ["Review stock", "First"]

    def test_toggle_task(self, client):
        """Test that PATCH flips the status both ways."""
        task_id = client.post("/api/tasks", json=VALID_TASK).json()["id"]
        assert client.patch(f"/api/tasks/{task_id}").json()["status"] == "completed"
        assert client.patch(f"/api/tasks/{task_id}").json()["status"] == "pending"

    def test_delete_task(self, client):
        """Test that a deleted task is gone and its id isn't reused."""
        task_id = client.post("/api/tasks", json=VALID_TASK).json()["id"]
        assert client.delete(f"/api/tasks/{task_id}").status_code == 200
        assert client.get("/api/tasks").json() == []
        assert client.post("/api/tasks", json=VALID_TASK).json()["id"] != task_id

    @pytest.mark.parametrize("method", ["patch", "delete"])
    def test_nonexistent_task(self, client, method):
        """Test that unknown ids return 404."""
        response = getattr(client, method)("/api/tasks/nope")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.parametrize("change", [
        {"title": ""},
        {"priority": "urgent"},
        {"dueDate": "soon"},
    ])
    def test_invalid_task_rejected(self, client, change):
        """Test that bad input returns 422."""
        assert client.post("/api/tasks", json={**VALID_TASK, **change}).status_code == 422
        assert client.get("/api/tasks").json() == []
