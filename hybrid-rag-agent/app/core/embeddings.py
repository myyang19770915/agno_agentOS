"""
app/core/embeddings.py — Embedding 產生器
同時支援 Dense（OpenAI-compatible，如 BAAI/bge-m3 via vLLM）與 Sparse（fastembed BM25）。
"""
from __future__ import annotations

import logging
from typing import List

from openai import OpenAI
from qdrant_client.models import SparseVector

from app.core.config import settings

logger = logging.getLogger(__name__)

_openai_client: OpenAI | None = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL,
        )
    return _openai_client


# ---- Dense Embedding (OpenAI) ----
def get_dense_embedding(text: str) -> List[float]:
    """取得 OpenAI dense embedding。"""
    resp = _get_openai().embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
    )
    return resp.data[0].embedding


def get_dense_embeddings(texts: List[str]) -> List[List[float]]:
    """批次取得 dense embeddings。"""
    resp = _get_openai().embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts,
    )
    return [d.embedding for d in resp.data]


# ---- Sparse Embedding (fastembed BM25) ----
_sparse_model = None


def _get_sparse_model():
    global _sparse_model
    if _sparse_model is None:
        from fastembed import SparseTextEmbedding
        _sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
    return _sparse_model


def get_sparse_embedding(text: str) -> SparseVector:
    """取得 BM25 sparse embedding（fastembed）。"""
    model = _get_sparse_model()
    results = list(model.embed([text]))
    sparse = results[0]
    return SparseVector(
        indices=sparse.indices.tolist(),
        values=sparse.values.tolist(),
    )


def get_sparse_embeddings(texts: List[str]) -> List[SparseVector]:
    """批次取得 sparse embeddings。"""
    model = _get_sparse_model()
    results = list(model.embed(texts))
    return [
        SparseVector(indices=s.indices.tolist(), values=s.values.tolist())
        for s in results
    ]
