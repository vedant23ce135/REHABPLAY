# Rehab Games Platform Launcher
# Quick start script for the platform

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🏥 REHAB GAMES PLATFORM LAUNCHER    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Choose how to run the platform:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Web Version (Recommended) - Open in browser" -ForegroundColor Green
Write-Host "  2. Flask Server - Run Python backend" -ForegroundColor Yellow
Write-Host "  3. Exit" -ForegroundColor Red
Write-Host ""

$choice = Read-Host "Enter your choice (1-3)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Starting web server..." -ForegroundColor Green
        Write-Host "Opening browser at http://localhost:8000" -ForegroundColor Cyan
        Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
        Write-Host ""
        
        # Change to web_platform directory
        Set-Location -Path "web_platform"
        
        # Start HTTP server and open browser
        Start-Process "http://localhost:8000"
        python -m http.server 8000
    }
    "2" {
        Write-Host ""
        Write-Host "Checking Python dependencies..." -ForegroundColor Green
        
        # Check if requirements are installed
        $pip_check = pip list 2>&1
        
        if ($pip_check -notmatch "flask") {
            Write-Host "Installing required packages..." -ForegroundColor Yellow
            pip install -r requirements.txt
        }
        
        Write-Host ""
        Write-Host "Starting Flask server..." -ForegroundColor Green
        Write-Host "Opening browser at http://localhost:5000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
        Write-Host ""
        
        # Start Flask and open browser
        Start-Process "http://localhost:5000"
        python flask_server.py
    }
    "3" {
        Write-Host ""
        Write-Host "Goodbye! 👋" -ForegroundColor Cyan
        exit
    }
    default {
        Write-Host ""
        Write-Host "Invalid choice. Please run the script again." -ForegroundColor Red
    }
}
