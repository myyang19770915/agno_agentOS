@echo off
echo ========================================
echo   Research Agent Application
echo ========================================
echo.
echo Starting Backend (Port 7777)...
start cmd /k \"cd backend && python main.py\"
echo.
echo Waiting for backend to start...
timeout /t 5
echo.
echo Starting Frontend (Port 3000)...
start cmd /k \"cd frontend && npm run dev\"
echo.
echo ========================================
echo   Application Started!
echo ========================================
echo.
echo Backend API: http://localhost:7777
echo Frontend UI: http://localhost:3000
echo API Docs: http://localhost:7777/docs
echo.
pause
