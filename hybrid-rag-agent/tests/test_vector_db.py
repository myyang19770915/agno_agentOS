"""
tests/test_vector_db.py — Qdrant VectorDB 單元測試
使用 mock 測試，不需真實 Qdrant 連線。
測試 Qdrant 原生 Hybrid Search (prefetch + RRF Fusion) 模式。
"""
import pytest
from unittest.mock import patch, MagicMock, call
from qdrant_client import models
from qdrant_client.models import Filter, FieldCondition, MatchAny

from app.core.vector_db import VectorDB


class TestVectorDBFilter:
    """Filter 構建邏輯測試。"""

    def test_build_filter_none(self):
        """filter_ids 為 None 時應回傳 None。"""
        assert VectorDB._build_filter(None) is None

    def test_build_filter_empty_list(self):
        """空列表應回傳 None。"""
        assert VectorDB._build_filter([]) is None

    def test_build_filter_with_ids(self):
        """有 ID 時應建立正確的 Filter。"""
        f = VectorDB._build_filter(["id1", "id2", "id3"])
        assert f is not None
        assert len(f.must) == 1
        condition = f.must[0]
        assert condition.key == "pg_id"
        assert set(condition.match.any) == {"id1", "id2", "id3"}

    def test_build_filter_single_id(self):
        """單一 ID 也應正確處理。"""
        f = VectorDB._build_filter(["only_one"])
        assert f is not None
        assert f.must[0].match.any == ["only_one"]


class TestVectorDBHealth:
    """VectorDB 健康檢查測試。"""

    def test_health_check_returns_false_on_error(self):
        """連線失敗時應回傳 False。"""
        vdb = VectorDB(host="nonexistent", port=9999)
        assert vdb.health_check() is False


class TestVectorDBNamedVectors:
    """Named Vectors 常數測試。"""

    def test_named_vector_constants(self):
        """確認 Named Vector 名稱正確。"""
        assert VectorDB.DENSE_VECTOR_NAME == "dense"
        assert VectorDB.SPARSE_VECTOR_NAME == "sparse"


class TestVectorDBHybridSearch:
    """Qdrant 原生 Hybrid Search (prefetch + RRF Fusion) 測試。"""

    @patch("app.core.vector_db.QdrantClient")
    def test_hybrid_search_calls_query_points(self, MockClient):
        """hybrid_search 應使用 query_points + prefetch + FusionQuery。"""
        mock_client = MockClient.return_value

        # Mock query_points 回傳
        mock_point_1 = MagicMock()
        mock_point_1.payload = {"pg_id": "doc_a"}
        mock_point_1.score = 0.95
        mock_point_1.id = 1

        mock_point_2 = MagicMock()
        mock_point_2.payload = {"pg_id": "doc_b"}
        mock_point_2.score = 0.88
        mock_point_2.id = 2

        mock_response = MagicMock()
        mock_response.points = [mock_point_1, mock_point_2]
        mock_client.query_points.return_value = mock_response

        vdb = VectorDB(host="localhost", port=6333)
        dense_vec = [0.1] * 1024
        sparse_vec = models.SparseVector(indices=[1, 5, 100], values=[0.5, 0.3, 0.7])

        results = vdb.hybrid_search(dense_vec, sparse_vec, limit=5)

        # 驗證回傳格式
        assert len(results) == 2
        assert results[0] == ("doc_a", 0.95)
        assert results[1] == ("doc_b", 0.88)

        # 驗證 query_points 呼叫參數
        mock_client.query_points.assert_called_once()
        call_kwargs = mock_client.query_points.call_args
        assert call_kwargs.kwargs["limit"] == 5
        assert call_kwargs.kwargs["with_payload"] is True

        # 驗證 prefetch 包含 dense + sparse 子查詢
        prefetch = call_kwargs.kwargs["prefetch"]
        assert len(prefetch) == 2
        assert prefetch[0].using == "dense"
        assert prefetch[1].using == "sparse"

        # 驗證主查詢是 FusionQuery(RRF)
        query = call_kwargs.kwargs["query"]
        assert isinstance(query, models.FusionQuery)
        assert query.fusion == models.Fusion.RRF

    @patch("app.core.vector_db.QdrantClient")
    def test_hybrid_search_with_filter(self, MockClient):
        """帶 filter_ids 時，prefetch 子查詢也應附帶 filter。"""
        mock_client = MockClient.return_value
        mock_response = MagicMock()
        mock_response.points = []
        mock_client.query_points.return_value = mock_response

        vdb = VectorDB(host="localhost", port=6333)
        dense_vec = [0.1] * 1024
        sparse_vec = models.SparseVector(indices=[1], values=[0.5])

        vdb.hybrid_search(dense_vec, sparse_vec, filter_ids=["id1", "id2"], limit=10)

        call_kwargs = mock_client.query_points.call_args
        prefetch = call_kwargs.kwargs["prefetch"]

        # 兩個 prefetch 都應有 filter
        for pf in prefetch:
            assert pf.filter is not None
            assert len(pf.filter.must) == 1
            assert pf.filter.must[0].key == "pg_id"
            assert set(pf.filter.must[0].match.any) == {"id1", "id2"}

    @patch("app.core.vector_db.QdrantClient")
    def test_hybrid_search_empty_result(self, MockClient):
        """無結果時應回傳空列表。"""
        mock_client = MockClient.return_value
        mock_response = MagicMock()
        mock_response.points = []
        mock_client.query_points.return_value = mock_response

        vdb = VectorDB(host="localhost", port=6333)
        results = vdb.hybrid_search([0.1] * 1024, models.SparseVector(indices=[1], values=[0.5]))
        assert results == []

    @patch("app.core.vector_db.QdrantClient")
    def test_hybrid_search_fallback_id(self, MockClient):
        """payload 沒有 pg_id 時，應 fallback 到 point.id。"""
        mock_client = MockClient.return_value

        mock_point = MagicMock()
        mock_point.payload = {}
        mock_point.score = 0.5
        mock_point.id = 42

        mock_response = MagicMock()
        mock_response.points = [mock_point]
        mock_client.query_points.return_value = mock_response

        vdb = VectorDB(host="localhost", port=6333)
        results = vdb.hybrid_search([0.1] * 1024, models.SparseVector(indices=[1], values=[0.5]))
        assert results[0] == ("42", 0.5)


