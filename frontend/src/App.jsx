import { useState, useRef, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatInterface from './components/ChatInterface'
import { initUser, getUserId } from './services/userContext'
import './App.css'

function App() {
  const chatRef = useRef(null);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sessionRefreshTrigger, setSessionRefreshTrigger] = useState(0);
  const [isTeamMode, setIsTeamMode] = useState(false); // 提升到 App 層
  const [userId, setUserId] = useState(null);

  // 一進入頁面即向父視窗請求使用者資訊
  useEffect(() => {
    initUser(5000).then((emplid) => {
      setUserId(emplid);
      console.log('[App] userId resolved:', emplid);
    });
  }, []);

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
        isTeamMode={isTeamMode}
        userId={userId}
      />
      <ChatInterface
        ref={chatRef}
        onSessionChange={handleSessionChange}
        onMessageSent={handleMessageSent}
        isTeamMode={isTeamMode}
        onTeamModeChange={setIsTeamMode}
        userId={userId}
      />
    </div>
  )
}

export default App
