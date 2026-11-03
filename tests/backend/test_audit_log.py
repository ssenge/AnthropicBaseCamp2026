"""
Tests for audit log API endpoints.
"""
import pytest

from main import audit_log, purchase_orders, restock_orders, tasks

TASK = {"title": "Review stock", "priority": "high", "dueDate": "2025-10-08"}


@pytest.fixture(autouse=True)
def isolate_state():
    """Writes live in module memory, so isolate each test."""
    stores = [audit_log, purchase_orders, restock_orders, tasks]
    for store in stores:
        store.clear()
    yield
    for store in stores:
        store.clear()


class TestAuditLogEndpoints:
    """Test suite for the audit trail."""

    def test_empty_log(self, client):
        """Test the log before any write."""
        assert client.get("/api/audit-log").json() == []

    def test_reads_are_not_recorded(self, client):
        """Test that GET requests leave no trail."""
        client.get("/api/orders")
        client.get("/api/tasks")
        assert client.get("/api/audit-log").json() == []

    def test_task_lifecycle_recorded_newest_first(self, client):
        """Test create, toggle, and delete."""
        task_id = client.post("/api/tasks", json=TASK).json()["id"]
        client.patch(f"/api/tasks/{task_id}")
        client.delete(f"/api/tasks/{task_id}")
        data = client.get("/api/audit-log").json()
        assert [e["action"] for e in data] == ["deleted", "updated", "created"]
        assert all(e["entity"] == "task" and e["entity_id"] == task_id for e in data)
        assert data[0]["id"] > data[1]["id"] > data[2]["id"]

    def test_restock_and_purchase_orders_recorded(self, client):
        """Test the other write endpoints."""
        client.post("/api/restocking/orders", json={"budget": 1000, "items": [{"item_sku": "WDG-001", "quantity": 10}]})
        client.post("/api/purchase-orders", json={
            "backlog_item_id": "1",
            "supplier_name": "Pacific Industrial Supply",
            "quantity": 350,
            "unit_cost": 6.2,
            "expected_delivery_date": "2099-12-01",
        })
        assert [e["entity"] for e in client.get("/api/audit-log").json()] == ["purchase_order", "restock_order"]

    def test_failed_writes_not_recorded(self, client):
        """Test that rejected requests leave no trail."""
        client.post("/api/tasks", json={**TASK, "title": ""})
        client.post("/api/restocking/orders", json={"budget": 1, "items": [{"item_sku": "WDG-001", "quantity": 10}]})
        client.patch("/api/tasks/nope")
        assert client.get("/api/audit-log").json() == []

    def test_limit(self, client):
        """Test that limit returns the newest entries."""
        for i in range(3):
            client.post("/api/tasks", json={**TASK, "title": f"Task {i}"})
        data = client.get("/api/audit-log?limit=2").json()
        assert [e["detail"] for e in data] == ["Task 2", "Task 1"]

    @pytest.mark.parametrize("limit", [0, 501])
    def test_limit_out_of_range(self, client, limit):
        """Test the limit bounds."""
        assert client.get(f"/api/audit-log?limit={limit}").status_code == 422
