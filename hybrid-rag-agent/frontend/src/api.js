const BASE = '';

export async function fetchHealth() {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- Database ----
export async function fetchTables(schema) {
  const params = schema ? `?schema=${encodeURIComponent(schema)}` : '';
  const res = await fetch(`${BASE}/api/db/tables${params}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchTableSchema(tableName, schema) {
  const params = schema ? `?schema=${encodeURIComponent(schema)}` : '';
  const res = await fetch(`${BASE}/api/db/tables/${encodeURIComponent(tableName)}/schema${params}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchTableRows(tableName, { schema, limit = 50, offset = 0 } = {}) {
  const sp = new URLSearchParams();
  if (schema) sp.set('schema', schema);
  sp.set('limit', String(limit));
  sp.set('offset', String(offset));
  const res = await fetch(`${BASE}/api/db/tables/${encodeURIComponent(tableName)}/rows?${sp}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- Chat (SSE) ----
export function streamChat(message, sessionId, onEvent) {
  const ctrl = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId }),
        signal: ctrl.signal,
      });

      if (!res.ok) {
        onEvent({ type: 'error', data: { message: `HTTP ${res.status}` } });
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = null;
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ') && currentEvent) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent({ type: currentEvent, data });
            } catch {
              // ignore parse errors
            }
            currentEvent = null;
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        onEvent({ type: 'error', data: { message: err.message } });
      }
    }
  })();

  return () => ctrl.abort();
}
