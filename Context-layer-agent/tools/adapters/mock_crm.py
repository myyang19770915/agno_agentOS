from __future__ import annotations

from typing import Any

from tools.adapters.base import BaseAdapter


class MockCRMAdapter(BaseAdapter):
    name = "mock_crm"

    def fetch(self, query: str, context_package: dict[str, Any]) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "domain": "customer",
            "signals": {
                "active_customer_count": 128,
                "trend": "上升",
                "top_segments": ["A級客戶", "北區製造"]
            }
        }
