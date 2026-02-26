#!/bin/bash

# ============================================================
# Agno AgentOS — 一鍵部署腳本
# ============================================================
# 後端 Backend:  port 8013, root_path /agentapi
# 前端 Frontend: port 8014, base /agentplatform
# Image Agent:   port 9999 (內部服務，不對外)
# ============================================================

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "============================================================"
echo -e "${BLUE}🚀 Agno AgentOS — 一鍵部署${NC}"
echo "============================================================"
echo ""
echo -e "${BLUE}📋 部署設定:${NC}"
echo "    Backend  → port 8013, root_path /agentapi"
echo "    Frontend → port 8014, base /agentplatform"
echo "    Image    → port 9999 (internal)"
echo ""

# 檢查虛擬環境
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ 找不到虛擬環境，請先執行: uv venv && uv pip install -r requirements.txt${NC}"
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

# 函數：清理舊進程
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 正在停止所有服務...${NC}"
    pkill -f 'python image_agent.py' 2>/dev/null
    pkill -f 'python main.py' 2>/dev/null
    pkill -f 'npm run dev' 2>/dev/null
    pkill -f 'vite' 2>/dev/null
    echo -e "${GREEN}✅ 所有服務已停止${NC}"
    exit 0
}

# 捕捉 Ctrl+C 信號
trap cleanup SIGINT SIGTERM

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

# ============================================================
# 步驟 0: 前端 Build（生產模式）
# ============================================================
echo -e "${YELLOW}[0/3] 📦 建置前端靜態資源...${NC}"
if [ -d "frontend" ]; then
    cd frontend
    npm install --silent 2>/dev/null
    npm run build 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}    ✓ 前端建置完成 (dist/)${NC}"
    else
        echo -e "${YELLOW}    ⚠️  前端建置失敗，將使用 dev 模式${NC}"
    fi
    cd ..
fi
echo ""

# ============================================================
# 步驟 1: 啟動 Image Agent (port 9999)
# ============================================================
echo -e "${YELLOW}[1/3] 🎨 啟動 Image Agent (port 9999)...${NC}"
start_service "Image Agent" "9999" "cd backend && python image_agent.py"

# ============================================================
# 步驟 2: 啟動 Main AgentOS (port 8013)
# ============================================================
echo -e "${YELLOW}[2/3] 🤖 啟動 Main AgentOS (port 8013, root_path=/agentapi)...${NC}"
start_service "Main AgentOS" "8013" "cd backend && python main.py"

# ============================================================
# 步驟 3: 啟動 Frontend (port 8014)
# ============================================================
echo -e "${YELLOW}[3/3] 🌐 啟動 Frontend (port 8014, base=/agentplatform)...${NC}"
start_service "Frontend" "8014" "cd frontend && npm run dev"

echo ""
echo "============================================================"
echo -e "${GREEN}✅ 所有服務已啟動！${NC}"
echo "============================================================"
echo ""
echo -e "${BLUE}📍 服務位址:${NC}"
echo "    - Frontend:    http://localhost:8014/agentplatform"
echo "    - Main API:    http://localhost:8013/agentapi/docs"
echo "    - Image Agent: http://localhost:9999/docs"
echo ""
echo -e "${BLUE}📍 反向代理設定（Nginx）:${NC}"
echo "    location /agentplatform/ → http://localhost:8014  (前端+API proxy)"
echo "    （API 請求 /agentplatform/api/ 由 Vite dev proxy 轉發到 :8013）"
echo ""
echo -e "${BLUE}📍 生產環境 Nginx 設定（兩條規則）:${NC}"
echo "    location /agentplatform/api/ → http://localhost:8013  (後端 API)"
echo "    location /agentplatform/     → 靜態資源 or http://localhost:8014"
echo ""
echo -e "${YELLOW}💡 提示:${NC}"
echo "    查看執行中的程序: ps aux | grep 'python\|vite'"
echo "    停止所有服務: 按 Ctrl+C 或執行:"
echo "      pkill -f 'python main.py|python image_agent.py|npm run dev'"
echo "    查看日誌: tail -f nohup.out"
echo "============================================================"
echo ""

# 保持腳本運行，按 Ctrl+C 可以停止
echo -e "${GREEN}服務正在後台運行，按 Ctrl+C 結束所有服務${NC}"
wait
