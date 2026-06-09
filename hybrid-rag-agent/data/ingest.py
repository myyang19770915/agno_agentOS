"""
data/ingest.py — 資料清洗與 Ingestion 腳本
將結構化資料同時寫入 PostgreSQL 與 Qdrant（含 Dense + Sparse Embedding）。
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List

from qdrant_client.models import PointStruct

# 確保可以 import app 套件
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.database import postgres_db
from app.core.vector_db import vector_db
from app.core.embeddings import (
    get_dense_embedding,
    get_dense_embeddings,
    get_sparse_embedding,
    get_sparse_embeddings,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---- 範例文件 ----
SAMPLE_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "title": "台北分公司 Q1 營收報告",
        "content": "台北分公司 2026 年第一季營收為 NT$12,500,000，較去年同期成長 15%。主要貢獻來自企業客戶的大型專案。",
        "branch": "Taipei",
        "category": "finance",
        "date": "2026-03-15",
    },
    {
        "title": "台中分公司合約風險評估",
        "content": "台中分公司目前有 3 份合約存在違約風險，主要原因為供應商交期延遲。建議啟動備用供應商計畫。",
        "branch": "Taichung",
        "category": "risk",
        "date": "2026-03-10",
    },
    {
        "title": "高雄分公司人員配置分析",
        "content": "高雄分公司目前共有 45 名員工，其中技術部門佔 60%。預計 Q2 將新增 10 名工程師以支援 AI 專案。",
        "branch": "Kaohsiung",
        "category": "hr",
        "date": "2026-03-01",
    },
    {
        "title": "全公司 AI 導入策略",
        "content": "公司計畫在 2026 年底前完成 RAG (Retrieval-Augmented Generation) 系統部署，涵蓋知識庫管理、客服自動化、與內部文件搜尋三大場景。",
        "branch": "HQ",
        "category": "strategy",
        "date": "2026-02-20",
    },
    {
        "title": "台北分公司合約審查報告",
        "content": "台北分公司 2026 年 Q1 共審查 28 份合約，其中 5 份需修訂條款，2 份存在潛在法律風險，已移交法務部門處理。",
        "branch": "Taipei",
        "category": "risk",
        "date": "2026-03-20",
    },
    {
        "title": "台中分公司 Q1 營收報告",
        "content": "台中分公司 2026 年第一季營收為 NT$8,200,000，較去年同期下降 5%。主要受到原物料成本上漲影響。",
        "branch": "Taichung",
        "category": "finance",
        "date": "2026-03-15",
    },
    {
        "title": "資安政策更新通知",
        "content": "即日起全公司啟用零信任架構 (Zero Trust Architecture)，所有內部系統需透過 MFA 認證。VPN 將於 Q2 全面升級為 ZTNA。",
        "branch": "HQ",
        "category": "security",
        "date": "2026-03-25",
    },
    {
        "title": "客服自動化進度報告",
        "content": "客服 AI 機器人已完成第一階段部署，目前可處理 FAQ 類問題，準確率達 87%。第二階段將整合工單系統與 RAG 知識庫。",
        "branch": "HQ",
        "category": "strategy",
        "date": "2026-03-22",
    },
]


def init_postgres_table() -> None:
    """建立 documents 表（如不存在）。"""
    postgres_db.execute_write("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            branch TEXT,
            category TEXT,
            date TEXT
        )
    """)
    logger.info("PostgreSQL table 'documents' ensured.")


def ingest_documents(docs: List[Dict[str, Any]]) -> int:
    """將文件同時寫入 Postgres 與 Qdrant。"""
    # 確保 Collection 與 Table 存在
    vector_db.ensure_collection()
    init_postgres_table()

    texts = [d["content"] for d in docs]
    titles = [d["title"] for d in docs]

    # 批次產生 embeddings
    logger.info("Generating dense embeddings for %d documents...", len(docs))
    dense_vecs = get_dense_embeddings(texts)

    logger.info("Generating sparse embeddings for %d documents...", len(docs))
    sparse_vecs = get_sparse_embeddings(texts)

    points: List[PointStruct] = []
    count = 0

    for i, doc in enumerate(docs):
        doc_id = doc.get("id") or str(uuid.uuid4())

        # 寫入 Postgres
        postgres_db.execute_write(
            """
            INSERT INTO documents (id, title, content, branch, category, date)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                branch = EXCLUDED.branch,
                category = EXCLUDED.category,
                date = EXCLUDED.date
            """,
            (doc_id, doc["title"], doc["content"], doc.get("branch"), doc.get("category"), doc.get("date")),
        )

        # 準備 Qdrant Point（Named Vectors: dense + sparse）
        from qdrant_client.models import SparseVector as SparseVectorModel
        sparse = sparse_vecs[i]
        points.append(
            PointStruct(
                id=i,  # Qdrant 用整數 ID
                vector={
                    "dense": dense_vecs[i],
                    "sparse": SparseVectorModel(
                        indices=sparse.indices.tolist() if hasattr(sparse.indices, "tolist") else list(sparse.indices),
                        values=sparse.values.tolist() if hasattr(sparse.values, "tolist") else list(sparse.values),
                    ),
                },
                payload={
                    "pg_id": doc_id,
                    "title": doc["title"],
                    "branch": doc.get("branch", ""),
                    "category": doc.get("category", ""),
                    "text": doc["content"][:500],  # 部分文本供預覽
                },
            )
        )
        count += 1

    vector_db.upsert_points(points)
    logger.info("Ingested %d documents into Postgres + Qdrant.", count)
    return count


def main():
    """執行範例資料 Ingestion。"""
    logger.info("=== Starting Data Ingestion ===")
    count = ingest_documents(SAMPLE_DOCUMENTS)
    logger.info("=== Done: %d documents ingested ===", count)

    # 驗證
    pg_rows = postgres_db.execute_query("SELECT COUNT(*) AS cnt FROM documents")
    qd_count = vector_db.count()
    logger.info("Postgres: %s rows | Qdrant: %d points", pg_rows[0]["cnt"], qd_count)


if __name__ == "__main__":
    main()
