import { API_BASE } from '../config';

const TEAM_API = `${API_BASE}/teams/creative-team/runs`;

// 取得可用的 Agent 列表
export async function getAgents() {
  const response = await fetch(`${API_BASE}/agents`);
  if (!response.ok) {
    throw new Error('Failed to fetch agents');
  }
  const data = await response.json();
  // AgentOS 回傳格式: { value: [...], Count: n }
  return data.value || data || [];
}

// 產生 UUID
export function generateSessionId() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

// 取得或建立 Session ID
export function getSessionId() {
  let sessionId = localStorage.getItem('sessionId');
  if (!sessionId) {
    sessionId = generateSessionId();
    localStorage.setItem('sessionId', sessionId);
  }
  return sessionId;
}

// 清除 Session
export function clearSession() {
  localStorage.removeItem('sessionId');
  return generateSessionId();
}

// SSE 串流解析共用函數
async function* parseSSEStream(response, signal) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = null;

  // 若 AbortSignal 觸發，立即關閉 reader
  if (signal) {
    signal.addEventListener('abort', () => {
      reader.cancel();
    }, { once: true });
  }

  try {
    while (true) {
      // 若已中止，直接結束
      if (signal?.aborted) break;

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmedLine = line.trim();

        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          try {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]') continue;

            const data = JSON.parse(dataStr);
            if (currentEvent) {
              data.event = currentEvent;
            }
            yield data;
            currentEvent = null;
          } catch (e) {
            console.error('Error parsing SSE data:', e);
          }
        } else if (trimmedLine === '') {
          currentEvent = null;
        }
      }
    }
  } finally {
    reader.cancel().catch(() => {});
  }
}

// 串流傳送訊息（單一 Agent）
export async function* sendMessage(message, sessionId, agentId = 'research-agent', signal) {
  const response = await fetch(`${API_BASE}/agents/${agentId}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      message,
      session_id: sessionId,
      stream: 'True',
      monitor: 'True'
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error('HTTP error! status: ' + response.status);
  }

  yield* parseSSEStream(response, signal);
}

// 串流傳送訊息（Team 模式）
export async function* sendTeamMessage(message, sessionId, signal) {
  const response = await fetch(TEAM_API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      message,
      session_id: sessionId,
      stream: 'True',
      monitor: 'True'
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error('HTTP error! status: ' + response.status);
  }

  yield* parseSSEStream(response, signal);
}

// 取得 Sessions（依類型: 'agent' 或 'team'）
export async function getSessions(type = 'agent') {
  const response = await fetch(`${API_BASE}/sessions?type=${type}&limit=100`);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${type} sessions`);
  }
  const result = await response.json();
  const list = result.data || [];
  // 為每筆 session 標記類型，方便前端判斷
  return list.map(s => ({ ...s, _type: type }));
}

// 取得特定 Session 的 Runs（對話歷史）
export async function getSessionRuns(sessionId, type = 'agent') {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/runs?type=${type}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!response.ok) {
    throw new Error('Failed to fetch session runs');
  }

  return response.json();
}

// 刪除 Session
export async function deleteSession(sessionId, type = 'agent') {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}?type=${type}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!response.ok) {
    throw new Error('Failed to delete session');
  }

  // 處理空回應（DELETE 通常不回傳 body）
  const text = await response.text();
  return text ? JSON.parse(text) : { success: true };
}

// 重命名 Session
export async function renameSession(sessionId, newName, type = 'agent') {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/rename?type=${type}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: newName })
  });

  if (!response.ok) {
    throw new Error('Failed to rename session');
  }

  return response.json();
}
