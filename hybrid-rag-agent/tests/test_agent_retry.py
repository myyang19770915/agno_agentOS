"""
tests/test_agent_retry.py — 驗證 agent 在收到 retryable SQL 錯誤後會重新產生 SQL 並重試。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Iterator
from unittest.mock import patch

from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse

from app.agents.router_agent import build_router_agent
from app.tools.analytics_tool import postgres_analytics_tool


@dataclass
class FakeRetryModel(Model):
    """用可控的 tool call 序列模擬 agent 根據錯誤 payload 重試 SQL。"""

    id: str = "fake-retry-model"
    name: str = "FakeRetryModel"
    provider: str = "test"
    call_count: int = 0
    seen_retry_payload: bool = False

    def invoke(self, *args, **kwargs) -> ModelResponse:
        messages: list[Message] = kwargs["messages"]
        self.call_count += 1

        if self.call_count == 1:
            return ModelResponse(
                role="assistant",
                tool_calls=[
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "postgres_analytics_tool",
                            "arguments": json.dumps(
                                {
                                    "sql": "SELECT missing_column FROM documents LIMIT 1",
                                    "purpose": "statistics",
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            )

        if self.call_count == 2:
            tool_messages = [message for message in messages if message.role == "tool"]
            assert tool_messages, "Agent 應先收到第一次 tool 執行結果"

            retry_payload = json.loads(tool_messages[-1].get_content_string())
            assert retry_payload["ok"] is False
            assert retry_payload["retryable"] is True
            assert retry_payload["failed_sql"] == "SELECT missing_column FROM documents LIMIT 1"
            self.seen_retry_payload = True

            return ModelResponse(
                role="assistant",
                tool_calls=[
                    {
                        "id": "call-2",
                        "type": "function",
                        "function": {
                            "name": "postgres_analytics_tool",
                            "arguments": json.dumps(
                                {
                                    "sql": "SELECT branch, COUNT(*) AS cnt FROM documents GROUP BY branch ORDER BY cnt DESC",
                                    "purpose": "statistics",
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            )

        assert self.seen_retry_payload is True
        return ModelResponse(
            role="assistant",
            content="已根據錯誤回饋修正 SQL，成功取得 documents 的 branch 統計結果。",
        )

    async def ainvoke(self, *args, **kwargs) -> ModelResponse:
        return self.invoke(*args, **kwargs)

    def invoke_stream(self, *args, **kwargs) -> Iterator[ModelResponse]:
        yield self.invoke(*args, **kwargs)

    async def ainvoke_stream(self, *args, **kwargs) -> AsyncIterator[ModelResponse]:
        yield self.invoke(*args, **kwargs)

    def _parse_provider_response(self, response: Any, **kwargs) -> ModelResponse:
        return response

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        return response


class TestAgentSqlRetry:
    def test_agent_retries_after_retryable_sql_error(self):
        fake_model = FakeRetryModel()
        agent = build_router_agent(
            model=fake_model,
            tools=[postgres_analytics_tool],
            debug_mode=False,
        )

        executed_sql: list[str] = []

        def fake_execute_query(sql: str, params=None):
            executed_sql.append(sql)
            if sql == "SELECT missing_column FROM documents LIMIT 1":
                raise Exception("column missing_column does not exist")
            if sql == "SELECT branch, COUNT(*) AS cnt FROM documents GROUP BY branch ORDER BY cnt DESC":
                return [{"branch": "Taipei", "cnt": 3}, {"branch": "HQ", "cnt": 2}]
            raise AssertionError(f"Unexpected SQL: {sql}")

        with patch("app.tools.analytics_tool.postgres_db.execute_query", side_effect=fake_execute_query), patch(
            "app.tools.analytics_tool.postgres_db.describe_table"
        ) as mock_describe_table:
            mock_describe_table.return_value = {
                "exists": True,
                "schema": "public",
                "table_name": "documents",
                "columns": [
                    {"column_name": "id", "data_type": "text", "is_nullable": "NO", "is_primary_key": True},
                    {"column_name": "branch", "data_type": "text", "is_nullable": "YES", "is_primary_key": False},
                    {"column_name": "content", "data_type": "text", "is_nullable": "NO", "is_primary_key": False},
                ],
                "foreign_keys": [],
            }

            result = agent.run("請統計各 branch 的文件數量")

        assert fake_model.call_count == 3
        assert fake_model.seen_retry_payload is True
        assert executed_sql == [
            "SELECT missing_column FROM documents LIMIT 1",
            "SELECT branch, COUNT(*) AS cnt FROM documents GROUP BY branch ORDER BY cnt DESC",
        ]
        assert "修正 SQL" in result.content