<#
.SYNOPSIS
Starts the Docker Compose stack for the system.
#>

Write-Host "Starting Building Knowledge Intelligence System via Docker Compose..." -ForegroundColor Cyan

# Check if docker-compose is available, otherwise use docker compose
if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    docker-compose up -d --build
} else {
    docker compose up -d --build
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nAll containers started successfully." -ForegroundColor Green
    Write-Host "`nServices:"
    Write-Host "  - Frontend: http://localhost:5173"
    Write-Host "  - Backend API (Swagger): http://localhost:8000/docs"
    Write-Host "  - System Health: http://localhost:8000/api/v1/health/system"
    Write-Host "  - Neo4j Browser: http://localhost:7474"
    Write-Host ""
    Write-Host "To view backend logs in real-time, run:"
    Write-Host "  docker logs -f infra_backend" -ForegroundColor Yellow
} else {
    Write-Host "`nFailed to start containers. Please check Docker logs." -ForegroundColor Red
}
