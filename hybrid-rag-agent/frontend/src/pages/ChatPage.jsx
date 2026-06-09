import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Box,
  Chip,
  IconButton,
  InputAdornment,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AddCommentIcon from '@mui/icons-material/AddComment';
import ChatMessage from '../components/ChatMessage';
import { streamChat } from '../api';

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const cancelRef = useRef(null);
  const bottomRef = useRef(null);
  // 每個 ChatPage 實例維持同一個 session_id，確保對話歷史連貫
  const sessionIdRef = useRef(crypto.randomUUID());

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || sending) return;

    setInput('');
    setSending(true);

    // Add user message
    const userMsg = { id: Date.now(), role: 'user', content: text };
    // Add placeholder assistant message
    const assistantId = Date.now() + 1;
    const assistantMsg = {
      id: assistantId,
      role: 'assistant',
      content: '',
      toolSteps: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    const cancel = streamChat(text, sessionIdRef.current, (event) => {
      setMessages((prev) => {
        const msgs = [...prev];
        const idx = msgs.findIndex((m) => m.id === assistantId);
        if (idx === -1) return msgs;
        const current = { ...msgs[idx] };

        switch (event.type) {
          case 'tool_start': {
            const steps = [...(current.toolSteps || [])];
            steps.push({
              tool_call_id: event.data.tool_call_id,
              tool_name: event.data.tool_name,
              tool_args: event.data.tool_args,
              status: 'running',
              result: null,
            });
            current.toolSteps = steps;
            break;
          }
          case 'tool_done': {
            const steps = (current.toolSteps || []).map((s) =>
              s.tool_call_id === event.data.tool_call_id
                ? { ...s, status: 'done', result: event.data.result }
                : s
            );
            current.toolSteps = steps;
            break;
          }
          case 'content': {
            current.content = (current.content || '') + (event.data.delta || '');
            break;
          }
          case 'done': {
            current.isStreaming = false;
            setSending(false);
            break;
          }
          case 'error': {
            current.content = (current.content || '') + `\n\n⚠️ 錯誤：${event.data.message}`;
            current.isStreaming = false;
            setSending(false);
            break;
          }
          default:
            break;
        }

        msgs[idx] = current;
        return msgs;
      });
    });

    cancelRef.current = cancel;
  }, [input, sending]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewConversation = useCallback(() => {
    if (cancelRef.current) cancelRef.current();
    sessionIdRef.current = crypto.randomUUID();
    setMessages([]);
    setInput('');
    setSending(false);
  }, []);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <Box sx={{ px: 3, py: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" fontWeight={700}>
            Agent 對話
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.3 }}>
            <Typography variant="caption" color="text.secondary">
              支援 SQL 統計分析 · 混合語意檢索 · 工具呼叫即時顯示
            </Typography>
            <Chip
              label={`session: ${sessionIdRef.current.slice(0, 8)}…`}
              size="small"
              variant="outlined"
              sx={{ height: 18, fontSize: 10, fontFamily: 'monospace' }}
            />
          </Box>
        </Box>
        <Tooltip title="新對話（清除歷史）">
          <span>
            <IconButton onClick={handleNewConversation} disabled={sending}>
              <AddCommentIcon />
            </IconButton>
          </span>
        </Tooltip>
      </Box>

      {/* Messages */}
      <Box sx={{ flex: 1, overflow: 'auto', px: 3, py: 2 }}>
        {messages.length === 0 && (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', opacity: 0.4 }}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h5" gutterBottom>🤖</Typography>
              <Typography>
                輸入你的問題開始對話
              </Typography>
              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                例如：「統計各 branch 的文件數」或「搜尋有關 RAG 的內容」
              </Typography>
            </Box>
          </Box>
        )}
        {messages.map((msg) => (
          <ChatMessage key={msg.id} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </Box>

      {/* Input */}
      <Box sx={{ px: 3, py: 2, borderTop: 1, borderColor: 'divider' }}>
        <TextField
          fullWidth
          multiline
          maxRows={4}
          placeholder="輸入訊息… (Enter 送出，Shift+Enter 換行)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={sending}
          slotProps={{
            input: {
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    color="primary"
                    onClick={handleSend}
                    disabled={!input.trim() || sending}
                  >
                    <SendIcon />
                  </IconButton>
                </InputAdornment>
              ),
            },
          }}
          sx={{
            '& .MuiOutlinedInput-root': { borderRadius: 3 },
          }}
        />
      </Box>
    </Box>
  );
}
