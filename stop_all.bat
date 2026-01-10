@echo off
chcp 65001 >nul
title Agno AgentOS - Stop All

echo ============================================================
echo 🛑 Agno AgentOS - 停止所有服務
echo ============================================================
echo.

echo 正在停止 Python 服務...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Image Agent*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Main AgentOS*" 2>nul

echo 正在停止 Node 服務...
taskkill /F /IM node.exe /FI "WINDOWTITLE eq Frontend*" 2>nul

echo.
echo ✅ 已嘗試停止所有服務
echo.
pause
