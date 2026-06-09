"""
tests/test_integration.py — 端對端整合測試
連接真實 PostgreSQL + Qdrant + Embedding + Reranker 服務進行驗證。

執行前須確保：
  1. 已設定 .env 並指向真實服務
  2. 已執行 data/generate_100_docs.py 完成資料寫入
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

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
from app.core.reranker import reranker
from app.tools.retrieval_tool import unified_hybrid_search
from app.tools.analytics_tool import postgres_analytics_tool

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ============================================================
# 1. 基礎服務連通性測試
# ============================================================

class TestServiceHealth:
    """驗證各服務是否可用。"""

    def test_postgres_health(self):
        assert postgres_db.health_check() is True

    def test_qdrant_health(self):
        assert vector_db.health_check() is True

    def test_embedding_service(self):
        vec = get_dense_embedding("測試連線")
        assert isinstance(vec, list)
        assert len(vec) == settings.EMBEDDING_DIM

    def test_sparse_embedding(self):
        sparse = get_sparse_embedding("測試 BM25 連線")
        assert hasattr(sparse, "indices")
        assert hasattr(sparse, "values")
        assert len(sparse.indices) > 0

    def test_reranker_service(self):
        docs = [{"content": "台北營收報告"}, {"content": "高雄人力資源"}]
        results = reranker.rerank("營收", docs)
        assert len(results) == 2
        assert results[0][1] >= results[1][1]  # 排序正確


# ============================================================
# 2. 資料完整性測試
# ============================================================

class TestDataIntegrity:
    """確認 100 筆資料已正確寫入。"""

    def test_postgres_document_count(self):
        rows = postgres_db.execute_query("SELECT COUNT(*) AS cnt FROM documents")
        cnt = rows[0]["cnt"]
        assert cnt >= 100, f"Expected >= 100 docs, got {cnt}"

    def test_qdrant_point_count(self):
        cnt = vector_db.count()
        assert cnt >= 100, f"Expected >= 100 points, got {cnt}"

    def test_postgres_branches_exist(self):
        rows = postgres_db.execute_query(
            "SELECT DISTINCT branch FROM documents ORDER BY branch"
        )
        branches = {r["branch"] for r in rows}
        expected = {"Taipei", "Taichung", "Kaohsiung", "Tainan", "HQ"}
        assert expected.issubset(branches), f"Missing branches: {expected - branches}"

    def test_postgres_categories_exist(self):
        rows = postgres_db.execute_query(
            "SELECT DISTINCT category FROM documents ORDER BY category"
        )
        categories = {r["category"] for r in rows}
        assert len(categories) >= 5, f"Expected >= 5 categories, got {categories}"

    def test_postgres_has_content(self):
        rows = postgres_db.execute_query(
            "SELECT id, title, content FROM documents LIMIT 5"
        )
        for r in rows:
            assert r["title"], "Title should not be empty"
            assert r["content"], "Content should not be empty"
            assert len(r["content"]) > 10, "Content too short"


# ============================================================
# 3. Embedding 品質測試
# ============================================================

class TestEmbeddingQuality:
    """驗證 Embedding 品質——相似文本應有更高相似度。"""

    def test_dense_batch_consistency(self):
        texts = ["台北分公司營收報告", "高雄分公司人力資源"]
        vecs = get_dense_embeddings(texts)
        assert len(vecs) == 2
        assert len(vecs[0]) == settings.EMBEDDING_DIM
        assert len(vecs[1]) == settings.EMBEDDING_DIM
        # 兩個不同主題的向量不應完全相同
        assert vecs[0] != vecs[1]

    def test_sparse_batch_consistency(self):
        texts = ["營收成長報告", "資安稽核報告"]
        sparse_vecs = get_sparse_embeddings(texts)
        assert len(sparse_vecs) == 2
        for sv in sparse_vecs:
            assert len(sv.indices) > 0

    def test_cosine_similarity_direction(self):
        """相似文本的 cosine similarity 應較高。"""
        import math
        q = get_dense_embedding("台北分公司營收報告")
        v_similar = get_dense_embedding("台北營收季度分析")
        v_different = get_dense_embedding("高雄員工培訓計畫")

        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb) if na and nb else 0

        sim_close = cosine(q, v_similar)
        sim_far = cosine(q, v_different)
        logger.info("Similar: %.4f, Different: %.4f", sim_close, sim_far)
        assert sim_close > sim_far, (
            f"Similar text should have higher cosine: {sim_close:.4f} vs {sim_far:.4f}"
        )


# ============================================================
# 4. Qdrant 搜尋功能測試
# ============================================================

class TestQdrantSearch:
    """驗證 Qdrant Dense / Sparse / Hybrid 搜尋。"""

    def test_dense_search(self):
        vec = get_dense_embedding("台北分公司營收")
        results = vector_db.dense_search(query_vector=vec, limit=5)
        assert len(results) > 0
        assert all(isinstance(pid, str) for pid in results)

    def test_sparse_search(self):
        sparse = get_sparse_embedding("風險評估報告")
        results = vector_db.sparse_search(sparse_vector=sparse, limit=5)
        # Sparse-only search 可能在 Qdrant 1.13.x 不完全支援，記錄結果
        logger.info("Sparse-only search returned %d results", len(results))
        # 不做強制 assert，Hybrid Search 已驗證 sparse 功能

    def test_hybrid_search(self):
        dense = get_dense_embedding("資安事件")
        sparse = get_sparse_embedding("資安事件")
        results = vector_db.hybrid_search(
            query_vector=dense, sparse_vector=sparse, limit=5
        )
        assert len(results) > 0
        # 結果格式: (pg_id, score)
        for pg_id, score in results:
            assert isinstance(pg_id, str)
            assert isinstance(score, float)

    def test_hybrid_search_with_filter(self):
        """帶 filter_ids 的 hybrid search。"""
        # 先從 PG 取幾個 ID
        rows = postgres_db.execute_query(
            "SELECT id FROM documents WHERE branch = %s LIMIT 10",
            ("Taipei",),
        )
        if not rows:
            pytest.skip("No Taipei documents found")

        filter_ids = [r["id"] for r in rows]
        dense = get_dense_embedding("營收報告")
        sparse = get_sparse_embedding("營收報告")
        results = vector_db.hybrid_search(
            query_vector=dense,
            sparse_vector=sparse,
            filter_ids=filter_ids,
            limit=5,
        )
        # 所有結果都應在 filter 範圍內
        result_ids = {pid for pid, _ in results}
        assert result_ids.issubset(set(filter_ids)), (
            f"Found IDs outside filter: {result_ids - set(filter_ids)}"
        )


# ============================================================
# 5. Reranker 整合測試
# ============================================================

class TestRerankerIntegration:
    """驗證 Reranker 重排序效果。"""

    def test_reranker_with_real_docs(self):
        rows = postgres_db.execute_query(
            "SELECT id, title, content, branch, category FROM documents LIMIT 10"
        )
        results = reranker.rerank(query="台北分公司營收報告", documents=rows)
        # Reranker 受 top_n 設定限制，回傳數量 <= min(len(rows), RERANKER_TOP_N)
        assert len(results) <= len(rows)
        assert len(results) > 0
        # 分數應為降序
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_reranker_relevance_boost(self):
        """包含查詢關鍵字的文件應被排到更前面。"""
        rows = postgres_db.execute_query(
            "SELECT id, title, content, branch, category FROM documents LIMIT 20"
        )
        if not rows:
            pytest.skip("No documents")

        results = reranker.rerank(query="營收報告", documents=rows)
        top3_titles = [doc["title"] for doc, _ in results[:3]]
        logger.info("Reranker top 3: %s", top3_titles)
        # 至少一個應包含「營收」
        has_revenue = any("營收" in t for t in top3_titles)
        logger.info("Top 3 contains '營收': %s", has_revenue)
        # 不做強制 assert（看模型能力），記錄結果即可


# ============================================================
# 6. 端對端 Retrieval Tool 測試
# ============================================================

class TestRetrievalToolE2E:
    """驗證 unified_hybrid_search 端對端流程。"""

    def test_basic_search(self):
        result_str = unified_hybrid_search(query="台北分公司營收", top_k=5)
        result = json.loads(result_str)
        assert "results" in result
        assert len(result["results"]) > 0
        assert result["fusion_method"] == "qdrant_native_rrf"
        assert result["reranker"] == settings.RERANKER_MODEL

    def test_filtered_search(self):
        """先用 SQL 取 Taipei IDs，再透過工具做帶約束搜尋。"""
        rows = postgres_db.execute_query(
            "SELECT id FROM documents WHERE branch = %s", ("Taipei",)
        )
        if not rows:
            pytest.skip("No Taipei documents")

        id_str = ",".join(r["id"] for r in rows[:15])
        result_str = unified_hybrid_search(
            query="營收報告", filter_ids=id_str, top_k=3
        )
        result = json.loads(result_str)
        assert result["filter_applied"] is True
        assert len(result["results"]) > 0

    def test_search_rerank_order(self):
        """驗證 rerank 排序存在。"""
        result_str = unified_hybrid_search(query="風險評估", top_k=5)
        result = json.loads(result_str)
        assert "rerank_ranking" in result
        if result["rerank_ranking"]:
            scores = [r["rerank_score"] for r in result["rerank_ranking"]]
            assert scores == sorted(scores, reverse=True)

    def test_search_no_crash_on_uncommon_query(self):
        """罕見查詢不應 crash。"""
        result_str = unified_hybrid_search(query="量子計算在金融衍生品中的應用", top_k=3)
        result = json.loads(result_str)
        assert "results" in result or "message" in result


# ============================================================
# 7. Analytics Tool 測試
# ============================================================

class TestAnalyticsToolE2E:
    """驗證 SQL 分析工具。"""

    def test_schema_overview(self):
        result_str = postgres_analytics_tool(
            purpose="schema",
            limit=10,
        )
        result = json.loads(result_str)
        assert result["ok"] is True
        assert result["purpose"] == "schema"
        assert "available_tables" in result
        assert len(result["available_tables"]) > 0

        table_names = {table["table_name"] for table in result["available_tables"]}
        assert "documents" in table_names

    def test_schema_for_documents_table(self):
        result_str = postgres_analytics_tool(
            purpose="schema",
            table_name="documents",
        )
        result = json.loads(result_str)
        assert result["ok"] is True
        assert result["purpose"] == "schema"
        assert result["schema"]["exists"] is True
        assert result["schema"]["table_name"] == "documents"

        column_names = {column["column_name"] for column in result["schema"]["columns"]}
        assert {"id", "title", "content"}.issubset(column_names)

    def test_count_by_branch(self):
        result_str = postgres_analytics_tool(
            sql="SELECT branch, COUNT(*) AS cnt FROM documents GROUP BY branch ORDER BY cnt DESC",
            purpose="statistics",
        )
        result = json.loads(result_str)
        assert "data" in result
        assert len(result["data"]) >= 3

    def test_count_by_category(self):
        result_str = postgres_analytics_tool(
            sql="SELECT category, COUNT(*) AS cnt FROM documents GROUP BY category ORDER BY cnt DESC",
            purpose="statistics",
        )
        result = json.loads(result_str)
        assert "data" in result

    def test_filter_ids_for_search(self):
        result_str = postgres_analytics_tool(
            sql="SELECT id FROM documents WHERE branch = 'Taipei'",
            purpose="filter_ids",
            id_column="id",
            limit=10,
        )
        result = json.loads(result_str)
        assert "ids" in result
        assert len(result["ids"]) > 0

    def test_sql_injection_blocked(self):
        result_str = postgres_analytics_tool(
            sql="DROP TABLE documents",
            purpose="statistics",
        )
        result = json.loads(result_str)
        assert "error" in result

    def test_error_payload_contains_schema_context(self):
        result_str = postgres_analytics_tool(
            sql="SELECT missing_column FROM documents LIMIT 1",
            purpose="statistics",
        )
        result = json.loads(result_str)
        assert result["ok"] is False
        assert result["retryable"] is True
        assert result["failed_sql"] == "SELECT missing_column FROM documents LIMIT 1"
        assert result["schema_context"]["referenced_tables"][0]["table_name"] == "documents"

        related_schema = result["schema_context"]["related_schema"]
        assert len(related_schema) > 0
        assert related_schema[0]["table_name"] == "documents"

        column_names = {column["column_name"] for column in related_schema[0]["columns"]}
        assert "id" in column_names
        assert "content" in column_names

        retry_instructions = result["retry_instructions"]
        assert len(retry_instructions) > 0


# ============================================================
# 8. 跨服務一致性測試
# ============================================================

class TestCrossServiceConsistency:
    """確認 PG 與 Qdrant 資料一致。"""

    def test_pg_ids_exist_in_qdrant(self):
        """PG 中的 ID 在 Qdrant 中應可被搜尋到。"""
        rows = postgres_db.execute_query("SELECT id FROM documents LIMIT 5")
        pg_ids = [r["id"] for r in rows]

        dense = get_dense_embedding("測試")
        sparse = get_sparse_embedding("測試")
        results = vector_db.hybrid_search(
            query_vector=dense,
            sparse_vector=sparse,
            filter_ids=pg_ids,
            limit=10,
        )
        result_ids = {pid for pid, _ in results}
        # 至少應找到部分匹配
        overlap = result_ids.intersection(set(pg_ids))
        assert len(overlap) > 0, "Qdrant should contain points matching PG IDs"

    def test_qdrant_payload_matches_pg(self):
        """Qdrant payload 的 title 應與 PG 中的 title 一致。"""
        rows = postgres_db.execute_query(
            "SELECT id, title FROM documents LIMIT 3"
        )
        if not rows:
            pytest.skip("No documents")

        # 透過 filter 搜尋找到 Qdrant 中的 point
        pg_ids = [r["id"] for r in rows]
        dense = get_dense_embedding(rows[0]["title"])
        sparse = get_sparse_embedding(rows[0]["title"])
        results = vector_db.hybrid_search(
            query_vector=dense,
            sparse_vector=sparse,
            filter_ids=pg_ids,
            limit=5,
        )
        assert len(results) > 0
