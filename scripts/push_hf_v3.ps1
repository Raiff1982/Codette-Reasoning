<#
Push Codette v3.0 model artifacts to Hugging Face.

PREREQUISITE (one-time, interactive — do this first in your terminal):
    hf auth login          # paste a WRITE token when prompted

Then run:
    pwsh scripts\push_hf_v3.ps1

Pushes:
  1. OpenVINO INT4 model  -> NEW repo Raiff1982/codette-llama-3.1-8b-openvino
  2. safetensors adapters -> existing Raiff1982/codette-lora-adapters (safetensors/ folder)

Idempotent: re-running only uploads changed files.
#>

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# ── Verify auth ──────────────────────────────────────────────────────────────
$who = (hf auth whoami 2>&1) -join "`n"
if ($LASTEXITCODE -ne 0 -or $who -match "Not logged in") {
    Write-Host "ERROR: hf CLI is not authenticated." -ForegroundColor Red
    Write-Host "Run 'hf auth login' with a WRITE token first, then re-run this script."
    exit 1
}
Write-Host "Authenticated as: $who" -ForegroundColor Green

$OV_REPO = "Raiff1982/codette-llama-3.1-8b-openvino"
$ADAPTER_REPO = "Raiff1982/codette-lora-adapters"
$OV_DIR = Join-Path $root "openvino_backend\llama-3.1-8b-instruct-int4"
$ADAPTER_DIR = Join-Path $root "behavioral_safetensors"

# ── 1. OpenVINO INT4 model ───────────────────────────────────────────────────
if (-not (Test-Path (Join-Path $OV_DIR "openvino_model.xml"))) {
    Write-Host "ERROR: OV model not found at $OV_DIR" -ForegroundColor Red
    exit 1
}
Write-Host "`n[1/2] Creating repo $OV_REPO (if needed) and uploading INT4 model (~4.4GB)..." -ForegroundColor Cyan
hf repo create $OV_REPO --repo-type model -y 2>&1 | Out-Host
hf upload $OV_REPO $OV_DIR . --repo-type model 2>&1 | Out-Host

# ── 2. safetensors adapters ──────────────────────────────────────────────────
Write-Host "`n[2/2] Uploading 10 safetensors adapters to $ADAPTER_REPO/safetensors/ ..." -ForegroundColor Cyan
hf upload $ADAPTER_REPO $ADAPTER_DIR safetensors --repo-type model 2>&1 | Out-Host

Write-Host "`nDone." -ForegroundColor Green
Write-Host "  Model:    https://huggingface.co/$OV_REPO"
Write-Host "  Adapters: https://huggingface.co/$ADAPTER_REPO/tree/main/safetensors"
