import { API_BASE } from '../config';
import { getUserId } from './userContext';

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
  const params = {
    message,
    session_id: sessionId,
    stream: 'True',
    monitor: 'True'
  };
  const userId = getUserId();
  if (userId) params.user_id = userId;

  const response = await fetch(`${API_BASE}/agents/${agentId}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(params),
    signal,
  });

  if (!response.ok) {
    throw new Error('HTTP error! status: ' + response.status);
  }

  yield* parseSSEStream(response, signal);
}

// 串流傳送訊息（Team 模式）
export async function* sendTeamMessage(message, sessionId, signal) {
  const params = {
    message,
    session_id: sessionId,
    stream: 'True',
    monitor: 'True'
  };
  const userId = getUserId();
  if (userId) params.user_id = userId;

  const response = await fetch(TEAM_API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(params),
    signal,
  });

  if (!response.ok) {
    throw new Error('HTTP error! status: ' + response.status);
  }

  yield* parseSSEStream(response, signal);
}

// 取得 Image Agent 的 Sessions（透過主後端 proxy）
async function getImageAgentSessions() {
  try {
    const userId = getUserId();
    const userParam = userId ? `&user_id=${encodeURIComponent(userId)}` : '';
    const response = await fetch(`${API_BASE}/image-agent/sessions?limit=100${userParam}`);
    if (!response.ok) return [];
    const result = await response.json();
    const list = result.data || [];
    // 標記來源為 image-agent，讓前端知道如何取得 runs 及刪除
    return list.map(s => ({ ...s, _type: 'agent', _source: 'image-agent' }));
  } catch {
    // Image agent 不可用時靜默回傳空陣列
    return [];
  }
}

// 取得 Sessions（依類型: 'agent' 或 'team'，依 user_id 過濾）
// Agent 模式同時查詢 research agent 和 image agent sessions，合併去重
export async function getSessions(type = 'agent') {
  const userId = getUserId();
  const userParam = userId ? `&user_id=${encodeURIComponent(userId)}` : '';
  const response = await fetch(`${API_BASE}/sessions?type=${type}&limit=100${userParam}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${type} sessions`);
  }
  const result = await response.json();
  const list = (result.data || []).map(s => ({ ...s, _type: type }));

  // Agent 模式下，同時取得 image agent sessions 並合併
  if (type === 'agent') {
    const imageSessions = await getImageAgentSessions();
    // 去重：排除 session_id 已存在於主列表中的 image sessions（team 委派產生的重複）
    const existingIds = new Set(list.map(s => s.session_id));
    const uniqueImageSessions = imageSessions.filter(s => !existingIds.has(s.session_id));
    return [...list, ...uniqueImageSessions];
  }

  return list;
}

// 取得特定 Session 的 Runs（對話歷史）
// source: 若為 'image-agent'，透過 proxy endpoint 查詢
export async function getSessionRuns(sessionId, type = 'agent', source = null) {
  // Image agent sessions 透過 proxy 查詢
  if (source === 'image-agent') {
    const response = await fetch(`${API_BASE}/image-agent/sessions/${sessionId}/runs`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!response.ok) {
      throw new Error('Failed to fetch image agent session runs');
    }
    return response.json();
  }

  const userId = getUserId();
  const userParam = userId ? `&user_id=${encodeURIComponent(userId)}` : '';
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/runs?type=${type}${userParam}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!response.ok) {
    throw new Error('Failed to fetch session runs');
  }

  return response.json();
}

// 刪除 Session
// source: 若為 'image-agent'，透過 proxy endpoint 刪除
export async function deleteSession(sessionId, type = 'agent', source = null) {
  // Image agent sessions 透過 proxy 刪除
  if (source === 'image-agent') {
    const response = await fetch(`${API_BASE}/image-agent/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!response.ok) {
      throw new Error('Failed to delete image agent session');
    }
    const text = await response.text();
    return text ? JSON.parse(text) : { success: true };
  }

  const userId = getUserId();
  const userParam = userId ? `&user_id=${encodeURIComponent(userId)}` : '';
  const response = await fetch(`${API_BASE}/sessions/${sessionId}?type=${type}${userParam}`, {
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
  const userId = getUserId();
  const userParam = userId ? `&user_id=${encodeURIComponent(userId)}` : '';
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/rename?type=${type}${userParam}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: newName })
  });

  if (!response.ok) {
    throw new Error('Failed to rename session');
  }

  return response.json();
}
