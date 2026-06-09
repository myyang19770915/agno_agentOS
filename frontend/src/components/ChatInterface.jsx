import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { sendMessage, sendTeamMessage, getSessionId, clearSession, generateSessionId, getAgents } from '../services/api';
import Message from './Message';
import ToolStatus from './ToolStatus';
import './ChatInterface.css';

// 支援的檔案類型
const ACCEPTED_FILE_TYPES = [
  // 圖片
  'image/png', 'image/jpeg', 'image/webp', 'image/gif',
  // 音訊
  'audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/ogg',
  // 影片
  'video/mp4', 'video/webm', 'video/ogg',
  // 文件
  'application/pdf',
  'text/csv', 'text/plain',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
  'application/json',
].join(',');

function mergeStreamText(existing, incoming) {
  if (!incoming) return existing;
  if (!existing) return incoming;
  if (existing.endsWith(incoming)) return existing;
  if (incoming.startsWith(existing)) return incoming;
  return existing + incoming;
}

function splitReasoningFromContent(rawContent) {
  if (!rawContent) {
    return { content: '', thinkingContent: '' };
  }

  const content = String(rawContent);

  const thinkingTagMatch = content.match(/<thinking>([\s\S]*?)<\/thinking>/i);
  if (thinkingTagMatch) {
    return {
      content: content.replace(thinkingTagMatch[0], '').trim(),
      thinkingContent: thinkingTagMatch[1].trim(),
    };
  }

  const markdownReasoningHeading = content.match(/(^|\n)##\s*(一步一步思考過程|思考過程|推理過程|分析過程)\s*\n/i);
  if (markdownReasoningHeading) {
    const reasoningStart = markdownReasoningHeading.index + markdownReasoningHeading[0].length;
    const answerHeading = /\n##\s*(答案|最終答案|結論)\s*\n/i;
    const remaining = content.slice(reasoningStart);
    const answerMatch = remaining.match(answerHeading);

    if (answerMatch) {
      const answerStart = reasoningStart + answerMatch.index + 1;
      return {
        content: content.slice(answerStart).trim(),
        thinkingContent: content.slice(reasoningStart, reasoningStart + answerMatch.index).trim(),
      };
    }
  }

  const inlineReasoningMatch = content.match(/(?:\n|^)\*\*Reasoning:\*\*|(?:\n|^)Reasoning:/i);
  if (inlineReasoningMatch && typeof inlineReasoningMatch.index === 'number') {
    const markerStart = inlineReasoningMatch.index;
    const markerEnd = markerStart + inlineReasoningMatch[0].length;
    const mainContent = content.slice(0, markerStart).trim();
    const reasoningContent = content.slice(markerEnd).trim();

    if (reasoningContent) {
      return {
        content: mainContent,
        thinkingContent: reasoningContent,
      };
    }
  }

  return { content, thinkingContent: '' };
}

function createAssistantPlaceholder() {
  return {
    role: 'assistant',
    content: '',
    thinkingContent: '',
    isStreaming: true,
  };
}

const ChatInterface = forwardRef(function ChatInterface({ onSessionChange, onMessageSent, isTeamMode, onTeamModeChange, userId }, ref) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(getSessionId());
  const [activeTools, setActiveTools] = useState([]);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [agents, setAgents] = useState([]);  // 可用 Agent 列表
  const [selectedAgent, setSelectedAgent] = useState('');  // 選中的 Agent ID
  const [reasoningContent, setReasoningContent] = useState('');  // Reasoning model 思考內容
  const [isThinking, setIsThinking] = useState(false);  // 是否正在思考中
  const [thinkingExpanded, setThinkingExpanded] = useState(false);  // 思考區塊是否展開
  const [uploadFiles, setUploadFiles] = useState([]);  // 已選擇的上傳檔案
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const shouldAutoScrollRef = useRef(true);
  const scrollTimeoutRef = useRef(null);
  const abortControllerRef = useRef(null);
  const inactivityTimerRef = useRef(null);
  const fileInputRef = useRef(null);
  const INACTIVITY_TIMEOUT_MS = 3 * 60 * 1000; // 3 分鐘無事件則逾時

  // 檢查是否接近底部（用於決定是否自動滾動）
  const isNearBottom = () => {
    const container = messagesContainerRef.current;
    if (!container) return true;
    const threshold = 100; // 距離底部 100px 以內視為接近底部
    return container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
  };

  // 防抖動滾動到底部
  const scrollToBottom = (force = false) => {
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }
    scrollTimeoutRef.current = setTimeout(() => {
      if (force || shouldAutoScrollRef.current) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
      }
    }, 50); // 50ms 防抖
  };

  const handleMessagesScroll = () => {
    shouldAutoScrollRef.current = isNearBottom();
  };

  useEffect(() => {
    scrollToBottom(shouldAutoScrollRef.current);
  }, [messages, activeTools]);

  // 通知父元件 session 變更
  useEffect(() => {
    if (onSessionChange) {
      onSessionChange(sessionId);
    }
  }, [sessionId, onSessionChange]);

  // 元件卸載時中止任何進行中的請求
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      clearTimeout(inactivityTimerRef.current);
    };
  }, []);

  // 初始化時載入可用 Agent 列表
  useEffect(() => {
    getAgents()
      .then((list) => {
        setAgents(list);
        // 預設選第一個 Agent
        if (list.length > 0 && !selectedAgent) {
          setSelectedAgent(list[0].id);
        }
      })
      .catch((err) => {
        console.error('Failed to load agents:', err);
        // 回退到預設值
        setAgents([{ id: 'research-agent', name: 'Research Agent' }]);
        setSelectedAgent('research-agent');
      });
  }, []);

  // 暴露方法給父元件
  useImperativeHandle(ref, () => ({
    // 載入指定 session 的對話
    loadSession: (newSessionId, runs) => {
      setSessionId(newSessionId);
      localStorage.setItem('sessionId', newSessionId);
      setActiveTools([]);
      setCurrentAgent(null);

      // 從 runs 中提取訊息
      const loadedMessages = extractMessagesFromRuns(runs);
      setMessages(loadedMessages);
    },
    // 開始新對話
    startNewSession: () => {
      const newSessionId = generateSessionId();
      setSessionId(newSessionId);
      localStorage.setItem('sessionId', newSessionId);
      setMessages([]);
      setActiveTools([]);
      setCurrentAgent(null);
    }
  }));

  // 從 runs 資料中提取訊息
  function extractMessagesFromRuns(runs) {
    const messages = [];

    if (!runs) return messages;

    // runs 可能是 { runs: [...] } 或直接是陣列
    const runList = runs.runs || runs || [];

    runList.forEach(run => {
      // 每個 run 可能包含 messages 陣列
      if (run.messages && Array.isArray(run.messages)) {
        run.messages.forEach(msg => {
          if (msg.role === 'user' || msg.role === 'assistant') {
            messages.push({
              role: msg.role,
              content: msg.content || ''
            });
          }
        });
      }

      // 或者可能有 input 和 output
      if (run.input) {
        messages.push({ role: 'user', content: run.input });
      }
      if (run.output) {
        messages.push({ role: 'assistant', content: run.output });
      }
    });

    return messages;
  }

  const handleNewSession = () => {
    // 中止任何進行中的請求
    abortControllerRef.current?.abort();
    clearTimeout(inactivityTimerRef.current);
    const newSessionId = clearSession();
    setSessionId(newSessionId);
    localStorage.setItem('sessionId', newSessionId);
    setMessages([]);
    setActiveTools([]);
    setCurrentAgent(null);
    setReasoningContent('');
    setIsThinking(false);
    setThinkingExpanded(false);
    shouldAutoScrollRef.current = true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if ((!input.trim() && uploadFiles.length === 0) || isLoading) return;

    const userMessage = input.trim() || (uploadFiles.length > 0 ? '請分析上傳的檔案' : '');
    const filesToSend = [...uploadFiles];  // 保存當前檔案後清除
    setInput('');
    setUploadFiles([]);

    // 組合使用者訊息（顯示檔案名稱）
    const fileNames = filesToSend.map(f => f.name);
    const displayContent = fileNames.length > 0
      ? `${userMessage}\n\n📎 ${fileNames.join(', ')}`
      : userMessage;
    setMessages(prev => [...prev, { role: 'user', content: displayContent }]);
    setIsLoading(true);
    setActiveTools([]);
    setCurrentAgent(null);
    setReasoningContent('');
    setIsThinking(false);
    setThinkingExpanded(false);
    shouldAutoScrollRef.current = true;
    setMessages(prev => [...prev, createAssistantPlaceholder()]);

    // 建立新的 AbortController，中止上一次未完成的請求
    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // 重置閒置計時器（每次收到事件就重置；逾時則中止）
    const resetInactivityTimer = () => {
      clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = setTimeout(() => {
        if (!abortController.signal.aborted) {
          console.warn('[Timeout] 超過', INACTIVITY_TIMEOUT_MS / 1000, '秒無回應，自動中止');
          abortController.abort();
          setIsLoading(false);
          setActiveTools([]);
          setCurrentAgent(null);
          setMessages(prev => {
            const last = prev[prev.length - 1];
            const timeoutNote = '\n\n> ⚠️ **等待逾時：長時間未收到回應，請稍後再試或重新發送。**';
            if (last?.role === 'assistant' && last.content) {
              const updated = [...prev];
              updated[updated.length - 1] = { ...last, content: last.content + timeoutNote };
              return updated;
            }
            return [...prev, {
              role: 'assistant',
              content: '⚠️ **等待逾時：長時間未收到回應。**\n\n可能原因：\n- 圖片生成中（ComfyUI 排隊）\n- 後端服務負載過高\n- 網路連線問題\n\n請稍候查看對話框是否有結果，或重新發送訊息。'
            }];
          });
        }
      }, INACTIVITY_TIMEOUT_MS);
    };

    // 立即啟動計時器（防止請求一開始就沒有回應）
    resetInactivityTimer();

    let assistantContent = '';
    let localReasoningContent = '';  // 本次回應的思考內容（存入 message 用）
    let activeAgentName = '';
    let lastPaintAt = 0;

    const yieldToBrowser = async (force = false) => {
      const now = typeof performance !== 'undefined' ? performance.now() : Date.now();
      if (!force && now - lastPaintAt < 16) return;
      lastPaintAt = now;
      await new Promise((resolve) => requestAnimationFrame(() => resolve()));
    };

    const upsertAssistantMessage = (content, thinkingContent = localReasoningContent) => {
      const derived = splitReasoningFromContent(content);
      const nextThinkingContent = thinkingContent || derived.thinkingContent;
      const nextContent = derived.thinkingContent ? derived.content : content;

      setMessages(prev => {
        const newMessages = [...prev];
        const lastMsg = newMessages[newMessages.length - 1];

        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.content = nextContent;
          if (nextThinkingContent) {
            lastMsg.thinkingContent = nextThinkingContent;
          }
          lastMsg.isStreaming = true;
        } else {
          newMessages.push({
            role: 'assistant',
            content: nextContent,
            thinkingContent: nextThinkingContent || undefined,
            isStreaming: true,
          });
        }

        return [...newMessages];
      });
    };

    const appendReasoning = (reasoningChunk) => {
      if (!reasoningChunk) return;
      localReasoningContent = mergeStreamText(localReasoningContent, reasoningChunk);
      setReasoningContent(localReasoningContent);
      setIsThinking(true);
      upsertAssistantMessage(assistantContent, localReasoningContent);
    };

    const appendAssistantContent = (contentChunk) => {
      if (!contentChunk) return;
      assistantContent = mergeStreamText(assistantContent, contentChunk);
      const derived = splitReasoningFromContent(assistantContent);
      if (!localReasoningContent && derived.thinkingContent) {
        localReasoningContent = derived.thinkingContent;
        setReasoningContent(derived.thinkingContent);
      }
      setIsThinking(Boolean(derived.thinkingContent) && !derived.content.trim());
      upsertAssistantMessage(assistantContent);
    };

    const extractToolInfo = (event) => {
      const tool = event.tool || event.data?.tool || event.tool_call || event.tool_calls?.[0] || null;
      const toolId = tool?.tool_call_id || event.tool_call_id || event.data?.tool_call_id || `${event.normalizedEvent || 'tool'}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const toolName = tool?.tool_name || tool?.name || tool?.function?.name || event.tool_name || event.data?.tool_name || 'Unknown Tool';
      const toolArgs = tool?.tool_args || tool?.args || tool?.arguments || tool?.function?.arguments || event.tool_args || event.data?.tool_args || '';
      const toolResult = tool?.result || event.result || event.content || event.data?.result || event.data?.content || '';
      const toolError = tool?.tool_call_error ? (toolResult || 'Tool call failed') : (event.error || event.message || event.data?.error || '');

      return {
        toolId,
        toolName,
        toolArgs,
        toolResult,
        toolError,
      };
    };

    try {
      // 根據模式選擇 API（傳送檔案）
      const messageStream = isTeamMode
        ? sendTeamMessage(userMessage, sessionId, abortController.signal, filesToSend)
        : sendMessage(userMessage, sessionId, selectedAgent, abortController.signal, filesToSend);

      let isFirstEvent = true;
      for await (const event of messageStream) {
        // 每收到一個事件，重置閒置計時器
        resetInactivityTimer();

        // 收到第一個事件時，後端已建立紀錄，通知側欄更新
        if (isFirstEvent && onMessageSent) {
          onMessageSent(sessionId);
          isFirstEvent = false;
        }

        console.log('Received event:', event); // Debug log

        const eventType = event.normalizedEvent || '';
        const eventContent = event.content || event.data?.content || '';
        const eventReasoning = event.reasoning_content || event.data?.reasoning_content || '';
        const eventAgentName = event.agent_name || event.member_name || event.team_name || '';

        if (eventAgentName) {
          activeAgentName = eventAgentName;
          setCurrentAgent(eventAgentName);
        }

        if (
          eventType === 'run_content' ||
          eventType === 'team_run_content' ||
          eventType === 'member_run_content' ||
          eventType === 'run_intermediate_content' ||
          eventType === 'team_run_intermediate_content'
        ) {
          if (eventReasoning && !eventContent) {
            appendReasoning(eventReasoning);
          } else {
            if (eventReasoning) {
              appendReasoning(eventReasoning);
            }
            if (eventContent) {
              appendAssistantContent(eventContent);
            }
            await yieldToBrowser();
          }
        }

        if (eventType === 'reasoning_started' || eventType === 'team_reasoning_started') {
          setIsThinking(true);
        }

        if (eventType === 'model_request_started' || eventType === 'team_model_request_started') {
          setIsThinking(true);
        }

        if (eventType === 'reasoning_content_delta' || eventType === 'team_reasoning_content_delta') {
          appendReasoning(eventReasoning || eventContent);
          await yieldToBrowser();
        }

        if (eventType === 'reasoning_completed' || eventType === 'team_reasoning_completed') {
          if (eventReasoning) {
            appendReasoning(eventReasoning);
          }
          setIsThinking(false);
        }

        if (eventType === 'model_request_completed' || eventType === 'team_model_request_completed') {
          setIsThinking(false);
        }

        // RunCompleted / TeamRunCompleted：作為非串流 reasoning model 的 fallback
        // 若整個 stream 過程中都沒有累積任何 content（如 o1/o3 不逐 token 輸出），
        // 從 RunCompleted 取完整回答
        if (eventType === 'run_completed' || eventType === 'team_run_completed') {
          setIsThinking(false);
          if (eventReasoning) {
            appendReasoning(eventReasoning);
          }
          const finalContent = eventContent;
          if (finalContent && !assistantContent) {
            appendAssistantContent(finalContent);
          } else if (assistantContent && localReasoningContent) {
            upsertAssistantMessage(assistantContent);
          }
        }

        // 錯誤事件：RunError / AgentRunError 等
        if (
          eventType === 'run_error' ||
          eventType === 'team_run_error' ||
          eventType === 'tool_call_error' ||
          eventType === 'team_tool_call_error' ||
          (eventType.includes('error') && (event.message || event.error || eventContent))
        ) {
          setIsThinking(false);
          const errMsg = event.message || event.error || eventContent || '未知錯誤';

          if (eventType === 'tool_call_error' || eventType === 'team_tool_call_error') {
            const { toolId, toolError } = extractToolInfo(event);
            setActiveTools(prev => prev.map(tool => (
              tool.id === toolId
                ? { ...tool, status: 'error', error: toolError || errMsg }
                : tool
            )));
          }

          setMessages(prev => {
            const newMessages = [...prev];
            const last = newMessages[newMessages.length - 1];
            if (last?.role === 'assistant' && last.content) {
              newMessages[newMessages.length - 1] = {
                ...last,
                content: last.content + `\n\n> ❌ **執行錯誤**：${errMsg}`,
                thinkingContent: localReasoningContent || last.thinkingContent,
              };
              return newMessages;
            }
            return [...newMessages, { role: 'assistant', content: `❌ **執行錯誤**：${errMsg}` }];
          });
        }

        // 處理工具呼叫事件
        if (eventType === 'tool_call_started' || eventType === 'team_tool_call_started') {
          const { toolId, toolName, toolArgs } = extractToolInfo(event);
          const toolAgentName = eventAgentName || activeAgentName || 'Assistant';

          setActiveTools(prev => {
            const toolArgsText = typeof toolArgs === 'string' ? toolArgs : JSON.stringify(toolArgs);
            const existingIndex = prev.findIndex(tool => tool.id === toolId);

            if (existingIndex >= 0) {
              const updated = [...prev];
              updated[existingIndex] = {
                ...updated[existingIndex],
                name: toolName,
                args: toolArgsText,
                status: 'running',
                agentName: toolAgentName,
              };
              return updated;
            }

            return [...prev, {
              id: toolId,
              name: toolName,
              args: toolArgsText,
              status: 'running',
              agentName: toolAgentName,
            }];
          });
          await yieldToBrowser();
        }

        if (eventType === 'tool_call_completed' || eventType === 'team_tool_call_completed') {
          const { toolId, toolResult } = extractToolInfo(event);
          setActiveTools(prev => prev.map(tool => (
            tool.id === toolId
              ? { ...tool, status: 'completed', result: toolResult }
              : tool
          )));
          await yieldToBrowser();
        }
      }
    } catch (error) {
      // AbortError 是我們主動觸發的（逾時 or 換題），不顯示錯誤
      if (error.name !== 'AbortError') {
        console.error('Error:', error);
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `❌ 發生錯誤：${error.message}`
        }]);
      }
    } finally {
      clearTimeout(inactivityTimerRef.current);
      setIsLoading(false);
      setIsThinking(false);
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMsg = newMessages[newMessages.length - 1];
        if (lastMsg?.role === 'assistant') {
          lastMsg.isStreaming = false;
        }
        return newMessages;
      });
    }
  };

  return (
    <div className="chat-interface">
      <header className="chat-header">
        <h1>{isTeamMode ? '👥 Creative Team' : `🤖 ${agents.find(a => a.id === selectedAgent)?.name || 'Agent'}`}</h1>
        <div className="header-controls">
          {/* Agent 選擇器 - 僅在 Agent 模式下顯示 */}
          {!isTeamMode && (
            <select
              className="agent-selector"
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
            >
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
          )}
          {/* 模式切換開關 */}
          <div className="mode-toggle">
            <span className={!isTeamMode ? 'active' : ''}>Agent</span>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={isTeamMode}
                onChange={(e) => onTeamModeChange(e.target.checked)}
              />
              <span className="slider"></span>
            </label>
            <span className={isTeamMode ? 'active' : ''}>Team</span>
          </div>
          <span className="session-id">Session: {sessionId.slice(0, 8)}...</span>
          <button onClick={handleNewSession} className="new-session-btn">
            New Session
          </button>
        </div>
      </header>

      {/* 思考中指示區塊（Reasoning Model 使用） */}
      {isLoading && (isThinking || reasoningContent) && (
        <div className="thinking-block">
          <div
            className="thinking-block-header"
            onClick={() => setThinkingExpanded(prev => !prev)}
          >
            <span className="thinking-icon">{isThinking ? '🧠' : '💭'}</span>
            <span className="thinking-title">
              {isThinking ? '正在思考中…' : '思考過程'}
            </span>
            {isThinking && (
              <span className="thinking-spinner"></span>
            )}
            <span className="thinking-toggle">{thinkingExpanded ? '▲' : '▼'}</span>
          </div>
          {thinkingExpanded && reasoningContent && (
            <div className="thinking-content">
              <pre>{reasoningContent}</pre>
            </div>
          )}
        </div>
      )}

      {currentAgent && (
        <div className="current-agent">
          <span className="agent-indicator">🎯</span>
          <span>Active Agent: {currentAgent}</span>
        </div>
      )}

      <div className="messages-container" ref={messagesContainerRef} onScroll={handleMessagesScroll}>
        {messages.length === 0 && (
          <div className="welcome-message">
            <h2>👋 Welcome{userId && userId !== 'unknown' ? `, ${userId}` : ''}!</h2>
            {userId && (
              <p className="welcome-user-badge">
                <span className="user-badge-icon">👤</span>
                {userId !== 'unknown' ? userId : '未識別使用者'}
              </p>
            )}
            {isTeamMode ? (
              <p>I'm a creative team with <strong>Research Agent</strong> and <strong>Image Generator</strong>.<br />Ask me to research topics or create images!</p>
            ) : (
              <p>Ask me anything. I can search the web to find information for you.</p>
            )}
          </div>
        )}

        {messages.map((msg, idx) => {
          // Check if this is the last message and it comes from the assistant
          const isLastAssistantMessage = idx === messages.length - 1 && msg.role === 'assistant';

          return (
            <div key={idx} className="message-wrapper">
              {/* If it's the last assistant message, render tools ABOVE it */}
              {isLastAssistantMessage && activeTools.length > 0 && (
                <ToolStatus
                  tools={activeTools}
                  onCancel={() => {
                    abortControllerRef.current?.abort();
                    clearTimeout(inactivityTimerRef.current);
                    setIsLoading(false);
                    setActiveTools([]);
                    setCurrentAgent(null);
                    setMessages(prev => {
                      const last = prev[prev.length - 1];
                      if (last?.role === 'assistant' && last.content) {
                        const updated = [...prev];
                        updated[updated.length - 1] = { ...last, content: last.content + '\n\n> ⏹ 已手動取消' };
                        return updated;
                      }
                      return [...prev, { role: 'assistant', content: '⏹ 已取消' }];
                    });
                  }}
                />
              )}
              <Message role={msg.role} content={msg.content} thinkingContent={msg.thinkingContent} isStreaming={msg.isStreaming} />
            </div>
          );
        })}

        {/* Fallback: If tools are active but there is no assistant message yet (e.g. searching before speaking) */}
        {activeTools.length > 0 && (messages.length === 0 || messages[messages.length - 1].role !== 'assistant') && (
          <ToolStatus
            tools={activeTools}
            onCancel={() => {
              abortControllerRef.current?.abort();
              clearTimeout(inactivityTimerRef.current);
              setIsLoading(false);
              setActiveTools([]);
              setCurrentAgent(null);
            }}
          />
        )}

        {isLoading && activeTools.length === 0 && messages.length > 0 && messages[messages.length - 1].role !== 'assistant' && (
          <div className="thinking">
            <span className="dot"></span>
            <span className="dot"></span>
            <span className="dot"></span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 檔案預覽區 */}
      {uploadFiles.length > 0 && (
        <div className="file-preview-bar">
          {uploadFiles.map((file, idx) => (
            <div key={idx} className="file-preview-item">
              <span className="file-preview-icon">
                {file.type.startsWith('image/') ? '🖼️' :
                 file.type.startsWith('audio/') ? '🎧' :
                 file.type.startsWith('video/') ? '🎬' :
                 file.type === 'application/pdf' ? '📄' :
                 '📎'}
              </span>
              <span className="file-preview-name" title={file.name}>
                {file.name.length > 20 ? file.name.slice(0, 17) + '...' : file.name}
              </span>
              <span className="file-preview-size">
                {(file.size / 1024).toFixed(0)}KB
              </span>
              <button
                type="button"
                className="file-preview-remove"
                onClick={() => setUploadFiles(prev => prev.filter((_, i) => i !== idx))}
                title="移除檔案"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="input-form">
        {/* 隱藏的檔案輸入框 */}
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          multiple
          accept={ACCEPTED_FILE_TYPES}
          onChange={(e) => {
            const newFiles = Array.from(e.target.files);
            if (newFiles.length > 0) {
              setUploadFiles(prev => [...prev, ...newFiles]);
            }
            // 重置 input 以便同一檔案可再次選擇
            e.target.value = '';
          }}
        />
        {/* 上傳檔案按鈕 */}
        <button
          type="button"
          className="upload-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading}
          title="上傳檔案（圖片、音訊、影片、PDF、CSV、DOCX、TXT、JSON）"
        >
          {/* 迴紙針圖示 */}
          <span className="paperclip-icon">🧷</span>
          {uploadFiles.length > 0 && (
            <span className="upload-badge">{uploadFiles.length}</span>
          )}
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={uploadFiles.length > 0 ? `已選擇 ${uploadFiles.length} 個檔案，輸入訊息…` : 'Type your message...'}
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || (!input.trim() && uploadFiles.length === 0)}>
          Send
        </button>
      </form>
    </div>
  );
});

export default ChatInterface;
