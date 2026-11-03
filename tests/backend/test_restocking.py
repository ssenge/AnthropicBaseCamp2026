"""
Tests for restocking API endpoints.
"""
import pytest

from main import restock_orders


@pytest.fixture(autouse=True)
def clear_restock_orders():
    """Submitted orders live in module memory, so isolate each test."""
    restock_orders.clear()
    yield
    restock_orders.clear()


class TestRestockRecommendations:
    """Test suite for budget-based recommendations."""

    def test_zero_budget_recommends_nothing(self, client):
        data = client.get("/api/restocking/recommendations?budget=0").json()
        assert data["recommendations"] == []
        assert data["total_cost"] == 0
        assert data["max_budget"] > 0

    def test_never_exceeds_budget(self, client):
        max_budget = client.get("/api/restocking/recommendations?budget=0").json()["max_budget"]
        for budget in [50, 1000, 5000, 20000, max_budget]:
            data = client.get(f"/api/restocking/recommendations?budget={budget}").json()
            assert data["total_cost"] <= budget
            assert data["remaining_budget"] == pytest.approx(budget - data["total_cost"])

    def test_max_budget_covers_every_need(self, client):
        max_budget = client.get("/api/restocking/recommendations?budget=0").json()["max_budget"]
        data = client.get(f"/api/restocking/recommendations?budget={max_budget}").json()
        assert all(r["quantity"] == r["needed"] for r in data["recommendations"])
        assert data["total_cost"] == pytest.approx(max_budget)

    def test_urgent_items_are_funded_first(self, client):
        data = client.get("/api/restocking/recommendations?budget=500").json()
        assert data["recommendations"]
        assert all(r["trend"] == "increasing" for r in data["recommendations"])

    def test_sku_with_enough_stock_is_excluded(self, client):
        # PSU-501 forecasts 252 units against 420 on hand
        max_budget = client.get("/api/restocking/recommendations?budget=0").json()["max_budget"]
        data = client.get(f"/api/restocking/recommendations?budget={max_budget}").json()
        assert "PSU-501" not in [r["item_sku"] for r in data["recommendations"]]

    def test_negative_budget_rejected(self, client):
        assert client.get("/api/restocking/recommendations?budget=-1").status_code == 422


class TestRestockOrders:
    """Test suite for submitting restocking orders."""

    def test_submit_order(self, client):
        plan = client.get("/api/restocking/recommendations?budget=5000").json()
        items = [{"item_sku": r["item_sku"], "quantity": r["quantity"]} for r in plan["recommendations"]]
        response = client.post("/api/restocking/orders", json={"budget": 5000, "items": items})
        assert response.status_code == 201
        order = response.json()
        assert order["status"] == "Submitted"
        assert order["total_cost"] == plan["total_cost"]
        assert order["lead_time_days"] == max(r["lead_time_days"] for r in plan["recommendations"])
        assert client.get("/api/restocking/orders").json()[0]["id"] == order["id"]

    def test_client_cannot_set_price(self, client):
        order = client.post("/api/restocking/orders", json={
            "budget": 100000,
            "items": [{"item_sku": "WDG-001", "quantity": 10, "unit_cost": 0.01}]
        }).json()
        assert order["total_cost"] == 125.0

    @pytest.mark.parametrize("body", [
        {"budget": 10, "items": [{"item_sku": "WDG-001", "quantity": 10}]},
        {"budget": 100000, "items": [{"item_sku": "NOPE", "quantity": 1}]},
        {"budget": 100000, "items": [{"item_sku": "PSU-501", "quantity": 1}]},
        {"budget": 100000, "items": [{"item_sku": "WDG-001", "quantity": 451}]},
        {"budget": 100000, "items": [{"item_sku": "WDG-001", "quantity": 1}, {"item_sku": "WDG-001", "quantity": 1}]},
    ])
    def test_invalid_order_returns_400(self, client, body):
        assert client.post("/api/restocking/orders", json=body).status_code == 400
        assert client.get("/api/restocking/orders").json() == []

    @pytest.mark.parametrize("body", [
        {"budget": 100, "items": []},
        {"budget": 100, "items": [{"item_sku": "WDG-001", "quantity": 0}]},
        {"budget": -1, "items": [{"item_sku": "WDG-001", "quantity": 1}]},
    ])
    def test_malformed_order_returns_422(self, client, body):
        assert client.post("/api/restocking/orders", json=body).status_code == 422
