@echo off
chcp 65001 >nul
title Agno AgentOS - One Click Start

echo ============================================================
echo 🚀 Agno AgentOS - 一鍵啟動
echo ============================================================
echo.

:: 檢查虛擬環境
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ 找不到虛擬環境，請先執行: uv venv
    pause
    exit /b 1
)

:: 啟動虛擬環境
call .venv\Scripts\activate.bat

echo [1/3] 🎨 啟動 Image Agent (port 9999)...
start "Image Agent" cmd /k "cd backend && python image_agent.py"
timeout /t 3 /nobreak >nul

echo [2/3] 🤖 啟動 Main AgentOS (port 7777)...
start "Main AgentOS" cmd /k "cd backend && python main.py"
timeout /t 3 /nobreak >nul

echo [3/3] 🌐 啟動 Frontend (port 3001)...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================================
echo ✅ 所有服務已啟動！
echo ============================================================
echo.
echo 📍 服務位址:
echo    - Frontend:    http://localhost:3001
echo    - Main API:    http://localhost:7777/docs
echo    - Image Agent: http://localhost:9999/docs
echo.
echo 💡 提示: 關閉此視窗不會停止服務
echo    要停止服務，請關閉各個服務的命令視窗
echo ============================================================
echo.
pause
