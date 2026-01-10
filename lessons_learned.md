# Lessons Learned

## Agno SSE Event Structure

When consuming the Server-Sent Events (SSE) stream from Agno's `AgentOSClient` or `OpenAILike` backend, the event structure for tool calls differs slightly from standard OpenAI formats.

### ToolCallStartedEvent

To correctly extract the tool name and arguments from a `ToolCallStarted` event in the frontend:

**Correct Access Path:**
- **Tool Name:** `event.tool.tool_name`
- **Tool Arguments:** `event.tool.tool_args`

**Note:**
- The event type string is `ToolCallStarted` or `ToolCallStart`.
- Do not rely solely on `event.tool_name` or `event.tool_call.function.name` (OpenAI style) as these may be missing or empty depending on the specific event version.

**Example JS Handling:**
```javascript
if (event.type === 'ToolCallStarted') {
    // Correct way to access tool details
    const toolName = event.tool?.tool_name || 'Unknown Tool';
    const toolArgs = event.tool?.tool_args || {};
    
    console.log(`Tool started: ${toolName}`, toolArgs);
}
```

### Reference Code
(Provided by User)
```python
from agno.run.agent import ToolCallStartedEvent, ToolCallCompletedEvent

async for event in client.run_agent_stream(...):
    if isinstance(event, ToolCallStartedEvent):
        print(f"Tool started: {event.tool.tool_name}")
    elif isinstance(event, ToolCallCompletedEvent):
        print(f"Tool completed: {event.tool.tool_name}")
```
