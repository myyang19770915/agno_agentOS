"""
tests/test_rrf.py — RRF 演算法單元測試
不依賴外部服務，可獨立執行。
"""
import pytest
from app.core.rrf import reciprocal_rank_fusion


class TestReciprocalRankFusion:
    """RRF 核心演算法測試。"""

    def test_single_result_list(self):
        """單一結果列表應回傳正確分數。"""
        results = reciprocal_rank_fusion([["a", "b", "c"]], k=60)
        ids = [doc_id for doc_id, _ in results]
        assert ids == ["a", "b", "c"]
        # a 的分數 = 1/(60+1) = 0.01639...
        assert results[0][1] == pytest.approx(1 / 61, rel=1e-6)

    def test_two_lists_overlap(self):
        """兩個列表中共有的 ID 應獲得更高分數。"""
        list1 = ["a", "b", "c"]
        list2 = ["b", "d", "a"]
        results = reciprocal_rank_fusion([list1, list2], k=60)
        scores = dict(results)
        # b 出現在兩個列表的 rank 2 和 rank 1
        # a 出現在兩個列表的 rank 1 和 rank 3
        assert scores["b"] > scores["c"]  # b 在兩方都出現
        assert scores["a"] > scores["d"]  # a 在兩方都出現

    def test_empty_input(self):
        """空輸入應回傳空列表。"""
        assert reciprocal_rank_fusion([]) == []

    def test_empty_sublists(self):
        """空子列表應正常處理。"""
        results = reciprocal_rank_fusion([[], ["a"]])
        assert len(results) == 1
        assert results[0][0] == "a"

    def test_no_overlap(self):
        """完全不重疊時，每個 ID 只有一個來源的分數。"""
        list1 = ["a", "b"]
        list2 = ["c", "d"]
        results = reciprocal_rank_fusion([list1, list2], k=60)
        scores = dict(results)
        assert scores["a"] == scores["c"]  # 都是 rank 1
        assert scores["b"] == scores["d"]  # 都是 rank 2

    def test_three_lists(self):
        """三路融合應正確計算。"""
        results = reciprocal_rank_fusion(
            [["a", "b"], ["b", "c"], ["c", "a"]], k=60
        )
        scores = dict(results)
        # 每個 ID 出現兩次
        assert len(results) == 3
        # a: rank1 + rank2/list3 = 1/61 + 1/62
        # b: rank2 + rank1/list2 = 1/62 + 1/61
        # 因此 a == b
        assert scores["a"] == pytest.approx(scores["b"], rel=1e-6)

    def test_k_parameter_effect(self):
        """較大的 k 會壓縮分數差異。"""
        results_k10 = reciprocal_rank_fusion([["a", "b"]], k=10)
        results_k1000 = reciprocal_rank_fusion([["a", "b"]], k=1000)

        diff_k10 = results_k10[0][1] - results_k10[1][1]
        diff_k1000 = results_k1000[0][1] - results_k1000[1][1]
        assert diff_k10 > diff_k1000  # k 小 → 差異大

    def test_large_input(self):
        """大規模輸入效能測試。"""
        ids = [str(i) for i in range(1000)]
        results = reciprocal_rank_fusion([ids, list(reversed(ids))], k=60)
        assert len(results) == 1000

    def test_duplicate_ids_in_single_list(self):
        """同一列表中的重複 ID 會累加分數。"""
        results = reciprocal_rank_fusion([["a", "a", "b"]])
        scores = dict(results)
        # a 出現在 rank 1 和 rank 2
        expected_a = 1 / 61 + 1 / 62
        assert scores["a"] == pytest.approx(expected_a, rel=1e-6)


class TestRRFEdgeCases:
    """RRF 邊緣案例。"""

    def test_single_item_list(self):
        results = reciprocal_rank_fusion([["only_one"]])
        assert len(results) == 1
        assert results[0][0] == "only_one"

    def test_preserves_all_ids(self):
        """確保所有 ID 都被保留。"""
        list1 = ["a", "b", "c"]
        list2 = ["d", "e", "f"]
        results = reciprocal_rank_fusion([list1, list2])
        result_ids = {doc_id for doc_id, _ in results}
        assert result_ids == {"a", "b", "c", "d", "e", "f"}
