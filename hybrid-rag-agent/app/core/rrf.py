"""
app/core/rrf.py — Reciprocal Rank Fusion 演算法
將多路檢索結果融合為單一排序列表。
"""
from __future__ import annotations

from typing import List, Tuple, Dict


def reciprocal_rank_fusion(
    results_list: List[List[str]],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """
    Reciprocal Rank Fusion (RRF)。

    Args:
        results_list: 多組已排序的 doc_id 列表，例如
                      [[id_a, id_b], [id_b, id_c]]
        k: 平滑常數（預設 60，原始論文建議值）

    Returns:
        按 RRF 分數降序排列的 (doc_id, score) 列表
    """
    if not results_list:
        return []

    scores: Dict[str, float] = {}
    for results in results_list:
        for rank, doc_id in enumerate(results, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
