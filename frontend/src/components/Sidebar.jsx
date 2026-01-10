import { useState, useEffect, useCallback } from 'react';
import { getSessions, getSessionRuns, deleteSession } from '../services/api';
import './Sidebar.css';

function Sidebar({ currentSessionId, onSelectSession, onNewSession, refreshTrigger }) {
    const [sessions, setSessions] = useState([]);
    const [groupedSessions, setGroupedSessions] = useState({});
    const [expandedDates, setExpandedDates] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // 載入 sessions
    const loadSessions = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await getSessions();

            // data 可能是 { data: [...] }, { sessions: [...] } 或直接是陣列
            const sessionList = data.data || data.sessions || (Array.isArray(data) ? data : []);
            setSessions(sessionList);

            // 按日期分組
            const grouped = groupSessionsByDate(sessionList);
            setGroupedSessions(grouped);

            // 預設展開今天和昨天
            const today = formatDate(new Date());
            const yesterday = formatDate(new Date(Date.now() - 86400000));
            setExpandedDates(prev => ({
                ...prev,
                [today]: true,
                [yesterday]: true
            }));
        } catch (err) {
            console.error('Failed to load sessions:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadSessions();
    }, [loadSessions, refreshTrigger]);

    // 當 currentSessionId 變化時重新載入（新對話可能產生）
    useEffect(() => {
        if (currentSessionId) {
            // 延遲一下確保後端已儲存
            const timer = setTimeout(loadSessions, 1000);
            return () => clearTimeout(timer);
        }
    }, [currentSessionId, loadSessions]);

    // 格式化日期
    function formatDate(date) {
        const d = new Date(date);
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today.getTime() - 86400000);
        const sessionDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());

        if (sessionDate.getTime() === today.getTime()) {
            return '今天';
        } else if (sessionDate.getTime() === yesterday.getTime()) {
            return '昨天';
        } else {
            return d.toLocaleDateString('zh-TW', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
    }

    // 格式化時間
    function formatTime(date) {
        return new Date(date).toLocaleTimeString('zh-TW', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // 解析時間戳記（支援 ISO 字串和 Unix timestamp）
    function parseTimestamp(rawTime) {
        if (!rawTime) return Date.now();
        if (typeof rawTime === 'string') {
            return new Date(rawTime).getTime();
        }
        // Unix timestamp（秒）轉換為毫秒
        return rawTime * 1000;
    }

    // 按日期分組 sessions
    function groupSessionsByDate(sessions) {
        const groups = {};

        sessions.forEach(session => {
            // 嘗試從不同欄位取得時間（可能是 ISO 字串或 Unix timestamp）
            const rawTime = session.created_at || session.updated_at || Date.now();
            // 判斷是 ISO 字串還是 Unix timestamp
            const timestamp = typeof rawTime === 'string' ? new Date(rawTime).getTime() : rawTime * 1000;
            const date = formatDate(timestamp);

            if (!groups[date]) {
                groups[date] = [];
            }
            groups[date].push(session);
        });

        // 按時間排序每個群組內的 sessions（最新在前）
        Object.keys(groups).forEach(date => {
            groups[date].sort((a, b) => {
                const timeA = a.updated_at || a.created_at || 0;
                const timeB = b.updated_at || b.created_at || 0;
                return timeB - timeA;
            });
        });

        return groups;
    }

    // 取得 session 預覽文字
    function getSessionPreview(session) {
        // 嘗試從 session 資料中取得預覽
        if (session.name) return session.name;
        if (session.title) return session.title;

        // 使用 session_id 的前幾個字元
        return `對話 ${session.session_id?.slice(0, 8) || 'Unknown'}...`;
    }

    // 切換日期群組展開/收合
    const toggleDateGroup = (date) => {
        setExpandedDates(prev => ({
            ...prev,
            [date]: !prev[date]
        }));
    };

    // 處理選擇 session
    const handleSelectSession = async (session) => {
        if (onSelectSession) {
            try {
                const runs = await getSessionRuns(session.session_id);
                onSelectSession(session.session_id, runs);
            } catch (err) {
                console.error('Failed to load session runs:', err);
            }
        }
    };

    // 處理刪除 session
    const handleDeleteSession = async (e, sessionId) => {
        e.stopPropagation();
        if (!confirm('確定要刪除這個對話嗎？')) return;

        try {
            await deleteSession(sessionId);
            await loadSessions();
        } catch (err) {
            console.error('Failed to delete session:', err);
        }
    };

    // 排序日期群組（最新在前）
    const sortedDates = Object.keys(groupedSessions).sort((a, b) => {
        if (a === '今天') return -1;
        if (b === '今天') return 1;
        if (a === '昨天') return -1;
        if (b === '昨天') return 1;
        // 其他日期按時間倒序
        return new Date(b) - new Date(a);
    });

    return (
        <div className="sidebar">
            <div className="sidebar-header">
                <h2>📚 對話紀錄</h2>
                <button className="new-chat-btn" onClick={onNewSession}>
                    ✨ 新對話
                </button>
            </div>

            <div className="sidebar-content">
                {loading ? (
                    <div className="loading-sessions">
                        <div className="loading-spinner"></div>
                    </div>
                ) : error ? (
                    <div className="no-sessions">
                        <p>⚠️ 載入失敗</p>
                        <p className="hint">{error}</p>
                    </div>
                ) : sortedDates.length === 0 ? (
                    <div className="no-sessions">
                        <p>📭 尚無對話紀錄</p>
                        <p className="hint">開始一個新對話吧！</p>
                    </div>
                ) : (
                    sortedDates.map(date => (
                        <div key={date} className="date-group">
                            <div
                                className="date-header"
                                onClick={() => toggleDateGroup(date)}
                            >
                                <span className={`expand-icon ${expandedDates[date] ? 'expanded' : ''}`}>
                                    ▶
                                </span>
                                <span>📅 {date}</span>
                                <span style={{ marginLeft: 'auto', opacity: 0.6 }}>
                                    ({groupedSessions[date].length})
                                </span>
                            </div>

                            <div className={`session-list ${expandedDates[date] ? '' : 'collapsed'}`}>
                                {groupedSessions[date].map(session => (
                                    <div
                                        key={session.session_id}
                                        className={`session-item ${session.session_id === currentSessionId ? 'active' : ''}`}
                                        onClick={() => handleSelectSession(session)}
                                    >
                                        <span className="session-icon">💬</span>
                                        <div className="session-info">
                                            <div className="session-title">
                                                {getSessionPreview(session)}
                                            </div>
                                            <div className="session-preview">
                                                {session.session_id?.slice(0, 16)}...
                                            </div>
                                        </div>
                                        <span className="session-time">
                                            {formatTime(parseTimestamp(session.updated_at || session.created_at))}
                                        </span>
                                        <button
                                            className="delete-btn"
                                            onClick={(e) => handleDeleteSession(e, session.session_id)}
                                            title="刪除對話"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

export default Sidebar;
