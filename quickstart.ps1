# Quick Start Script for Geopolitical Risk Analysis System
# Run this script to check prerequisites and get setup instructions

Write-Host "`n===================================================================" -ForegroundColor Cyan
Write-Host "  AI System for Predicting Geopolitical Risk - Quick Start" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan

# Check Python
Write-Host "`n[1/3] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python not found. Please install Python 3.9+ from https://www.python.org/" -ForegroundColor Red
    exit 1
}

# Check PostgreSQL
Write-Host "`n[2/3] Checking PostgreSQL..." -ForegroundColor Yellow
try {
    $pgVersion = psql --version 2>&1
    Write-Host "  ✓ PostgreSQL found: $pgVersion" -ForegroundColor Green
} catch {
    Write-Host "  ! PostgreSQL not found in PATH" -ForegroundColor Yellow
    Write-Host "    Please ensure PostgreSQL is installed and accessible" -ForegroundColor Yellow
}

# Check MongoDB
Write-Host "`n[3/3] Checking MongoDB..." -ForegroundColor Yellow
try {
    $mongoVersion = mongod --version 2>&1 | Select-String "version" | Select-Object -First 1
    Write-Host "  ✓ MongoDB found: $mongoVersion" -ForegroundColor Green
} catch {
    Write-Host "  ! MongoDB not found in PATH" -ForegroundColor Yellow
    Write-Host "    Please ensure MongoDB is installed and running" -ForegroundColor Yellow
}

# Check if .env exists
Write-Host "`n[Config] Checking configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  ✓ .env file exists" -ForegroundColor Green
} else {
    Write-Host "  ! .env file not found" -ForegroundColor Yellow
    Write-Host "    Creating from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "  ✓ Created .env - Please edit it with your database credentials" -ForegroundColor Green
}

# Instructions
Write-Host "`n===================================================================" -ForegroundColor Cyan
Write-Host "  NEXT STEPS" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan

Write-Host "`n1. Install Python dependencies:" -ForegroundColor White
Write-Host "   pip install -r requirements.txt" -ForegroundColor Gray

Write-Host "`n2. Configure your .env file with database credentials" -ForegroundColor White
Write-Host "   Edit the .env file and set:" -ForegroundColor Gray
Write-Host "   - POSTGRES_PASSWORD" -ForegroundColor Gray
Write-Host "   - ACLED_API_KEY (optional)" -ForegroundColor Gray

Write-Host "`n3. Create PostgreSQL database:" -ForegroundColor White
Write-Host "   psql -U postgres -c `"CREATE DATABASE geopolitical_risk;`"" -ForegroundColor Gray

Write-Host "`n4. Initialize database schema:" -ForegroundColor White
Write-Host "   python setup_db.py" -ForegroundColor Gray

Write-Host "`n5. Run the pipeline:" -ForegroundColor White
Write-Host "   python run_pipeline.py" -ForegroundColor Gray

Write-Host "`n6. Start the API server:" -ForegroundColor White
Write-Host "   python run_api.py" -ForegroundColor Gray

Write-Host "`n===================================================================" -ForegroundColor Cyan
Write-Host "  For detailed instructions, see SETUP_GUIDE.md" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan

Write-Host "`nPress any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
