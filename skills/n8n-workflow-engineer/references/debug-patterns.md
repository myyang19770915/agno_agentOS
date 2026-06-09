# Debug Patterns

<!-- TOC -->
- [Validate Output Interpretation](#validate-output-interpretation)
- [Error: typeVersion does not exist](#error-typeversion-does-not-exist)
- [Error: invalid operation / Could not find property option](#error-invalid-operation--could-not-find-property-option)
- [Error: AI sub-node invisible or broken connection](#error-ai-sub-node-invisible-or-broken-connection)
- [Error: Push rejected (OCC conflict)](#error-push-rejected-occ-conflict)
- [Test Failure: Class A vs Class B](#test-failure-class-a-vs-class-b)
- [Real Example: Gmail + OpenAI Workflow Debug Session](#real-example-gmail--openai-workflow-debug-session)
<!-- /TOC -->

---

## Validate Output Interpretation

```bash
n8nac skills validate my-workflow.workflow.ts
```

Output structure:
```
❌ Errors (N):
  • <message> [NodePropertyName]
    Path: nodes[NodePropertyName].<field>

⚠️  Warnings (N):
  • Unknown parameter: "fieldName". [NodePropertyName]
```

- **Errors** = blocking: push will produce broken workflow in n8n
- **Warnings** = non-blocking but investigate: unknown parameter means typo or deprecated field

---

## Error: typeVersion does not exist

**Symptom (validate output):**
```
typeVersion 1.7 does not exist for node "@n8n/n8n-nodes-langchain.openAi".
Valid versions: [1, 1.1]. Use 1.1 (latest).
```

**Root cause:** Used a version number not in the schema's valid array.

**Fix:**
1. Run `n8nac skills node-info <nodeType>` to see the example — it always shows the latest valid version
2. Update the `version` field in `@node({...})` decorator to match

**Common version traps:**

| Wrong | Correct | Node |
|-------|---------|------|
| `version: 1.7` | `version: 1.1` | `n8n-nodes-base.openAi` |
| `version: 1.6` | `version: 2.2` | `n8n-nodes-base.if` |
| `version: 3` | `version: 3.1` | `@n8n/n8n-nodes-langchain.agent` |

---

## Error: invalid operation / Could not find property option

**Symptom (n8n UI):** "Could not find property option" when opening workflow

**Root cause:** The `operation` or `resource` string doesn't match any valid option value.

**Fix:**
```bash
n8nac skills node-info <nodeName>
# Look at: resource?: 'chat' | 'image' | 'text'
# Look at: operation?: 'create' | 'delete' | 'get' | 'getAll'
```

Use the EXACT strings from the schema — not guesses:
- ❌ `operation: 'post'` (Slack) → ✅ `operation: 'create'`
- ❌ `operation: 'send'` (Gmail) → ✅ `operation: 'create'`
- ❌ `resource: 'email'` (Gmail) → ✅ `resource: 'message'`

Also: each `resource` value unlocks a different set of valid `operation` values.
Never mix `operation` from one resource with a different resource.

---

## Error: AI sub-node invisible or broken connection

**Symptom:** LangChain sub-node (model, memory, tool) floats disconnected in n8n canvas

**Root cause:** Used `.out(0).to()` for a node that requires `.uses()`

**Identify:** Any node flagged `[ai_languageModel]`, `[ai_memory]`, `[ai_tool]`,
`[ai_outputParser]`, `[ai_document]` in the workflow-map MUST use `.uses()`

**Wrong:**
```typescript
this.OpenaiModel.out(0).to(this.AiAgent.in(0));
```

**Correct:**
```typescript
this.AiAgent.uses({
  ai_languageModel: this.OpenaiModel.output,
  ai_tool:          [this.Calculator.output],  // tools are always arrays
});
```

---

## Error: Push rejected (OCC conflict)

**Symptom:**
```
Push rejected: remote version is newer than your local version
```

**Cause:** Workflow was modified in n8n UI after the last pull.

**Fix options:**
```bash
# Option A: Keep your local version (force push)
n8nac resolve <id> --mode keep-current

# Option B: Keep the remote (discard local)
n8nac resolve <id> --mode keep-incoming
```

---

## Test Failure: Class A vs Class B

After `n8nac test <id>`:

### Class A — Configuration Gap (exit code 0)

```
⚠  Configuration gap detected (Class A)
Missing: OpenAI credentials / model not configured
```

**What it means:** The workflow code is correct, but requires manual setup in n8n UI.
**Action:** Tell the user what to configure (credentials, model selection, env var).
**NEVER:** Re-edit or re-push the workflow to "fix" a Class A error.

### Class B — Wiring Error (exit code 1)

```
❌ Workflow execution failed (Class B)
Error: Cannot read property 'content' of undefined at "Telegram Send"
```

**What it means:** The workflow logic has a bug — wrong expression, wrong field reference.
**Action:** Fix the `.workflow.ts` file, push, and run `n8nac test` again.

---

## Real Example: Gmail + OpenAI Workflow Debug Session

This is a real debug session from building the `商周文章-每週彙整報告.workflow.ts` workflow.

### Attempt 1 — Wrong node type for OpenAI

**Written:**
```typescript
@node({ type: '@n8n/n8n-nodes-langchain.openAi', version: 1.7 })
OpenAiSummary = {
  modelId: { __rl: true, value: 'gpt-4o-mini', mode: 'list' },
  messages: { values: [...] }
};
```

**Validate output:**
```
❌ typeVersion 1.7 does not exist for "@n8n/n8n-nodes-langchain.openAi". Valid: [1, 1.1]
⚠  Unknown parameter: "modelId"
⚠  Unknown parameter: "messages"
```

**Root cause analysis:**
- `@n8n/n8n-nodes-langchain.openAi` does not accept `modelId` or `messages` directly
- It is only a sub-node wrapper; the correct direct-call node is `n8n-nodes-base.openAi`

**Fix applied:**
```typescript
@node({ type: 'n8n-nodes-base.openAi', version: 1.1 })
OpenAiSummary = {
  resource: 'chat',
  chatModel: 'gpt-4o-mini',
  prompt: {
    messages: [
      { role: 'system', content: '...' },
      { role: 'user',   content: '={{ $json.combined }}' }
    ]
  },
  simplifyOutput: true
};
```

**Result:** `✅ Workflow is valid!` → pushed → `✅ Workflow looks clean — no issues found.`

### Key lesson

When you need OpenAI for a **direct chat call** (not inside an AI Agent chain):
- Use `n8n-nodes-base.openAi` (version `1.1`)
- Output is at `$json.message.content`

When you need OpenAI as a **language model inside an AI Agent**:
- Use `@n8n/n8n-nodes-langchain.lmChatOpenAi` (version `1.3`)
- Connect via `agent.uses({ ai_languageModel: this.Model.output })`
