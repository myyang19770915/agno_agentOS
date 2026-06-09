from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self, query: str, context_package: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
