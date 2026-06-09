from __future__ import annotations

from typing import Any

from tools.adapters.base import BaseAdapter


class MockERPAdapter(BaseAdapter):
    name = "mock_erp"

    def fetch(self, query: str, context_package: dict[str, Any]) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "domain": "customer",
            "signals": {
                "change_pct": 7.3,
                "supporting_sources": ["sales_order", "shipment"]
            }
        }
