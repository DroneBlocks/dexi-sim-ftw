# DEXI Simulation Quickstart Script (PowerShell)
# Support: https://github.com/DroneBlocks/dexi-sim-ftw

Write-Host "🚀 Starting DEXI Simulation Quickstart..." -ForegroundColor Cyan

# 1. Check for Docker
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker not found. Please install Docker Desktop first." -ForegroundColor Red
    Exit 1
}

Write-Host "✅ Docker detected." -ForegroundColor Green

# 2. Warning about WSL (if running on Windows host)
if ($IsWindows) {
    Write-Host "⚠️  Note: If you are running on Windows, we STRONGLY recommend using WSL2." -ForegroundColor Yellow
    Write-Host "   If you encounter permission errors with Node-RED, please run 'quickstart.sh' inside WSL." -ForegroundColor Yellow
}

# 3. Start Services
Write-Host "🐳 Starting containers with Docker Compose..." -ForegroundColor Cyan
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker Compose failed to start." -ForegroundColor Red
    Exit $LASTEXITCODE
}

# 4. Show Status
Write-Host ""
Write-Host "🎉 Simulation is running!" -ForegroundColor Green
Write-Host "---------------------------------------------------" -ForegroundColor Gray
Write-Host "🌍 Unity City:      http://localhost:1337"
Write-Host "🕹️  Ground Control:  http://localhost"
Write-Host "🧠 Node-RED:        http://localhost:1880"
Write-Host "💻 VNC Desktop:     http://localhost:6080"
Write-Host "---------------------------------------------------" -ForegroundColor Gray
Write-Host "To stop: docker compose down" -ForegroundColor Cyan
