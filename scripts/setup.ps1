<#
.SYNOPSIS
Initializes the Building Knowledge Intelligence System environment.

.DESCRIPTION
This script sets up the local development environment by checking dependencies,
copying the .env file, and providing next steps.
#>

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Building Knowledge Intelligence System " -ForegroundColor Cyan
Write-Host " First-Time Setup Wizard                " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check for Docker
Write-Host "[1/3] Checking dependencies..." -ForegroundColor Yellow
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "  ✓ Docker is installed." -ForegroundColor Green
} else {
    Write-Host "  ✗ Docker is not installed. Please install Docker Desktop to continue." -ForegroundColor Red
    exit 1
}

if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    Write-Host "  ✓ docker-compose is installed." -ForegroundColor Green
} else {
    Write-Host "  ! docker-compose is missing. Docker Compose v2 (docker compose) will be used." -ForegroundColor DarkYellow
}

# 2. Setup Environment Variables
Write-Host "`n[2/3] Setting up environment variables..." -ForegroundColor Yellow
if (-Not (Test-Path ".env")) {
    Copy-Item ".env.example" -Destination ".env"
    Write-Host "  ✓ Created .env file from template." -ForegroundColor Green
    Write-Host "  ! IMPORTANT: Please edit .env and insert your GROQ_API_KEY before starting." -ForegroundColor Magenta
} else {
    Write-Host "  ✓ .env file already exists." -ForegroundColor Green
}

# 3. Create necessary local directories
Write-Host "`n[3/3] Creating local directories..." -ForegroundColor Yellow
$dirs = @("backend/uploads", "backend/chroma_data")
foreach ($dir in $dirs) {
    if (-Not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Host "  ✓ Created $dir" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Directory $dir already exists" -ForegroundColor Green
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Setup Complete!                        " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Edit the .env file and add your API keys."
Write-Host "2. Run .\scripts\start-docker.ps1 to launch the system."
Write-Host ""
