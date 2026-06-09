"""
Agno Tools 單元測試

測試 agno_tools.py 中的 4 個 @tool 函式，驗證它們能正確封裝底層 Adapter 並返回 JSON 格式的結果。
不需要 LLM 連線即可執行。

注意：@tool 裝飾器會將函式轉換為 agno.tools.function.Function 物件，
因此測試時需透過 .entrypoint() 呼叫底層函式。
"""

import json
import os
import sys
import unittest

# 確保可以從專案根目錄匯入 tools 模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.tools.function import Function

from tools.adapters.agno_tools import (
    query_case_system,
    query_crm,
    query_erp,
    resolve_context,
)


class TestAgnoTools(unittest.TestCase):

    def test_tools_are_function_objects(self):
        """所有 tool 應為 agno Function 物件"""
        for t in [resolve_context, query_crm, query_erp, query_case_system]:
            self.assertIsInstance(t, Function)

    def test_resolve_context_returns_valid_json_with_required_keys(self):
        """resolve_context 應返回包含所有必要欄位的 JSON 字串"""
        result = resolve_context.entrypoint(query="幫我看最近 active customer 狀況", user_id="sales_manager_demo")
        data = json.loads(result)

        self.assertIn("query_context", data)
        self.assertIn("domain_context", data)
        self.assertIn("user_context", data)
        self.assertIn("access_context", data)
        self.assertIn("data_sources", data)
        self.assertIn("warnings", data)

    def test_resolve_context_detects_customer_term(self):
        """resolve_context 應正確解析 Customer 名詞"""
        result = resolve_context.entrypoint(query="幫我看最近 active customer 狀況", user_id="sales_manager_demo")
        data = json.loads(result)

        self.assertIn("Customer", data["query_context"]["resolved_terms"])
        self.assertEqual(data["domain_context"]["customer_scope"], "External Customer only")

    def test_resolve_context_finance_warning(self):
        """resolve_context 應在使用者無財務權限時返回 warning"""
        result = resolve_context.entrypoint(query="請分析 active customer 的營收與付款狀況", user_id="sales_manager_demo")
        data = json.loads(result)

        self.assertTrue(any("finance access restricted" in w for w in data["warnings"]))

    def test_query_crm_returns_valid_json(self):
        """query_crm 應返回包含 active_customer_count 的 JSON"""
        result = query_crm.entrypoint(query="幫我看 active customer")
        data = json.loads(result)

        self.assertEqual(data["adapter"], "mock_crm")
        self.assertEqual(data["domain"], "customer")
        self.assertIn("active_customer_count", data["signals"])
        self.assertEqual(data["signals"]["active_customer_count"], 128)

    def test_query_erp_returns_valid_json(self):
        """query_erp 應返回包含 change_pct 的 JSON"""
        result = query_erp.entrypoint(query="查詢業務數據")
        data = json.loads(result)

        self.assertEqual(data["adapter"], "mock_erp")
        self.assertIn("change_pct", data["signals"])
        self.assertEqual(data["signals"]["change_pct"], 7.3)

    def test_query_case_system_returns_valid_json(self):
        """query_case_system 應返回包含 open_case_count 的 JSON"""
        result = query_case_system.entrypoint(query="查詢 open case")
        data = json.loads(result)

        self.assertEqual(data["adapter"], "mock_case")
        self.assertEqual(data["domain"], "case")
        self.assertIn("open_case_count", data["signals"])
        self.assertEqual(data["signals"]["open_case_count"], 23)
        self.assertEqual(data["signals"]["high_priority_open_cases"], 5)

    def test_all_tools_return_strings(self):
        """所有 tool 的 entrypoint 都應返回 str 類型"""
        results = [
            resolve_context.entrypoint(query="test", user_id="sales_manager_demo"),
            query_crm.entrypoint(query="test"),
            query_erp.entrypoint(query="test"),
            query_case_system.entrypoint(query="test"),
        ]
        for r in results:
            self.assertIsInstance(r, str)

    def test_tool_names_are_correct(self):
        """確認 tool 名稱正確"""
        self.assertEqual(resolve_context.name, "resolve_context")
        self.assertEqual(query_crm.name, "query_crm")
        self.assertEqual(query_erp.name, "query_erp")
        self.assertEqual(query_case_system.name, "query_case_system")

    def test_tool_descriptions_exist(self):
        """確認每個 tool 都有 description（供 LLM 選擇工具使用）"""
        for t in [resolve_context, query_crm, query_erp, query_case_system]:
            self.assertIsNotNone(t.description)
            self.assertTrue(len(t.description) > 0)


if __name__ == "__main__":
    unittest.main()
