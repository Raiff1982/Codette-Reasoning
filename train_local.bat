@echo off
REM Codette Local CPU Trainer - Background training launcher
REM Runs at low priority so your computer stays responsive
REM
REM Usage:
REM   train_local.bat lean newton        Train newton with Pipeline 1 (lean, ~18GB RAM)
REM   train_local.bat offload empathy    Train empathy with Pipeline 2 (offload, ~8-12GB)
REM   train_local.bat lean --list        List available adapters
REM   train_local.bat offload --pagefile-info   Page file setup guide

setlocal

set PYTHON=J:\python.exe
set TRAIN_DIR=J:\codette-training-lab\training

if "%1"=="" goto :usage
if "%1"=="lean" goto :lean
if "%1"=="offload" goto :offload
goto :usage

:lean
echo ============================================================
echo   Starting Codette CPU-Lean Trainer (Pipeline 1)
echo   Running at BELOW_NORMAL priority
echo ============================================================
shift
start "Codette Training (Lean)" /BELOWNORMAL "%PYTHON%" "%TRAIN_DIR%\train_cpu_lean.py" %1 %2 %3 %4 %5 %6 %7 %8 %9
echo Training started in background window.
goto :end

:offload
echo ============================================================
echo   Starting Codette CPU-Offload Trainer (Pipeline 2)
echo   Running at IDLE priority (background only)
echo ============================================================
shift
start "Codette Training (Offload)" /LOW "%PYTHON%" "%TRAIN_DIR%\train_cpu_offload.py" %1 %2 %3 %4 %5 %6 %7 %8 %9
echo Training started in background window.
goto :end

:usage
echo.
echo   Codette Local CPU Trainer
echo   =========================
echo.
echo   Usage:  train_local.bat [pipeline] [adapter] [options]
echo.
echo   Pipelines:
echo     lean      Pipeline 1: ~18 GB RAM, faster (~30-90s/step)
echo     offload   Pipeline 2: ~8-12 GB RAM, slower (~2-5min/step)
echo.
echo   Examples:
echo     train_local.bat lean newton
echo     train_local.bat lean empathy --epochs 2
echo     train_local.bat offload quantum
echo     train_local.bat lean --list
echo     train_local.bat offload --pagefile-info
echo.

:end
endlocal
