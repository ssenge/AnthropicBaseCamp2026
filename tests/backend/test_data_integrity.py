"""
Tests for mock data consistency and filter edge cases.
"""
import pytest


class TestDataIntegrity:
    """The UI keys rows on these fields, so they must be unique."""

    @pytest.mark.parametrize("endpoint, field", [
        ("orders", "id"),
        ("orders", "order_number"),
        ("inventory", "id"),
        ("demand", "id"),
        ("backlog", "id"),
    ])
    def test_field_is_unique(self, client, endpoint, field):
        values = [row[field] for row in client.get(f"/api/{endpoint}").json()]
        assert len(values) == len(set(values))

    def test_every_order_reachable_by_id(self, client):
        for order in client.get("/api/orders").json():
            assert client.get(f"/api/orders/{order['id']}").json()["order_number"] == order["order_number"]

    def test_every_forecast_can_be_priced(self, client):
        for forecast in client.get("/api/demand").json():
            assert forecast["unit_cost"] > 0
            assert forecast["lead_time_days"] > 0


class TestFilterEdgeCases:
    """Filter branches the feature tests don't reach."""

    @pytest.mark.parametrize("quarter, months", [
        ("Q1-2025", ("2025-01", "2025-02", "2025-03")),
        ("Q4-2025", ("2025-10", "2025-11", "2025-12")),
    ])
    def test_get_orders_by_quarter(self, client, quarter, months):
        data = client.get(f"/api/orders?month={quarter}").json()
        assert len(data) > 0
        assert all(order["order_date"][:7] in months for order in data)

    def test_unknown_quarter_returns_everything(self, client):
        everything = client.get("/api/orders").json()
        assert len(client.get("/api/orders?month=Q9-2099").json()) == len(everything)

    def test_all_means_no_filter(self, client):
        everything = client.get("/api/orders").json()
        filtered = client.get("/api/orders?warehouse=all&category=all&status=all&month=all").json()
        assert len(filtered) == len(everything)

    def test_quarterly_report_sums_match_orders(self, client):
        orders = client.get("/api/orders").json()
        rows = client.get("/api/reports/quarterly").json()
        assert sum(r["total_revenue"] for r in rows) == pytest.approx(sum(o["total_value"] for o in orders))
