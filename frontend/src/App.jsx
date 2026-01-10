import { useState, useRef } from 'react'
import Sidebar from './components/Sidebar'
import ChatInterface from './components/ChatInterface'
import './App.css'

function App() {
  const chatRef = useRef(null);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sessionRefreshTrigger, setSessionRefreshTrigger] = useState(0);

  // 處理從側欄選擇 session
  const handleSelectSession = (sessionId, runs) => {
    setCurrentSessionId(sessionId);
    if (chatRef.current) {
      chatRef.current.loadSession(sessionId, runs);
    }
  };

  // 處理新對話
  const handleNewSession = () => {
    if (chatRef.current) {
      chatRef.current.startNewSession();
    }
  };

  // 處理 session 變更（從 ChatInterface 傳回）
  const handleSessionChange = (sessionId) => {
    setCurrentSessionId(sessionId);
  };

  // 處理訊息發送（通知側欄重新整理）
  const handleMessageSent = () => {
    setSessionRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="app">
      <Sidebar
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        refreshTrigger={sessionRefreshTrigger}
      />
      <ChatInterface
        ref={chatRef}
        onSessionChange={handleSessionChange}
        onMessageSent={handleMessageSent}
      />
    </div>
  )
}

export default App
