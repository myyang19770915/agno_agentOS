"""
tests/test_reranker.py — Reranker 單元測試
使用 mock 測試，不需真實 vLLM Reranker 服務。
"""
import pytest
from unittest.mock import patch, MagicMock

from app.core.reranker import Reranker


class TestRerankerRerank:
    """Reranker.rerank() 核心邏輯測試。"""

    @patch("app.core.reranker.requests.post")
    def test_rerank_basic(self, mock_post):
        """基本 rerank：應按分數降序排列。"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"index": 0, "score": 0.3},
                {"index": 1, "score": 0.9},
                {"index": 2, "score": 0.6},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        rr = Reranker(base_url="http://fake:30807", top_n=10)
        docs = [
            {"id": "a", "content": "文件 A"},
            {"id": "b", "content": "文件 B"},
            {"id": "c", "content": "文件 C"},
        ]

        results = rr.rerank("測試查詢", docs)

        # 應按分數降序：b(0.9) > c(0.6) > a(0.3)
        assert len(results) == 3
        assert results[0][0]["id"] == "b"
        assert results[0][1] == 0.9
        assert results[1][0]["id"] == "c"
        assert results[2][0]["id"] == "a"

    @patch("app.core.reranker.requests.post")
    def test_rerank_top_n(self, mock_post):
        """top_n 應限制回傳數量。"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {"index": 0, "score": 0.1},
                {"index": 1, "score": 0.9},
                {"index": 2, "score": 0.5},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        rr = Reranker(base_url="http://fake:30807", top_n=2)
        docs = [
            {"id": "a", "content": "A"},
            {"id": "b", "content": "B"},
            {"id": "c", "content": "C"},
        ]

        results = rr.rerank("query", docs)
        assert len(results) == 2
        assert results[0][0]["id"] == "b"

    def test_rerank_empty_documents(self):
        """空文件列表應回傳空列表。"""
        rr = Reranker(base_url="http://fake:30807")
        results = rr.rerank("query", [])
        assert results == []

    @patch("app.core.reranker.requests.post")
    def test_rerank_api_failure_returns_original_order(self, mock_post):
        """API 失敗時應保持原始順序。"""
        import requests as req
        mock_post.side_effect = req.exceptions.ConnectionError("connection refused")

        rr = Reranker(base_url="http://fake:30807", top_n=10)
        docs = [
            {"id": "a", "content": "A"},
            {"id": "b", "content": "B"},
        ]

        results = rr.rerank("query", docs)
        assert len(results) == 2
        # 保持原始順序
        assert results[0][0]["id"] == "a"
        assert results[1][0]["id"] == "b"
        # 分數為 0.0
        assert results[0][1] == 0.0

    @patch("app.core.reranker.requests.post")
    def test_rerank_score_count_mismatch(self, mock_post):
        """API 回傳的 score 數量不匹配時，應保持原始順序。"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {"index": 0, "score": 0.5},
                # 缺少 index=1
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        rr = Reranker(base_url="http://fake:30807", top_n=10)
        docs = [
            {"id": "a", "content": "A"},
            {"id": "b", "content": "B"},
        ]

        results = rr.rerank("query", docs)
        assert len(results) == 2
        assert results[0][0]["id"] == "a"

    @patch("app.core.reranker.requests.post")
    def test_rerank_sends_correct_payload(self, mock_post):
        """應發送正確的 payload 到 vLLM API。"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [{"index": 0, "score": 0.5}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        rr = Reranker(
            base_url="http://test:30807",
            model_name="test-model",
            top_n=5,
        )
        docs = [{"id": "x", "content": "test content"}]

        rr.rerank("my query", docs)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["model"] == "test-model"
        assert payload["text_1"] == ["my query"]
        assert payload["text_2"] == ["test content"]
        assert call_kwargs.kwargs["timeout"] == 30
        assert "http://test:30807/score" in call_kwargs.args[0]

    @patch("app.core.reranker.requests.post")
    def test_rerank_custom_content_key(self, mock_post):
        """應支援自訂 content_key。"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [{"index": 0, "score": 0.8}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        rr = Reranker(base_url="http://fake:30807", top_n=5)
        docs = [{"id": "1", "body": "自訂欄位內容"}]

        results = rr.rerank("query", docs, content_key="body")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["text_2"] == ["自訂欄位內容"]
        assert len(results) == 1
