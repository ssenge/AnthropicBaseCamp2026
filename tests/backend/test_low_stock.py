"""
Tests for low-stock alert API endpoints.
"""


class TestLowStockEndpoints:
    """Test suite for low-stock alerts."""

    def test_get_all_alerts(self, client):
        """Test that alerts are items at or below their reorder point."""
        data = client.get("/api/inventory/low-stock").json()
        assert len(data) > 0
        for alert in data:
            assert alert["quantity_on_hand"] <= alert["reorder_point"]
            assert alert["shortfall"] == alert["reorder_point"] - alert["quantity_on_hand"]
            assert alert["severity"] in ["critical", "warning"]

    def test_route_is_not_captured_by_item_id(self, client):
        """Test that the route isn't treated as /api/inventory/{item_id}."""
        assert isinstance(client.get("/api/inventory/low-stock").json(), list)

    def test_alerts_match_dashboard_count(self, client):
        """Test cross-endpoint consistency, overall and when filtered."""
        for query in ["", "?warehouse=Tokyo", "?category=sensors", "?warehouse=London&category=sensors"]:
            alerts = client.get(f"/api/inventory/low-stock{query}").json()
            summary = client.get(f"/api/dashboard/summary{query}").json()
            assert len(alerts) == summary["low_stock_items"]

    def test_alerts_ordered_most_depleted_first(self, client):
        """Test the ordering by remaining fraction of the reorder point."""
        data = client.get("/api/inventory/low-stock").json()
        fractions = [a["quantity_on_hand"] / a["reorder_point"] for a in data]
        assert fractions == sorted(fractions)

    def test_get_alerts_by_warehouse(self, client):
        """Test filtering alerts by warehouse."""
        for alert in client.get("/api/inventory/low-stock?warehouse=Tokyo").json():
            assert alert["warehouse"] == "Tokyo"

    def test_no_match_returns_empty(self, client):
        """Test a filter that matches nothing."""
        assert client.get("/api/inventory/low-stock?warehouse=Nowhere").json() == []
