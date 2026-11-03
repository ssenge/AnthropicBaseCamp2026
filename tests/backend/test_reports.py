"""
Tests for reports API endpoints.
"""
import pytest


@pytest.mark.parametrize("endpoint", ["quarterly", "monthly-trends"])
class TestReportFilters:
    """The reports must respect the same filters as the rest of the app."""

    @staticmethod
    def order_count(rows):
        return sum(r.get("total_orders", r.get("order_count")) for r in rows)

    @pytest.mark.parametrize("query, order_query", [
        ("warehouse=Tokyo", "warehouse=Tokyo"),
        ("category=sensors", "category=sensors"),
        ("status=delivered", "status=delivered"),
        ("month=2025-01", "month=2025-01"),
        ("warehouse=London&category=sensors&month=2025-03", "warehouse=London&category=sensors&month=2025-03"),
    ])
    def test_filter_matches_orders_endpoint(self, client, endpoint, query, order_query):
        rows = client.get(f"/api/reports/{endpoint}?{query}").json()
        orders = client.get(f"/api/orders?{order_query}").json()
        assert self.order_count(rows) == len(orders)

    def test_filter_narrows_results(self, client, endpoint):
        everything = self.order_count(client.get(f"/api/reports/{endpoint}").json())
        tokyo = self.order_count(client.get(f"/api/reports/{endpoint}?warehouse=Tokyo").json())
        assert 0 < tokyo < everything

    def test_no_match_returns_empty(self, client, endpoint):
        assert client.get(f"/api/reports/{endpoint}?warehouse=Nowhere").json() == []
