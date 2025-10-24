# Script Helper PowerShell untuk Windows

# Build Docker Image
function Build-Image {
    Write-Host "Building Docker image..." -ForegroundColor Green
    docker build -t uts-aggregator .
}

# Run Docker Container
function Run-Container {
    Write-Host "Running Docker container..." -ForegroundColor Green
    docker run -p 8080:8080 -v ${PWD}/data:/app/data --name uts-aggregator uts-aggregator
}

# Stop and Remove Container
function Stop-Container {
    Write-Host "Stopping container..." -ForegroundColor Yellow
    docker stop uts-aggregator
    docker rm uts-aggregator
}

# Run Tests
function Run-Tests {
    Write-Host "Running tests..." -ForegroundColor Green
    pytest tests/ -v
}

# Run Tests with Coverage
function Run-Coverage {
    Write-Host "Running tests with coverage..." -ForegroundColor Green
    pytest tests/ --cov=src --cov-report=html --cov-report=term
}

# Install Dependencies
function Install-Deps {
    Write-Host "Installing dependencies..." -ForegroundColor Green
    pip install -r requirements.txt
}

# Run Application Locally
function Run-Local {
    Write-Host "Running application locally..." -ForegroundColor Green
    python -m src.main
}

# Run Demo Script
function Run-Demo {
    Write-Host "Running demo script..." -ForegroundColor Green
    python demo.py
}

# Check API Health
function Check-Health {
    Write-Host "Checking API health..." -ForegroundColor Green
    curl http://localhost:8080/health
}

# Get Stats
function Get-Stats {
    Write-Host "Getting stats..." -ForegroundColor Green
    curl http://localhost:8080/stats | ConvertFrom-Json | ConvertTo-Json
}

# Docker Compose Up
function Compose-Up {
    Write-Host "Starting Docker Compose..." -ForegroundColor Green
    docker-compose up --build
}

# Docker Compose Down
function Compose-Down {
    Write-Host "Stopping Docker Compose..." -ForegroundColor Yellow
    docker-compose down
}

# Clean Up
function Clean-All {
    Write-Host "Cleaning up..." -ForegroundColor Yellow
    
    # Remove containers
    docker stop uts-aggregator 2>$null
    docker rm uts-aggregator 2>$null
    docker-compose down 2>$null
    
    # Remove data
    if (Test-Path "data") {
        Remove-Item -Recurse -Force data
    }
    
    # Remove Python cache
    Get-ChildItem -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force
    Get-ChildItem -Include *.pyc -Recurse -Force | Remove-Item -Force
    
    # Remove test cache
    if (Test-Path ".pytest_cache") {
        Remove-Item -Recurse -Force .pytest_cache
    }
    
    if (Test-Path "htmlcov") {
        Remove-Item -Recurse -Force htmlcov
    }
    
    Write-Host "Cleanup complete!" -ForegroundColor Green
}

# Help Menu
function Show-Help {
    Write-Host "`n=== UTS Aggregator Helper Script ===" -ForegroundColor Cyan
    Write-Host "`nAvailable commands:" -ForegroundColor Yellow
    Write-Host "  Build-Image        - Build Docker image"
    Write-Host "  Run-Container      - Run Docker container"
    Write-Host "  Stop-Container     - Stop and remove container"
    Write-Host "  Run-Tests          - Run unit tests"
    Write-Host "  Run-Coverage       - Run tests with coverage"
    Write-Host "  Install-Deps       - Install Python dependencies"
    Write-Host "  Run-Local          - Run application locally"
    Write-Host "  Run-Demo           - Run demo script"
    Write-Host "  Check-Health       - Check API health"
    Write-Host "  Get-Stats          - Get statistics"
    Write-Host "  Compose-Up         - Start Docker Compose"
    Write-Host "  Compose-Down       - Stop Docker Compose"
    Write-Host "  Clean-All          - Clean up everything"
    Write-Host "  Show-Help          - Show this help"
    Write-Host "`nExample usage:" -ForegroundColor Yellow
    Write-Host "  . .\helper.ps1"
    Write-Host "  Build-Image"
    Write-Host "  Run-Container"
    Write-Host ""
}

# Show help on import
Show-Help
