import { useState, useMemo } from 'react';
import './ToolStatus.css';

function ToolStatus({ tools }) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  // 根據 agent 分組工具呼叫
  const groupedByAgent = useMemo(() => {
    const groups = {};
    tools.forEach(tool => {
      const agentName = tool.agentName || 'Unknown Agent';
      if (!groups[agentName]) {
        groups[agentName] = [];
      }
      groups[agentName].push(tool);
    });
    return groups;
  }, [tools]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return '⏳';
      case 'completed':
        return '✅';
      case 'error':
        return '❌';
      default:
        return '🔧';
    }
  };

  // 不同 Agent 使用不同的圖示
  const getAgentIcon = (agentName) => {
    const name = agentName.toLowerCase();
    if (name.includes('research')) {
      return '🔍'; // 研究員
    } else if (name.includes('image') || name.includes('generator')) {
      return '🎨'; // 圖像生成
    } else if (name.includes('writer') || name.includes('content')) {
      return '✍️'; // 寫作
    } else if (name.includes('code') || name.includes('developer')) {
      return '💻'; // 程式開發
    } else if (name.includes('analyst') || name.includes('data')) {
      return '📊'; // 數據分析
    } else {
      return '🤖'; // 預設
    }
  };

  // 獲取 Agent 的整體狀態
  const getAgentStatus = (agentTools) => {
    if (agentTools.some(t => t.status === 'running')) return 'running';
    if (agentTools.some(t => t.status === 'error')) return 'error';
    if (agentTools.every(t => t.status === 'completed')) return 'completed';
    return 'pending';
  };

  const agentNames = Object.keys(groupedByAgent);
  const totalTools = tools.length;
  const completedTools = tools.filter(t => t.status === 'completed').length;

  return (
    <div className="tool-status">
      <div
        className="tool-status-header"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <span className="header-left">
          <span className="tool-icon">👥</span>
          <span>Agent 任務指派</span>
          <span className="task-count">({completedTools}/{totalTools})</span>
        </span>
        <span className={`collapse-icon ${isCollapsed ? 'collapsed' : ''}`}>
          ▼
        </span>
      </div>

      {!isCollapsed && (
        <div className="agent-list">
          {agentNames.map((agentName, agentIndex) => {
            const agentTools = groupedByAgent[agentName];
            const agentStatus = getAgentStatus(agentTools);
            const agentIcon = getAgentIcon(agentName);

            return (
              <div key={agentIndex} className={`agent-group ${agentStatus}`}>
                <div className="agent-header">
                  <span className="agent-icon">{agentIcon}</span>
                  <span className="agent-name">{agentName}</span>
                  <span className="agent-task-count">
                    {agentTools.filter(t => t.status === 'completed').length}/{agentTools.length}
                  </span>
                </div>
                <div className="tool-list">
                  {agentTools.map((tool, toolIndex) => (
                    <div key={toolIndex} className={`tool-item ${tool.status}`}>
                      <span className="status-icon">{getStatusIcon(tool.status)}</span>
                      <div className="tool-info">
                        <span className="tool-name">{tool.name}</span>
                        {tool.args && (
                          <span className="tool-args">
                            {tool.args.length > 80
                              ? tool.args.substring(0, 80) + '...'
                              : tool.args}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default ToolStatus;
