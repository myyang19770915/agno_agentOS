---
name: n8n-workflow-engineer
description: >
  Expert n8n workflow engineer skill for creating, editing, debugging, and deploying n8n workflows
  as TypeScript code using the n8nac CLI (n8n-as-code). USE FOR: creating new .workflow.ts files
  from scratch; editing or extending existing workflows (pull → edit → push); debugging broken
  nodes (wrong typeVersion, invalid operation, missing parameters); validating workflow syntax
  locally; pushing and verifying workflows live on n8n; understanding the git-like sync lifecycle
  (list/pull/push/verify). Also covers: researching correct node schemas with "n8nac skills
  node-info", searching community examples, testing webhook/chat/form triggers. DO NOT USE FOR:
  general n8n UI questions; n8n server administration; installing n8n itself.
---

# n8n Workflow Engineer

Design, debug, and deploy n8n workflows as version-controlled TypeScript (`.workflow.ts`) files
using the `n8nac` CLI.

---

## Setup Check

Before any workflow operation, confirm `n8nac-config.json` exists in the workspace root:

```json
{
  "host": "https://your-n8n-host",
  "syncFolder": "workflows",
  "projectId": "<id>",
  "projectName": "Personal",
  "instanceIdentifier": "<slug>"
}
```

If missing → run init:
```bash
npx --yes n8nac init-auth --host <url> --api-key <key>
npx --yes n8nac init-project --project-index 1 --sync-folder workflows
```

Install CLI globally to avoid repeated downloads:
```bash
npm install -g n8nac
```

---

## Git-like Sync Lifecycle (CRITICAL)

```
n8n UI  ←──pull──  .workflow.ts  ──push──→  n8n UI
                        ↑
                  Agent edits here
```

| Command | Purpose |
|---------|---------|
| `n8nac list` | Show all workflows + sync status |
| `n8nac pull <id>` | Download remote → local |
| `n8nac push <filename.workflow.ts>` | Upload local → remote |
| `n8nac push <filename.workflow.ts> --verify` | Push + immediate schema verify |
| `n8nac verify <id>` | Fetch live workflow + validate schema |

**Rules:**
- Always `pull` before editing an existing workflow (Optimistic Concurrency Control)
- `push` takes only the **filename** (with `.workflow.ts` suffix), NOT a path or workflow title
- New workflows must be created inside the active sync folder (check `n8nac list --local` for path)

---

## Research Protocol (MANDATORY before writing any node)

```bash
# 1. Find the exact node name
n8nac skills search "google sheets"

# 2. Get exact schema: typeVersion, parameters, valid operation/resource values
n8nac skills node-info googleSheets

# 3. Browse community examples for patterns
n8nac skills examples search "gmail summarize telegram"
```

See [references/node-schema-guide.md](references/node-schema-guide.md) for common schema patterns
and known pitfalls.

---

## Minimal Workflow Template

```typescript
import { workflow, node, links } from '@n8n-as-code/transformer';

@workflow({ name: 'My Workflow', active: false })
export class MyWorkflow {
  @node({
    name: 'Schedule Trigger',
    type: 'n8n-nodes-base.scheduleTrigger',
    version: 1.3,
    position: [0, 0]
  })
  ScheduleTrigger = {
    rule: {
      interval: [{ field: 'days', daysInterval: 1, triggerAtHour: '8', triggerAtMinute: 0 }]
    }
  };

  @node({ name: 'Next Node', type: 'n8n-nodes-base.noOp', version: 1, position: [200, 0] })
  NextNode = {};

  @links()
  defineRouting() {
    this.ScheduleTrigger.out(0).to(this.NextNode.in(0));
  }
}
```

---

## Validate → Push → Verify Cycle

```bash
# 1. Local syntax + schema check (catches wrong typeVersion, unknown params)
n8nac skills validate my-workflow.workflow.ts

# 2. Push (creates new or updates existing in n8n)
n8nac push my-workflow.workflow.ts

# 3. Verify live runtime schema (catches invalid operation values, bad combos)
n8nac verify <workflowId>

# Shorthand: push + verify in one command
n8nac push my-workflow.workflow.ts --verify
```

After push, run `n8nac list` to get the assigned workflow ID before running `verify`.

---

## Debug Guide

See [references/debug-patterns.md](references/debug-patterns.md) for:
- Fixing `typeVersion does not exist` errors
- Fixing `invalid operation` / `Could not find property option` errors
- Fixing broken AI sub-node connections (`.uses()` vs `.out().to()`)
- Interpreting Class A vs Class B test failures

---

## Testing Webhook / Chat / Form Workflows

```bash
n8nac test-plan <id>          # Is it HTTP-testable? What payload?
n8nac test <id>               # Fire test-mode URL, report result
```

**Class A** (exit 0) = config gap (credentials, model not set) → inform user, do NOT re-edit code  
**Class B** (exit 1) = wiring error (bad expression, wrong field) → fix `.workflow.ts`, push, re-test
