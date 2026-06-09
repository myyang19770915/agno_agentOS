import json
import unittest

from tools.context_pipeline import run_query_pipeline
from tools.context_resolver import resolve_context_package


class ContextResolverTests(unittest.TestCase):
    def test_resolves_customer_active_context_for_sales_manager(self):
        package = resolve_context_package(
            query="幫我看最近 active customer 狀況",
            user_id="sales_manager_demo",
        )

        self.assertEqual(package["query_context"]["intent"], "analysis")
        self.assertIn("Customer", package["query_context"]["resolved_terms"])
        self.assertEqual(package["domain_context"]["customer_scope"], "External Customer only")
        self.assertEqual(
            package["domain_context"]["active_rule"],
            "最近 180 天內，至少有一項有效商務或服務互動紀錄",
        )
        self.assertEqual(package["user_context"]["department"], "業務")
        self.assertEqual(package["user_context"]["role"], "Sales Manager")
        self.assertIn("CRM", package["data_sources"])
        self.assertIn("ERP", package["data_sources"])

    def test_finance_query_adds_access_warning_when_user_lacks_finance_access(self):
        package = resolve_context_package(
            query="請分析 active customer 的營收與付款狀況",
            user_id="sales_manager_demo",
        )

        warnings = "\n".join(package["warnings"])
        self.assertIn("finance access restricted", warnings)

    def test_package_is_json_serializable(self):
        package = resolve_context_package(
            query="幫我看最近 active customer 狀況",
            user_id="sales_manager_demo",
        )
        serialized = json.dumps(package, ensure_ascii=False)
        self.assertIn("query_context", serialized)

    def test_end_to_end_pipeline_returns_context_data_and_answer_draft(self):
        payload = run_query_pipeline(
            query="幫我看最近 active customer 狀況",
            user_id="sales_manager_demo",
        )

        self.assertIn("context_package", payload)
        self.assertIn("data_result", payload)
        self.assertIn("answer_draft", payload)
        self.assertEqual(payload["data_result"]["metric_name"], "active_customer_status")
        self.assertIn("目前 active customer", payload["answer_draft"]["summary"])

    def test_pipeline_builds_llm_prompt(self):
        payload = run_query_pipeline(
            query="幫我看最近 active customer 狀況",
            user_id="sales_manager_demo",
        )
        prompt = payload["llm_prompt"]
        self.assertIn("幫我看最近 active customer 狀況", prompt)
        self.assertIn("最近 180 天內，至少有一項有效商務或服務互動紀錄", prompt)
        self.assertIn("128", prompt)
        self.assertIn("summary_first", prompt)

    def test_pipeline_reports_adapter_provenance(self):
        payload = run_query_pipeline(
            query="幫我看最近 active customer 狀況",
            user_id="sales_manager_demo",
        )
        provenance = payload["data_result"]["provenance"]
        adapter_names = [item["adapter"] for item in provenance]
        self.assertIn("mock_crm", adapter_names)
        self.assertIn("mock_erp", adapter_names)

    def test_customer_case_query_resolves_both_domains(self):
        payload = run_query_pipeline(
            query="請分析 active customer 的 open case 狀況",
            user_id="sales_manager_demo",
        )
        resolved_terms = payload["context_package"]["query_context"]["resolved_terms"]
        self.assertIn("Customer", resolved_terms)
        self.assertIn("Case", resolved_terms)
        self.assertEqual(payload["data_result"]["metric_name"], "customer_case_status")
        self.assertIn("case_scope", payload["context_package"]["domain_context"])
        self.assertIn("cross_domain_notes", payload["context_package"]["domain_context"])
        adapter_names = [item["adapter"] for item in payload["data_result"]["provenance"]]
        self.assertIn("mock_case", adapter_names)
        self.assertIn("open case", payload["llm_prompt"].lower())


if __name__ == "__main__":
    unittest.main()
