"""
app/core/vector_db.py — Qdrant 連線與 Hybrid Search 邏輯
採用 Qdrant 原生 Hybrid Search：透過 prefetch + query(fusion=RRF)
在 Server 端完成 Dense + Sparse (BM25) 融合，無需 Python 端 RRF。
參考: https://qdrant.tech/documentation/search/hybrid-queries/
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    SparseVectorParams,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorDB:
    """Qdrant Hybrid Search 封裝（使用原生 prefetch + RRF Fusion）。"""

    # Named vector 常數
    DENSE_VECTOR_NAME = "dense"
    SPARSE_VECTOR_NAME = "sparse"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection: Optional[str] = None,
    ):
        self._host = host or settings.QDRANT_HOST
        self._port = port or settings.QDRANT_PORT
        self._collection = collection or settings.QDRANT_COLLECTION

        # 若 host 包含 http:// 或 https://，使用 url 參數連線
        if self._host.startswith("http://") or self._host.startswith("https://"):
            self._client = QdrantClient(url=self._host)
        else:
            self._client = QdrantClient(host=self._host, port=self._port)

    # ---- Collection 管理 ----
    def ensure_collection(self, dim: int = 0) -> None:
        """若 Collection 不存在則建立（Named Vectors: dense + sparse）。"""
        dim = dim or settings.EMBEDDING_DIM
        collections = [c.name for c in self._client.get_collections().collections]
        if self._collection in collections:
            return
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config={
                self.DENSE_VECTOR_NAME: VectorParams(
                    size=dim, distance=Distance.COSINE
                ),
            },
            sparse_vectors_config={
                self.SPARSE_VECTOR_NAME: SparseVectorParams(),
            },
        )
        # 建立 pg_id payload 索引，加速過濾
        self._client.create_payload_index(
            collection_name=self._collection,
            field_name="pg_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        logger.info("Created collection '%s' with dim=%d (named vectors: dense+sparse)", self._collection, dim)

    # ---- 寫入 ----
    def upsert_points(self, points: List[PointStruct]) -> None:
        self._client.upsert(collection_name=self._collection, points=points)

    # ---- 檢索 ----
    def hybrid_search(
        self,
        query_vector: List[float],
        sparse_vector: models.SparseVector,
        filter_ids: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Tuple[str, float]]:
        """
        Qdrant 原生 Hybrid Search — Server 端 RRF 融合。

        使用 query_points API 搭配 prefetch:
        1. prefetch[0]: Dense 向量子查詢 (using="dense")
        2. prefetch[1]: Sparse BM25 子查詢 (using="sparse")
        3. 主 query: FusionQuery(fusion=Fusion.RRF) → Server 端融合

        Args:
            query_vector: Dense embedding 向量
            sparse_vector: Sparse (BM25) 向量
            filter_ids: 可選 pg_id 白名單
            limit: 回傳筆數

        Returns:
            按 RRF 分數降序排列的 (pg_id, score) 列表
        """
        qdrant_filter = self._build_filter(filter_ids)

        # 建立 prefetch 子查詢
        prefetch_queries = [
            models.Prefetch(
                query=query_vector,
                using=self.DENSE_VECTOR_NAME,
                filter=qdrant_filter,
                limit=limit,
            ),
            models.Prefetch(
                query=sparse_vector,
                using=self.SPARSE_VECTOR_NAME,
                filter=qdrant_filter,
                limit=limit,
            ),
        ]

        # 透過 Qdrant Server 端 RRF 融合
        results = self._client.query_points(
            collection_name=self._collection,
            prefetch=prefetch_queries,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True,
        )

        return [
            (point.payload.get("pg_id", str(point.id)), point.score)
            for point in results.points
        ]

    def dense_search(
        self,
        query_vector: List[float],
        filter_ids: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[str]:
        """純 Dense 向量檢索，回傳 pg_id 列表。"""
        qdrant_filter = self._build_filter(filter_ids)
        results = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            using=self.DENSE_VECTOR_NAME,
            query_filter=qdrant_filter,
            limit=limit,
            with_payload=True,
        )
        return [point.payload.get("pg_id", str(point.id)) for point in results.points]

    def sparse_search(
        self,
        sparse_vector: models.SparseVector,
        filter_ids: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[str]:
        """BM25 Sparse 檢索，回傳 pg_id 列表。"""
        qdrant_filter = self._build_filter(filter_ids)
        results = self._client.query_points(
            collection_name=self._collection,
            query=sparse_vector,
            using=self.SPARSE_VECTOR_NAME,
            query_filter=qdrant_filter,
            limit=limit,
            with_payload=True,
        )
        return [point.payload.get("pg_id", str(point.id)) for point in results.points]

    # ---- 輔助 ----
    @staticmethod
    def _build_filter(filter_ids: Optional[List[str]]) -> Optional[models.Filter]:
        if not filter_ids:
            return None
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="pg_id",
                    match=models.MatchAny(any=filter_ids),
                )
            ]
        )

    # ---- 刪除 ----
    def delete_by_pg_ids(self, pg_ids: List[str]) -> int:
        """
        根據 pg_id (Postgres PK) 刪除對應的 Qdrant points。

        當 Postgres 資料被刪除時，呼叫此方法同步清除 Qdrant 中的向量。

        Args:
            pg_ids: 要刪除的 pg_id 列表

        Returns:
            請求刪除的 pg_id 數量（Qdrant delete 為冪等操作，
            即使 ID 不存在也不會報錯）
        """
        if not pg_ids:
            logger.debug("delete_by_pg_ids called with empty list, skipping")
            return 0

        qdrant_filter = self._build_filter(pg_ids)
        self._client.delete(
            collection_name=self._collection,
            points_selector=qdrant_filter,
            wait=True,
        )
        logger.info("Deleted points matching pg_ids: %s", pg_ids)
        return len(pg_ids)

    def health_check(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception as exc:
            logger.warning("Qdrant health check failed: %s", exc)
            return False

    def count(self) -> int:
        info = self._client.get_collection(self._collection)
        return info.points_count or 0


# 模組級單例
vector_db = VectorDB()