class TestVectorDBDeleteByPgIds:
    """delete_by_pg_ids 刪除功能測試。"""

    @patch("app.core.vector_db.QdrantClient")
    def test_delete_by_pg_ids_calls_client_delete(self, MockClient):
        """應使用 Filter 呼叫 client.delete。"""
        mock_client = MockClient.return_value
        vdb = VectorDB(host="localhost", port=6333)

        result = vdb.delete_by_pg_ids(["doc_1", "doc_2", "doc_3"])

        assert result == 3
        mock_client.delete.assert_called_once()
        call_kwargs = mock_client.delete.call_args
        assert call_kwargs.kwargs["collection_name"] == vdb._collection
        assert call_kwargs.kwargs["wait"] is True

        # 驗證 filter 正確
        selector = call_kwargs.kwargs["points_selector"]
        assert isinstance(selector, Filter)
        assert len(selector.must) == 1
        assert selector.must[0].key == "pg_id"
        assert set(selector.must[0].match.any) == {"doc_1", "doc_2", "doc_3"}

    @patch("app.core.vector_db.QdrantClient")
    def test_delete_by_pg_ids_single_id(self, MockClient):
        """單一 pg_id 刪除也應正確運作。"""
        mock_client = MockClient.return_value
        vdb = VectorDB(host="localhost", port=6333)

        result = vdb.delete_by_pg_ids(["only_one"])

        assert result == 1
        mock_client.delete.assert_called_once()
        selector = mock_client.delete.call_args.kwargs["points_selector"]
        assert selector.must[0].match.any == ["only_one"]

    @patch("app.core.vector_db.QdrantClient")
    def test_delete_by_pg_ids_empty_list(self, MockClient):
        """空列表時不呼叫 client.delete，回傳 0。"""
        mock_client = MockClient.return_value
        vdb = VectorDB(host="localhost", port=6333)

        result = vdb.delete_by_pg_ids([])

        assert result == 0
        mock_client.delete.assert_not_called()

    @patch("app.core.vector_db.QdrantClient")
    def test_delete_by_pg_ids_idempotent(self, MockClient):
        """即使重複刪除同一組 ID 也不應報錯（冪等性）。"""
        mock_client = MockClient.return_value
        vdb = VectorDB(host="localhost", port=6333)

        # 連續刪除兩次
        vdb.delete_by_pg_ids(["doc_x"])
        vdb.delete_by_pg_ids(["doc_x"])

        assert mock_client.delete.call_count == 2
