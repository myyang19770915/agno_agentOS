from __future__ import annotations

from typing import Any

from tools.adapters.base import BaseAdapter


class MockCaseAdapter(BaseAdapter):
    name = "mock_case"

    def fetch(self, query: str, context_package: dict[str, Any]) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "domain": "case",
            "signals": {
                "open_case_count": 23,
                "high_priority_open_cases": 5,
                "top_case_categories": ["交期", "品質", "技術支援"]
            }
        }
