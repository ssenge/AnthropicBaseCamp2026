"""
Tests for supplier and purchase order API endpoints.
"""
import pytest

from main import purchase_orders

VALID_PO = {
    "backlog_item_id": "1",
    "supplier_name": "Pacific Industrial Supply",
    "quantity": 350,
    "unit_cost": 6.2,
    "expected_delivery_date": "2099-12-01",
}


@pytest.fixture(autouse=True)
def clear_purchase_orders():
    """Purchase orders live in module memory, so isolate each test."""
    purchase_orders.clear()
    yield
    purchase_orders.clear()


class TestSupplierEndpoints:
    """Test suite for supplier endpoints."""

    def test_get_all_suppliers(self, client):
        """Test getting all suppliers with their structure."""
        response = client.get("/api/suppliers")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert len({s["name"] for s in data}) == len(data)
        for supplier in data:
            assert supplier["lead_time_days"] > 0
            assert 0 <= supplier["rating"] <= 5


class TestPurchaseOrderEndpoints:
    """Test suite for purchase order endpoints."""

    def test_create_purchase_order(self, client):
        """Test that a new PO is retrievable and sets the backlog flag."""
        response = client.post("/api/purchase-orders", json=VALID_PO)
        assert response.status_code == 201
        po = response.json()
        assert po["status"] == "Submitted"
        assert po["expected_delivery_date"] == "2099-12-01"
        assert client.get("/api/purchase-orders/1").json()["id"] == po["id"]

        flags = {b["id"]: b["has_purchase_order"] for b in client.get("/api/backlog").json()}
        assert flags["1"] is True
        assert flags["2"] is False

    def test_second_purchase_order_rejected(self, client):
        """Test that a backlog item can only have one PO."""
        client.post("/api/purchase-orders", json=VALID_PO)
        assert client.post("/api/purchase-orders", json=VALID_PO).status_code == 409
        assert len(purchase_orders) == 1

    def test_get_nonexistent_purchase_order(self, client):
        """Test a backlog item without a PO."""
        response = client.get("/api/purchase-orders/1")
        assert response.status_code == 404
        assert "no purchase order" in response.json()["detail"].lower()

    @pytest.mark.parametrize("change, status", [
        ({"backlog_item_id": "nope"}, 404),
        ({"supplier_name": "Nobody Ltd"}, 400),
        ({"expected_delivery_date": "2020-01-01"}, 400),
        ({"quantity": 351}, 400),
        ({"quantity": 0}, 422),
        ({"unit_cost": 0}, 422),
        ({"expected_delivery_date": "soon"}, 422),
        ({"notes": "x" * 501}, 422),
    ])
    def test_invalid_purchase_order_rejected(self, client, change, status):
        """Test that bad input is rejected and nothing is stored."""
        assert client.post("/api/purchase-orders", json={**VALID_PO, **change}).status_code == status
        assert purchase_orders == []
