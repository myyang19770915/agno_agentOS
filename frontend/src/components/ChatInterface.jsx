import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { sendMessage, sendTeamMessage, getSessionId, clearSession, generateSessionId, getAgents } from '../services/api';
import Message from './Message';
import ToolStatus from './ToolStatus';
import './ChatInterface.css';

const ChatInterface = forwardRef(function ChatInterface({ onSessionChange, onMessageSent }, ref) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(getSessionId());
  const [activeTools, setActiveTools] = useState([]);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [isTeamMode, setIsTeamMode] = useState(false); // Team 模式切換
  const [agents, setAgents] = useState([]);  // 可用 Agent 列表
  const [selectedAgent, setSelectedAgent] = useState('');  // 選中的 Agent ID
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const scrollTimeoutRef = useRef(null);

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
      if (force || isNearBottom()) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
      }
    }, 50); // 50ms 防抖
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeTools]);

  // 通知父元件 session 變更
  useEffect(() => {
    if (onSessionChange) {
      onSessionChange(sessionId);
    }
  }, [sessionId, onSessionChange]);

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
    const newSessionId = clearSession();
    setSessionId(newSessionId);
    localStorage.setItem('sessionId', newSessionId);
    setMessages([]);
    setActiveTools([]);
    setCurrentAgent(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);
    setActiveTools([]);
    setCurrentAgent(null);

    let assistantContent = '';

    try {
      // 根據模式選擇 API
      const messageStream = isTeamMode
        ? sendTeamMessage(userMessage, sessionId)
        : sendMessage(userMessage, sessionId, selectedAgent);

      let isFirstEvent = true;
      for await (const event of messageStream) {
        // 收到第一個事件時，後端已建立紀錄，通知側欄更新
        if (isFirstEvent && onMessageSent) {
          onMessageSent(sessionId);
          isFirstEvent = false;
        }

        console.log('Received event:', event); // Debug log

        // 處理不同類型的事件
        // Agent 模式: RunContent
        // Team 模式: TeamRunContent
        if (event.event === 'RunContent' || event.type === 'RunContent' ||
          event.event === 'TeamRunContent' || event.type === 'TeamRunContent') {
          const content = event.content || event.data?.content || '';
          assistantContent += content;
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMsg = newMessages[newMessages.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
              lastMsg.content = assistantContent;
            } else {
              newMessages.push({ role: 'assistant', content: assistantContent });
            }
            return [...newMessages];
          });

          // 顯示當前 Agent 名稱
          const agentName = event.agent_name || event.member_name || event.team_name;
          if (agentName) {
            setCurrentAgent(agentName);
          }
        }

        // 處理 Team Member 回應事件
        if (event.event === 'MemberRunContent' || event.type === 'MemberRunContent') {
          const content = event.content || '';
          assistantContent += content;
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMsg = newMessages[newMessages.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
              lastMsg.content = assistantContent;
            } else {
              newMessages.push({ role: 'assistant', content: assistantContent });
            }
            return [...newMessages];
          });

          // 顯示當前執行的 member
          if (event.member_name) {
            setCurrentAgent(event.member_name);
          }
        }

        // 處理工具呼叫事件
        // Check for both ToolCallStart (older?) and ToolCallStarted (newer/observed)
        if (event.event === 'ToolCallStart' || event.event === 'ToolCallStarted' ||
          event.type === 'ToolCallStart' || event.type === 'ToolCallStarted') {

          // Try correctly mapped Agno structure based on user feedback (event.tool.tool_name)
          const toolName = event.tool?.tool_name ||
            event.tool?.name ||
            event.tool_call?.function?.name ||
            event.tool_call?.name ||
            event.tool_calls?.[0]?.function?.name ||
            event.tool_calls?.[0]?.name ||
            event.tool_name ||
            event.data?.tool_name ||
            'Unknown Tool';

          const toolArgs = event.tool?.tool_args ||
            event.tool?.args ||
            event.tool?.arguments ||
            event.tool_call?.function?.arguments ||
            event.tool_call?.arguments ||
            event.tool_calls?.[0]?.function?.arguments ||
            event.tool_calls?.[0]?.arguments ||
            event.tool_args ||
            event.data?.tool_args ||
            '';

          // 從事件中取得 agent 名稱
          const toolAgentName = event.agent_name || currentAgent || '';

          setActiveTools(prev => [...prev, {
            name: toolName,
            args: typeof toolArgs === 'string' ? toolArgs : JSON.stringify(toolArgs),
            status: 'running',
            agentName: toolAgentName
          }]);
        }

        if (event.event === 'ToolCallEnd' || event.event === 'ToolCallCompleted' ||
          event.type === 'ToolCallEnd' || event.type === 'ToolCallCompleted') {
          setActiveTools(prev => {
            const newTools = [...prev];
            const lastTool = newTools[newTools.length - 1];
            if (lastTool) {
              lastTool.status = 'completed';
            }
            return newTools;
          });
        }

        // 處理 Agent 名稱（階段二用）
        if (event.member_name || event.agent_name) {
          setCurrentAgent(event.member_name || event.agent_name);
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message}`
      }]);
    } finally {
      setIsLoading(false);
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
                onChange={(e) => setIsTeamMode(e.target.checked)}
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

      {currentAgent && (
        <div className="current-agent">
          <span className="agent-indicator">🎯</span>
          <span>Active Agent: {currentAgent}</span>
        </div>
      )}

      <div className="messages-container" ref={messagesContainerRef}>
        {messages.length === 0 && (
          <div className="welcome-message">
            <h2>👋 Welcome!</h2>
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
                <ToolStatus tools={activeTools} />
              )}
              <Message role={msg.role} content={msg.content} />
            </div>
          );
        })}

        {/* Fallback: If tools are active but there is no assistant message yet (e.g. searching before speaking) */}
        {activeTools.length > 0 && (messages.length === 0 || messages[messages.length - 1].role !== 'assistant') && (
          <ToolStatus tools={activeTools} />
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

      <form onSubmit={handleSubmit} className="input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
});

export default ChatInterface;
