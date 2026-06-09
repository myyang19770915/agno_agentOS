"""
app/core/reranker.py — Reranker 封裝
使用 BAAI/bge-reranker-v2-m3 (vLLM) 對檢索結果進行重排序，
讓最終結果更貼近使用者 query 的語意。
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class Reranker:
    """透過 vLLM Cross-Encoder API 進行 Rerank。"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        top_n: Optional[int] = None,
        truncate_prompt_tokens: int = 2000,
        timeout: int = 30,
    ):
        self.base_url = base_url or settings.RERANKER_BASE_URL
        self.model_name = model_name or settings.RERANKER_MODEL
        self.top_n = top_n or settings.RERANKER_TOP_N
        self.truncate_prompt_tokens = truncate_prompt_tokens
        self.timeout = timeout

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        content_key: str = "content",
    ) -> List[Tuple[Dict, float]]:
        """
        對檢索結果進行 Rerank。

        Args:
            query: 使用者查詢
            documents: 從 Postgres 取回的文件列表（dict）
            content_key: dict 中代表文件內容的 key

        Returns:
            按 rerank 分數降序排列的 (document, score) 列表
        """
        if not documents:
            return []

        texts = [doc.get(content_key, "") for doc in documents]

        payload = {
            "model": self.model_name,
            "text_1": [query] * len(texts),
            "text_2": texts,
            "truncate_prompt_tokens": self.truncate_prompt_tokens,
        }

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{self.base_url}/score",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            if "data" in result and isinstance(result["data"], list):
                scores_data = sorted(result["data"], key=lambda x: x.get("index", 0))
                scores = [item.get("score", 0.0) for item in scores_data]
            else:
                logger.error("Unexpected reranker API response format: %s", result)
                scores = [0.0] * len(documents)

        except requests.exceptions.RequestException as exc:
            logger.error("Reranker API call failed: %s", exc)
            # Rerank 失敗時保持原始順序
            return [(doc, 0.0) for doc in documents]

        if len(scores) != len(documents):
            logger.error(
                "Reranker returned %d scores for %d documents, keeping original order",
                len(scores), len(documents),
            )
            return [(doc, 0.0) for doc in documents]

        # 組合並按分數降序排列
        paired = list(zip(documents, scores))
        paired.sort(key=lambda x: x[1], reverse=True)

        # 限制 top_n
        if self.top_n and self.top_n > 0:
            paired = paired[: self.top_n]

        return paired


# 模組級單例
reranker = Reranker()
