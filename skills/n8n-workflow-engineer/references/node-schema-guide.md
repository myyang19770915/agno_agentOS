# Node Schema Guide

<!-- TOC -->
- [How to Identify Correct typeVersion](#how-to-identify-correct-typeversion)
- [Common Node Schemas](#common-node-schemas)
  - [Schedule Trigger](#schedule-trigger)
  - [Gmail (getAll)](#gmail-getall)
  - [Code Node](#code-node)
  - [OpenAI (direct, non-LangChain)](#openai-direct-non-langchain)
  - [Telegram](#telegram)
- [AI Agent Pattern (LangChain)](#ai-agent-pattern-langchain)
- [Critical Pitfalls](#critical-pitfalls)
<!-- /TOC -->

---

## How to Identify Correct typeVersion

Always run `n8nac skills node-info <nodeName>` before writing any node.
The example in the output shows the latest valid version.

```bash
n8nac skills node-info scheduleTrigger   # → version: 1.3
n8nac skills node-info gmail             # → version: 2.2
n8nac skills node-info telegram          # → version: 1.2
n8nac skills node-info openAi           # → version: 1.1  (direct, non-LangChain)
n8nac skills node-info lmChatOpenAi     # → version: 1.3  (LangChain sub-node)
n8nac skills node-info agent            # → version: 3.1+ (LangChain AI Agent)
n8nac skills node-info code             # → version: 2
```

---

## Common Node Schemas

### Schedule Trigger

```typescript
@node({ name: 'Schedule Trigger', type: 'n8n-nodes-base.scheduleTrigger', version: 1.3, position: [0, 0] })
ScheduleTrigger = {
  rule: {
    interval: [{
      field: 'weeks',          // seconds | minutes | hours | days | weeks | months | cronExpression
      weeksInterval: 1,
      triggerAtDay: '1',       // '0'=Sun '1'=Mon ... '6'=Sat
      triggerAtHour: '8',      // '0'-'23' as STRING
      triggerAtMinute: 0       // number
    }]
  }
};
```

### Gmail (getAll)

```typescript
@node({ name: 'Gmail Get All', type: 'n8n-nodes-base.gmail', version: 2.1, position: [200, 0],
  credentials: { gmailOAuth2: { id: 'CRED_ID', name: 'Gmail account' } }
})
GmailGetAll = {
  resource: 'message',
  operation: 'getAll',
  returnAll: false,
  limit: 20,
  simple: true,
  filters: {
    q: 'subject:(商周 OR 商週) newer_than:7d'   // Gmail search syntax
  }
};
```

### Code Node

```typescript
@node({ name: 'Combine Content', type: 'n8n-nodes-base.code', version: 2, position: [400, 0] })
CombineContent = {
  mode: 'runOnceForAllItems',   // or 'runOnceForEachItem'
  jsCode: `
const items = $input.all();
const combined = items.map(i => i.json.snippet || '').join('\\n\\n---\\n\\n');
return [{ json: { combined, count: items.length } }];
`
};
```

### OpenAI (direct, non-LangChain)

Use `n8n-nodes-base.openAi` version `1.1` for direct chat calls (not inside an AI Agent chain).

```typescript
@node({ name: 'OpenAI Summary', type: 'n8n-nodes-base.openAi', version: 1.1, position: [600, 0],
  credentials: { openAiApi: { id: 'CRED_ID', name: 'OpenAi account' } }
})
OpenAiSummary = {
  resource: 'chat',
  chatModel: 'gpt-4o-mini',
  prompt: {
    messages: [
      { role: 'system', content: 'You are a helpful assistant.' },
      { role: 'user',   content: '={{ $json.combined }}' }
    ]
  },
  simplifyOutput: true,
  options: {}
};
// Output: $json.message.content
```

> ⚠️ Do NOT use `@n8n/n8n-nodes-langchain.openAi` — that type does not exist.
> The correct LangChain package node is `@n8n/n8n-nodes-langchain.lmChatOpenAi` (sub-model only).

### Telegram

```typescript
@node({ name: 'Telegram Send', type: 'n8n-nodes-base.telegram', version: 1.2, position: [800, 0],
  credentials: { telegramApi: { id: 'CRED_ID', name: 'Telegram account' } }
})
TelegramSend = {
  chatId: '{{ CHAT_ID }}',
  text: '={{ $json.message.content }}',
  additionalFields: {
    parse_mode: 'Markdown'
  }
};
```

---

## AI Agent Pattern (LangChain)

Regular nodes → `.out(0).to(target.in(0))`  
AI sub-nodes (model, memory, tool, parser) → `.uses()` — NEVER `.out().to()`

```typescript
// Trigger → Agent (regular routing)
this.ChatTrigger.out(0).to(this.AiAgent.in(0));

// Sub-nodes via .uses()
this.AiAgent.uses({
  ai_languageModel: this.OpenaiModel.output,       // single ref
  ai_memory:        this.Memory.output,            // single ref
  ai_tool:          [this.SearchTool.output],      // ALWAYS array
  ai_outputParser:  this.OutputParser.output,      // single ref
});
```

Key versions for LangChain nodes:
- `@n8n/n8n-nodes-langchain.agent` → version `3.1`
- `@n8n/n8n-nodes-langchain.lmChatOpenAi` → version `1.3`
- `@n8n/n8n-nodes-langchain.memoryBufferWindow` → version `1.3`
- `@n8n/n8n-nodes-langchain.chatTrigger` → version `1.4`

---

## Critical Pitfalls

| Error in n8n UI | Root Cause | Fix |
|----------------|------------|-----|
| "Could not find workflow" | `typeVersion` not in schema's valid array | Run `node-info`, use the version shown in example |
| "Could not find property option" | Invalid `operation` or `resource` string | Run `node-info`, check exact `options[].value` strings |
| AI sub-node invisible/broken | Used `.out().to()` for LangChain sub-node | Switch to `.uses()` |
| `ai_tool` not connected | Used `ai_tool: this.Tool.output` (not array) | Use `ai_tool: [this.Tool.output]` (array) |
| Switch/If rule never matches | `value1`/`value2` swapped | `value1` = expression, `value2` = literal |
| Unknown parameter warning | Typo or deprecated field name | Re-check `node-info` for exact field names |
