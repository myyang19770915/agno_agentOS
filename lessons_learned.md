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

---

## PythonTools 的 stdout 黑洞問題：Agent 無法自我修正

**日期：** 2026-03-03  
**檔案：** `backend/agents_remote.py`

### 問題現象

後端 terminal 持續出現以下錯誤輸出：

```
Error: strip() got an unexpected keyword argument 'jitter'
Traceback (most recent call last):
  File "<string>", line 29, in <module>
TypeError: strip() got an unexpected keyword argument 'jitter'
```

但 agent 始終無法察覺這個錯誤，也無法自我修正，持續重試相同的錯誤程式碼。

### 根本原因

Agno 的 `PythonTools.run_python_code()` 使用 Python 內建 `exec()` 執行使用者程式碼，但**不重定向 `sys.stdout` 與 `sys.stderr`**。

這導致三種失敗情境：

| 情境 | `exec()` 行為 | Agent 收到的回傳值 | 實際輸出去哪了 |
|------|-------------|------------------|--------------|
| 程式碼執行成功，有 `print()` | 成功執行 | `"successfully ran python code"` | 全部寫到 server terminal |
| try/except 捕獲例外並 `print(traceback)` | 成功執行（未拋出） | `"successfully ran python code"` | Traceback 寫到 terminal，agent 不知道 |
| `exec()` 本身拋出例外 | 拋出 | `"Error running python code: {e}"` | 只有錯誤訊息，無行號無 traceback |

**結論：PythonTools 的執行結果對 agent 是「黑洞」— agent 盲目執行，從不知道輸出與錯誤。**

### 修法：建立 `CapturedPythonTools` 子類別

在 `agents_remote.py` 覆寫 `run_python_code`，用 `io.StringIO` 重定向 `sys.stdout/stderr`，並在 except 中附上完整 traceback 回傳給 agent：

```python
import io
import sys
import traceback as _traceback_module
from agno.tools.python import PythonTools

class CapturedPythonTools(PythonTools):
    def run_python_code(self, code: str, variable_to_return=None) -> str:
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = captured_stdout
        sys.stderr = captured_stderr
        try:
            exec(code, self.safe_globals, self.safe_locals)
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            stdout_output = captured_stdout.getvalue()
            stderr_output = captured_stderr.getvalue()

            if variable_to_return:
                variable_value = self.safe_locals.get(variable_to_return)
                if variable_value is None:
                    return f"Variable {variable_to_return} not found"
                return str(variable_value)

            parts = []
            if stdout_output:
                parts.append(stdout_output.rstrip())
            if stderr_output:
                parts.append(f"[stderr]:\n{stderr_output.rstrip()}")
            return "\n".join(parts) if parts else "successfully ran python code"

        except Exception as e:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            stdout_output = captured_stdout.getvalue()
            stderr_output = captured_stderr.getvalue()
            full_traceback = _traceback_module.format_exc()
            parts = []
            if stdout_output:
                parts.append(stdout_output.rstrip())
            if stderr_output:
                parts.append(f"[stderr]:\n{stderr_output.rstrip()}")
            parts.append(f"Error: {e}\nTraceback:\n{full_traceback}")
            return "\n".join(parts)
```

將 agent tools 清單中的 `PythonTools(...)` 改為 `CapturedPythonTools(...)` 即完成套用。

### 修改後行為

- `print()` 輸出 → agent 可見，作為工具執行結果回報
- try/except 印出的 Traceback → agent 可見，觸發 Self-Correction Logic
- `exec()` 直接拋出例外 → agent 看到含行號的完整 traceback，可精準定位並修正
- Instruction 中設有「出現 `Error:` 時至少重試 2 次」的自我修正邏輯，修法後此機制終於能正常運作

### 通用原則

> 使用 `exec()` 執行動態程式碼時，**務必在執行前重定向 `sys.stdout` 與 `sys.stderr`**，否則所有輸出對呼叫端（包括 agent）完全不可見，形同黑洞。
