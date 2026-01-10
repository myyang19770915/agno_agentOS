# Agno AgentOS - 一鍵啟動 (PowerShell)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🚀 Agno AgentOS - 一鍵啟動" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 取得腳本所在目錄
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 檢查虛擬環境
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "❌ 找不到虛擬環境，請先執行: uv venv" -ForegroundColor Red
    exit 1
}

Write-Host "[1/3] 🎨 啟動 Image Agent (port 9999)..." -ForegroundColor Yellow
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "Set-Location '$scriptDir'; .\.venv\Scripts\Activate.ps1; cd backend; python image_agent.py" -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "[2/3] 🤖 啟動 Main AgentOS (port 7777)..." -ForegroundColor Yellow
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "Set-Location '$scriptDir'; .\.venv\Scripts\Activate.ps1; cd backend; python main.py" -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "[3/3] 🌐 啟動 Frontend (port 3001)..." -ForegroundColor Yellow
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "Set-Location '$scriptDir'; cd frontend; npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✅ 所有服務已啟動！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 服務位址:" -ForegroundColor White
Write-Host "   - Frontend:    http://localhost:3001" -ForegroundColor Gray
Write-Host "   - Main API:    http://localhost:7777/docs" -ForegroundColor Gray
Write-Host "   - Image Agent: http://localhost:9999/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 提示: 關閉此視窗不會停止服務" -ForegroundColor DarkYellow
Write-Host "   要停止服務，請關閉各個服務的 PowerShell 視窗" -ForegroundColor DarkYellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "按 Enter 鍵關閉此視窗"
