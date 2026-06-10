Write-Host "Starting docker-compose..." -ForegroundColor Cyan
docker compose up -d --build

Write-Host "Waiting for services to become active..." -ForegroundColor Gray
$maxRetries = 40
$retryInterval = 5
$success = $false

for ($i = 1; $i -le $maxRetries; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000/" -Method Get -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $success = $true
            break
        }
    } catch {
    }
    Write-Host "  Waiting for frontend to respond... ($i/$maxRetries)" -ForegroundColor Gray
    Start-Sleep -Seconds $retryInterval
}

if (-not $success) {
    Write-Warning "Timeout: Services did not become healthy within $($maxRetries * $retryInterval) seconds."
    docker compose down
    exit 1
}

$exitCode = 0
try {
    python test_endpoints.py "localhost:3000"
    $exitCode = $LASTEXITCODE
} catch {
    $exitCode = 1
}

Write-Host "Tearing down TrafficSense stack..." -ForegroundColor Gray
docker compose down

if ($exitCode -eq 0) {
    Write-Host "SUCCESS: All live endpoints checked successfully!" -ForegroundColor Green
} else {
    Write-Warning "FAILURE: Endpoint checks failed (Exit Code: $exitCode)."
}

exit $exitCode
