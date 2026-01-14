# GitHub Issue: RemoteAgent cannot be used as Team member

> [!TIP]
> ## ✅ 已解決 - Resolved in agno 2.3.26
> 
> **更新日期**: 2026-01-14
> 
> 此問題已在 **agno 2.3.26** 版本中修復！現在可以正常使用 `RemoteAgent` 作為 `Team` 成員。
> 
> **驗證結果**: Creative Team 成功運行，RemoteAgent (image-generator) 可以與本地 Agent 協作。

# https://github.com/agno-agi/agno/pull/5987/files#diff-12440e8eb86e8a5f2003778e2bbb3b709f5a74d2e5c5cfda7f24041974098c72


---

**Repository**: https://github.com/agno-agi/agno/issues/new

**Title**: `[Bug] RemoteAgent cannot be used as Team member - missing attributes`

**Labels**: `bug`

**Status**: ~~Open~~ → **Closed (Fixed in v2.3.26)**

---

## Bug Description

When using `RemoteAgent` as a member of a `Team`, the team execution fails with `AttributeError` because `RemoteAgent` is missing required attributes that `Team` expects.

## Environment

- **Agno Version**: ~~2.3.24~~ → **2.3.26 (Fixed)**
- **Python Version**: 3.11+
- **OS**: Windows 11

## Error Messages

```
ERROR    Error in Team run: 'RemoteAgent' object has no attribute 'knowledge_filters'
ERROR    Error in async generator: 'RemoteAgent' object has no attribute 'knowledge_filters'
```

When using `print_response()`, another error occurs:
```
AttributeError: 'RemoteAgent' object has no attribute 'output_schema'
```

## Code to Reproduce

### Remote Agent Service (image_agent.py)
```python
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.os import AgentOS

model = OpenAILike(
    id="deepseek-chat",
    api_key="sk-xxx",
    base_url="http://localhost:4001/v1",
)

image_generator = Agent(
    id="image-generator",
    name="Image Generator",
    model=model,
    instructions="You are an image generation assistant.",
    markdown=True
)

agent_os = AgentOS(
    name="Image Generator AgentOS",
    agents=[image_generator],
    a2a_interface=True,
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="image_agent:app", host="0.0.0.0", port=9999, reload=True)
```

### Main Application (agents_remote.py)
```python
from agno.agent import Agent, RemoteAgent
from agno.models.openai.like import OpenAILike
from agno.team import Team

model = OpenAILike(
    id="deepseek-chat",
    api_key="sk-xxx",
    base_url="http://localhost:4001/v1",
)

research_agent = Agent(
    id="research-agent",
    name="Research Agent",
    model=model,
    instructions="You are a research assistant.",
    markdown=True,
)

# RemoteAgent pointing to the AgentOS service
image_agent = RemoteAgent(
    base_url="http://localhost:9999",
    agent_id="image-generator",
)

# Team with both local and remote agents
creative_team = Team(
    id="creative-team",
    name="Creative Research Team",
    model=model,
    members=[research_agent, image_agent],  # This causes the error
    instructions="Coordinate research and image generation tasks.",
    markdown=True,
)
```

### Test Script (verify_agents_remote.py)
```python
from agents_remote import creative_team
import asyncio

async def test_remote_team():
    response = await creative_team.arun(
        "Research Elon Musk's features and create a portrait",
        user_id="test-user-123",
    )
    print(response.content)

if __name__ == "__main__":
    asyncio.run(test_remote_team())
```

## Expected Behavior

`RemoteAgent` should be usable as a `Team` member, as shown in the documentation:

From https://docs.agno.com/reference/agents/remote-agent:
```python
from agno.agent import RemoteAgent
from agno.team import Team
from agno.models import OpenAIChat

researcher = RemoteAgent(
    base_url="http://research-server:7777",
    agent_id="researcher-agent",
)

team = Team(
    name="Research Team",
    model=OpenAIChat(id="gpt-4o"),
    members=[researcher],
    instructions="Coordinate research tasks",
)

response = await team.arun("Research AI trends")
```

## Root Cause Analysis

It appears that `RemoteAgent` class is missing several attributes that the `Team` class expects all members to have:
- `knowledge_filters`
- `output_schema`

The `Team.arun()` and related methods try to access these attributes on all members, causing the error when a `RemoteAgent` is included.

## Suggested Fix

`RemoteAgent` should either:
1. Implement stub/default values for these attributes, or
2. `Team` should check if member is a `RemoteAgent` and handle it differently

## Additional Context

- The `RemoteAgent` works correctly when called directly with `await image_agent.arun()`
- The issue only occurs when `RemoteAgent` is used as a `Team` member
- Documentation shows this use case should be supported

Thank you for looking into this!
