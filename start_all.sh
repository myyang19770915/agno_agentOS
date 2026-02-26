#!/bin/bash

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "============================================================"
echo -e "${BLUE}🚀 Agno AgentOS - 一鍵啟動${NC}"
echo "============================================================"
echo ""

# 檢查虛擬環境
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ 找不到虛擬環境，請先執行: uv venv${NC}"
    exit 1
fi

# 啟動虛擬環境
source .venv/bin/activate

# 檢查 Python 是否可用
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python 找不到，請檢查虛擬環境${NC}"
    exit 1
fi

# 檢查 Node.js（用於前端）
if ! command -v npm &> /dev/null; then
    echo -e "${YELLOW}⚠️  npm 找不到，前端可能無法啟動${NC}"
fi

# 函數：檢查端口是否可用
wait_for_port() {
    local port=$1
    local max_attempts=30
    local attempt=0
    
    echo -e "${BLUE}    ⏳ 等待端口 $port 就緒...${NC}"
    
    while [ $attempt -lt $max_attempts ]; do
        python3 -c "import socket; s = socket.socket(); s.connect(('localhost', $port)); s.close()" 2>/dev/null && {
            echo -e "${GREEN}    ✓ 端口 $port 已就緒${NC}"
            return 0
        }
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    
    echo ""
    echo -e "${YELLOW}    ⚠️  端口 $port 未於預期時間內就緒（可能正在初始化）${NC}"
    return 1
}

# 函數：啟動服務並等待就緒
start_service() {
    local name=$1
    local port=$2
    local command=$3
    
    echo -e "${BLUE}[*] 🎯 啟動 $name (port $port)...${NC}"
    eval "$command" &
    local pid=$!
    echo -e "${GREEN}    ✓ PID: $pid${NC}"
    
    # 等待服務就緒
    wait_for_port $port
}

echo -e "${YELLOW}[1/3] 🎨 啟動 Image Agent (port 9999)...${NC}"
start_service "Image Agent" "9999" "cd backend && python image_agent.py"

echo -e "${YELLOW}[2/3] 🤖 啟動 Main AgentOS (port 7777)...${NC}"
start_service "Main AgentOS" "7777" "cd backend && python main.py"

echo -e "${YELLOW}[3/3] 🌐 啟動 Frontend (port 3001)...${NC}"
start_service "Frontend" "3001" "cd frontend && npm run dev"

echo ""
echo "============================================================"
echo -e "${GREEN}✅ 所有服務已啟動！${NC}"
echo "============================================================"
echo ""
echo -e "${BLUE}📍 服務位址:${NC}"
echo "    - Frontend:    http://localhost:3001"
echo "    - Main API:    http://localhost:7777/docs"
echo "    - Image Agent: http://localhost:9999/docs"
echo ""
echo -e "${YELLOW}💡 提示:${NC}"
echo "    查看執行中的程序: ps aux | grep python"
echo "    停止所有服務: pkill -f 'python main.py\\|python image_agent.py\\|npm run dev'"
echo "    查看日誌: tail -f nohup.out"
echo "============================================================"
echo ""

# 保持腳本運行，按 Ctrl+C 可以停止
echo -e "${GREEN}服務正在後台運行，按 Ctrl+C 結束此腳本${NC}"
wait
