"""
tests/test_embeddings.py — Embedding 模組測試
Dense embedding 需要 OPENAI_API_KEY，Sparse embedding 使用本地 fastembed。
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSparseEmbedding:
    """BM25 Sparse Embedding（本地 fastembed，不需 API Key）。"""

    def test_sparse_embedding_returns_sparse_vector(self):
        """get_sparse_embedding 應回傳 SparseVector 結構。"""
        from app.core.embeddings import get_sparse_embedding
        sv = get_sparse_embedding("測試文本")
        assert hasattr(sv, "indices")
        assert hasattr(sv, "values")
        assert len(sv.indices) > 0
        assert len(sv.indices) == len(sv.values)

    def test_sparse_embeddings_batch(self):
        """批次 sparse embedding 應回傳正確數量。"""
        from app.core.embeddings import get_sparse_embeddings
        results = get_sparse_embeddings(["文本一", "文本二", "文本三"])
        assert len(results) == 3
        for sv in results:
            assert len(sv.indices) > 0

    def test_sparse_embedding_different_texts(self):
        """不同文本應產生不同的 sparse vector。"""
        from app.core.embeddings import get_sparse_embedding
        sv1 = get_sparse_embedding("台北分公司營收報告")
        sv2 = get_sparse_embedding("高雄人員配置分析")
        # 不同文本至少有部分不同的 indices
        assert set(sv1.indices) != set(sv2.indices) or sv1.values != sv2.values


class TestDenseEmbeddingMocked:
    """Dense Embedding Mock 測試（不呼叫 OpenAI API）。"""

    @patch("app.core.embeddings._get_openai")
    def test_get_dense_embedding_shape(self, mock_openai):
        """應回傳正確維度的向量。"""
        fake_embedding = [0.1] * 1024
        mock_resp = MagicMock()
        mock_resp.data = [MagicMock(embedding=fake_embedding)]
        mock_openai.return_value.embeddings.create.return_value = mock_resp

        from app.core.embeddings import get_dense_embedding
        result = get_dense_embedding("test")
        assert len(result) == 1024

    @patch("app.core.embeddings._get_openai")
    def test_get_dense_embeddings_batch(self, mock_openai):
        """批次呼叫應回傳相同數量的向量。"""
        fake = [MagicMock(embedding=[0.1] * 1024) for _ in range(3)]
        mock_resp = MagicMock()
        mock_resp.data = fake
        mock_openai.return_value.embeddings.create.return_value = mock_resp

        from app.core.embeddings import get_dense_embeddings
        result = get_dense_embeddings(["a", "b", "c"])
        assert len(result) == 3
