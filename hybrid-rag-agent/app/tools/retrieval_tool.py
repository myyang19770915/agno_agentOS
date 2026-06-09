"""
app/tools/retrieval_tool.py — 混合檢索工具 (SQL + Qdrant Native Hybrid Search + Rerank)
實作「帶約束的鏈式檢索 (Chained & Constrained Retrieval)」。
Qdrant Server 端 RRF 融合 → Reranker 重排序 → 回傳最終結果。
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from app.core.config import settings
from app.core.embeddings import get_dense_embedding, get_sparse_embedding
from app.core.vector_db import vector_db
from app.core.database import postgres_db
from app.core.reranker import reranker

logger = logging.getLogger(__name__)


def unified_hybrid_search(
    query: str,
    filter_ids: Optional[str] = None,
    top_k: int = 5,
) -> str:
    """
    帶約束的混合檢索工具（Qdrant 原生 Hybrid Search + Rerank）。

    流程：
    1. 若有 filter_ids（逗號分隔的 ID 字串）→ 限制 Qdrant 搜尋範圍
    2. 產生 Dense + Sparse (BM25) Embeddings
    3. 透過 Qdrant 原生 prefetch + RRF Fusion 完成 Server 端混合搜尋
    4. 從 Postgres 取回最終內容
    5. 透過 Reranker 對結果重排序，使結果更貼近 query 語意

    Args:
        query: 使用者的自然語言查詢
        filter_ids: 可選，由 SQL 預先篩選出的 ID（逗號分隔），例如 "id1,id2,id3"
        top_k: 回傳前 N 筆結果
    """
    try:
        # 解析 filter_ids
        id_list: Optional[List[str]] = None
        if filter_ids:
            id_list = [x.strip() for x in filter_ids.split(",") if x.strip()]
            if len(id_list) == 0:
                id_list = None

        # 產生 Dense + Sparse Embeddings
        dense_vec = get_dense_embedding(query)
        sparse_vec = get_sparse_embedding(query)

        # Qdrant 原生 Hybrid Search（Server 端 RRF 融合）
        # 多取一些候選，交給 Reranker 精排
        retrieve_limit = max(top_k * 3, 20)
        fused = vector_db.hybrid_search(
            query_vector=dense_vec,
            sparse_vector=sparse_vec,
            filter_ids=id_list,
            limit=retrieve_limit,
        )

        top_ids = [doc_id for doc_id, _ in fused]

        if not top_ids:
            return json.dumps(
                {"message": "未找到相關結果", "results": []},
                ensure_ascii=False,
            )

        # 從 Postgres 取回完整內容
        placeholders = ", ".join(["%s"] * len(top_ids))
        sql = f"SELECT * FROM documents WHERE id IN ({placeholders})"
        rows = postgres_db.execute_query(sql, tuple(top_ids))

        # 按 RRF 排序整理
        row_map = {str(r.get("id", "")): r for r in rows}
        ordered = [row_map[pid] for pid in top_ids if pid in row_map]

        # Rerank — 透過 Cross-Encoder 重排序，讓結果更貼近 query
        reranked_pairs = reranker.rerank(
            query=query,
            documents=ordered,
            content_key="content",
        )
        reranked_docs = [doc for doc, _score in reranked_pairs]
        rerank_scores = [
            {"id": str(doc.get("id", "")), "rerank_score": round(score, 6)}
            for doc, score in reranked_pairs
        ]

        return json.dumps(
            {
                "query": query,
                "filter_applied": bool(id_list),
                "fusion_method": "qdrant_native_rrf",
                "reranker": settings.RERANKER_MODEL,
                "rrf_ranking": [
                    {"id": doc_id, "score": round(score, 6)}
                    for doc_id, score in fused[:retrieve_limit]
                ],
                "rerank_ranking": rerank_scores,
                "results": reranked_docs,
            },
            ensure_ascii=False,
            default=str,
        )

    except Exception as exc:
        logger.exception("unified_hybrid_search error")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
