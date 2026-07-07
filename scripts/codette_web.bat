@echo off
setlocal
REM Codette v3.0 RC+xi Web UI
REM Opens browser to http://localhost:7860
REM
REM v3.0 additions (July 5-7 2026): OpenVINO GenAI backend LIVE
REM   - Llama 3.1 8B INT4 (4.46GB) on Intel Arc 140V GPU via OpenVINO 2026.2
REM     (auto-detected when openvino_backend\llama-3.1-8b-instruct-int4 exists;
REM      falls back to llama.cpp GGUF otherwise)
REM   - All 10 LoRA adapters converted GGUF->safetensors, hot-swap preserved
REM   - Sustained throughput 9.3 tok/s (was paging 2.4GB/request under llama.cpp)
REM   - GPQA-main 0-shot 34.0% via reason-then-answer mode (was 25.4% = chance)
REM   - State Engine v8 ENFORCING (spec: docs/specs/state_engine_v8_spec.py):
REM       measured epistemic tension gates synthesis + drives AAP epsilon,
REM       render-fidelity audit reverts drifted renders,
REM       input-sycophancy pressure injects hold-ground directive
REM   - Memory hygiene: benchmark queries excluded from store/recall/session;
REM     breach-narrative + GPQA pollution purged (see CHANGELOG_2026-07-05.md)
REM   See docs/CHANGELOG_2026-07-05.md
REM
REM v2.4 (May 26 2026): Phase 8 render/cognition separation, coherence
REM   0.572->0.700, Turing 0.413->0.820. See docs/CHANGELOG_2026-05-26.md
REM v2.3 (May 22 2026): full 10-adapter roster, Full Adapter Synthesis.
REM   See docs/CHANGELOG_2026-05-22.md
REM
REM ACTIVE SUBSYSTEMS:
REM   Backend:    OpenVINO GenAI (Arc GPU, INT4) with llama.cpp GGUF fallback
REM   Memory:     LivingMemoryKernelV2 + UnifiedMemory (SQLite+FTS5, WAL)
REM   Reasoning:  QuantumSpiderweb (5D belief graph), ResonantContinuityEngine
REM   Integrity:  State Engine v8 + HallucinationGuard + SycophancyGuard + DebateTracker
REM   Ethics:     AEGIS (6-framework) + EthicalAIGovernance + Colleen + Guardian
REM   Output:     StyleAdaptiveSynthesis, ResponseComplexityMatcher, render-fidelity audit
REM   Analytics:  DriftDetector (/api/drift), CocoonSynthesizer (/api/synthesize)
REM
REM Model: Llama 3.1 8B INT4 (OpenVINO IR) + 10 LoRA adapters
REM        (Newton, DaVinci, Empathy, Philosophy, Quantum, Consciousness,
REM         Multi-Perspective, Systems, Constraint_Tracker, Orchestrator)
REM

echo.
echo ============================================================
echo   Codette v3.0 RC+xi  --  OpenVINO / Arc GPU
echo ============================================================
echo.
echo   Backend: OpenVINO GenAI INT4 on Intel Arc 140V
echo            (auto-detected; llama.cpp GGUF fallback)
echo   State Engine v8: measured tension + render audit ENFORCING
echo   Memory guards: benchmark isolation active
echo.
echo   Subsystems:
echo     * 10 LoRA adapters (safetensors, hot-swap)
echo     * QuantumSpiderweb + ResonantContinuityEngine
echo     * HallucinationGuard + SycophancyGuard + AEGIS
echo     * LivingMemoryKernelV2 + UnifiedMemory (SQLite+FTS5)
echo     * DriftDetector  --  GET /api/drift
echo.
echo   First GPU load takes ~2 min (Arc kernel compile);
echo   cached loads ~20s.
echo.
echo   Testing locally at: http://localhost:7860
echo.
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

REM ── Kill any zombie server instances first ──────────────────────────
REM Stale/competing instances deadlock over port 7860 and the GPU, and
REM the server then hangs forever at load. (Root cause of every
REM "she isn't starting" incident so far.)
echo   Checking for existing server instances...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%%'\" | Where-Object { $_.CommandLine -like '*codette_server*' } | ForEach-Object { Write-Host ('    stopping stale instance PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" 2>nul
echo.

REM ── Python selection ────────────────────────────────────────────────
REM Preference order:
REM   1. openvino_env  — required for the OpenVINO backend (default path)
REM   2. .venv         — if a project venv exists
REM   3. Python 3.14 standalone — has llama_cpp for the GGUF fallback path
set "PYTHON_CMD="
if exist "%PROJECT_ROOT%\openvino_env\Scripts\python.exe" set "PYTHON_CMD=%PROJECT_ROOT%\openvino_env\Scripts\python.exe"
if not defined PYTHON_CMD if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" set "PYTHON_CMD=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if not defined PYTHON_CMD if exist "%PROJECT_ROOT%\.venv\bin\python" set "PYTHON_CMD=%PROJECT_ROOT%\.venv\bin\python"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python314\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PYTHON_CMD set "PYTHON_CMD=python"

cd /d "%PROJECT_ROOT%"
set PYTHONNOUSERSITE=1

echo   Python: %PYTHON_CMD%
echo   Starting server...
echo.
"%PYTHON_CMD%" -u -B "%PROJECT_ROOT%\inference\codette_server.py" --gpu-layers 35
echo.
if errorlevel 1 (
    echo ERROR: Server exited with an error. See above for details.
) else (
    echo Server stopped.
)
echo.
pause
endlocal
