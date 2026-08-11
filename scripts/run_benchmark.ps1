# Phase 7.1 AAP Benchmark Runner
# Usage:
#   .\scripts\run_benchmark.ps1
#   .\scripts\run_benchmark.ps1 -Quick
#   .\scripts\run_benchmark.ps1 -Url http://localhost:7860
#   .\scripts\run_benchmark.ps1 -Suite phase7   # run original phase7 benchmark instead

param(
    [string]$Url     = "http://localhost:7860",
    [switch]$Quick,
    [ValidateSet("aap","phase7","both")]
    [string]$Suite   = "aap",
    [int]$Timeout    = 120   # per-query HTTP timeout in seconds; raise for CPU-only servers
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Codette Phase 7.1 Benchmark" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Server  : $Url"
Write-Host "  Suite   : $Suite"
Write-Host "  Quick   : $Quick"
Write-Host "  Timeout : ${Timeout}s per query"
Write-Host ""

# Check server is up
Write-Host "Checking server..." -NoNewline
# 2026-08-10: this probed $Url/health, which 404s — the route is /api/health.
# Worse, -ErrorAction SilentlyContinue suppressed the error INSIDE the try, so
# the catch never ran: the check printed nothing, the /api/status fallback was
# dead code, and the script charged on even with the server down. Probe the real
# route and let the error reach the catch.
try {
    $resp = Invoke-WebRequest -Uri "$Url/api/health" -TimeoutSec 5 -UseBasicParsing
    if ($resp.StatusCode -eq 200) { Write-Host " OK" -ForegroundColor Green }
    else { throw "unexpected status $($resp.StatusCode)" }
} catch {
    try {
        $resp = Invoke-WebRequest -Uri "$Url/api/status" -TimeoutSec 5 -UseBasicParsing
        Write-Host " OK (via /api/status)" -ForegroundColor Green
    } catch {
        Write-Host " UNREACHABLE" -ForegroundColor Red
        Write-Host ""
        Write-Host "Server not responding at $Url" -ForegroundColor Red
        Write-Host "Start it with:  python inference\codette_server.py" -ForegroundColor Yellow
        exit 1
    }
}

# Run selected suite(s)
$exitCode = 0

if ($Suite -eq "aap" -or $Suite -eq "both") {
    Write-Host ""
    Write-Host "Running Phase 7.1 AAP benchmark..." -ForegroundColor Cyan
    $args = @("benchmarks\phase71_aap_benchmark.py", "--url", $Url, "--timeout", $Timeout)
    if ($Quick) { $args += "--quick" }
    python @args
    if ($LASTEXITCODE -ne 0) { $exitCode = $LASTEXITCODE }
}

if ($Suite -eq "phase7" -or $Suite -eq "both") {
    Write-Host ""
    Write-Host "Running Phase 7 benchmark..." -ForegroundColor Cyan
    python benchmarks\phase7_benchmark.py
    if ($LASTEXITCODE -ne 0) { $exitCode = $LASTEXITCODE }
}

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "Benchmark complete." -ForegroundColor Green
} else {
    Write-Host "Benchmark finished with errors (exit $exitCode)." -ForegroundColor Yellow
}

exit $exitCode
