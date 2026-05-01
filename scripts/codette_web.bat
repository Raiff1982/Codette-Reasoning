@echo off
setlocal
REM Codette v2.1 RC+xi Web UI
REM Opens browser to http://localhost:7860
REM
REM RC+xi FRAMEWORK (v2.1 — May 2026):
REM   Recursive Convergence + Epistemic Tension
REM   Every inference turn emits a full ReasoningTrace with 12 event types:
REM     SPIDERWEB_UPDATE  QuantumSpiderweb belief propagation (forge_with_debate)
REM     GUARDIAN_CHECK    Input safety + trust calibration
REM     NEXUS_SIGNAL      Pre-corruption detection
REM     EPISTEMIC_METRICS epsilon band, gamma coherence, coverage
REM     PERSPECTIVE_SELECTED  Active perspectives + domains (forge_with_debate)
REM     AEGIS_SCORE       6-framework ethical evaluation (utilitarian/deontological/virtue...)
REM     HALLUCINATION_FLAG  Per-perspective, fires on PAUSE/INTERRUPT only
REM     SYNTHESIS_RESULT  Integrated output + style register + depth_preserved
REM     SYCOPHANCY_FLAG   Post-synthesis integrity check, every turn
REM     PSI_UPDATE        Resonant continuity wavefunction psi_r
REM     MEMORY_WRITE      MemoryCocoonV2 with epsilon_band, psi_r, problem_type
REM
REM   New in v2.1:
REM     StyleAdaptiveSynthesis   Register-matched surface form (CASUAL/TECHNICAL/EMOTIONAL/FORMAL/EXPLORATORY)
REM                              Depth preservation invariant: adapted depth >= 0.85 * original
REM     DriftDetector            Longitudinal drift: epsilon trend, perspective lock, recurring tensions
REM                              Exposed at GET /api/drift, polled every 60s in UI
REM     UnifiedMemory bridge     RC+xi cocoons dual-written to SQLite FTS5 store
REM                              Enables cross-system search (CocoonSynthesizer, adapter learning)
REM     HallucinationGuard       Codette canonical terms whitelist prevents false positives
REM                              forge_with_debate path: scans per-perspective + synthesis
REM     SycophancyGuard          reset_session() called on /api/new_session
REM     Early-return trace fix   All fallback exits (stability/Colleen/Guardian) now finalize trace
REM
REM ACTIVE SUBSYSTEMS:
REM   Memory:     LivingMemoryKernelV2 (epsilon_band, psi_r, unresolved_tensions, synthesis_quality)
REM               UnifiedMemory (SQLite+FTS5, WAL mode, LRU cache, legacy migration)
REM   Reasoning:  QuantumSpiderweb (5D belief graph), ResonantContinuityEngine (psi_r)
REM   Integrity:  HallucinationGuard + SycophancyGuard + DebateTracker + SycophancyGuard
REM   Ethics:     AEGIS (6-framework) + EthicalAIGovernance + Colleen + Guardian
REM   Output:     StyleAdaptiveSynthesis, ResponseComplexityMatcher
REM   Analytics:  DriftDetector (/api/drift), CocoonSynthesizer (/api/synthesize)
REM
REM Model: Llama 3.1 8B quantized + 9 domain-specific LoRA adapters + orchestrator
REM Tests: 26 passing (e2e trace, debate trace, hallucination, drift detector)
REM

echo.
echo ============================================================
echo   Codette v2.1 RC+xi  --  Structurally Complete
echo ============================================================
echo.
echo   All 12 trace event types wired and tested.
echo   Longitudinal drift detection active.
echo   Style-adaptive synthesis: register-matched output.
echo   UnifiedMemory bridge: FTS5 cross-system search enabled.
echo.
echo   Subsystems:
echo     * 9 LoRA adapters (Newton, DaVinci, Empathy, Philosophy,
echo         Quantum, Consciousness, Multi-Perspective, Systems, Orchestrator)
echo     * 7-layer consciousness stack (forge_with_debate)
echo     * QuantumSpiderweb + ResonantContinuityEngine
echo     * HallucinationGuard + SycophancyGuard + AEGIS
echo     * LivingMemoryKernelV2 + UnifiedMemory (SQLite+FTS5)
echo     * DriftDetector  --  GET /api/drift
echo.
echo   Testing locally at: http://localhost:7860
echo.
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "PYTHON_CMD="
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" set "PYTHON_CMD=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if not defined PYTHON_CMD if exist "%PROJECT_ROOT%\.venv\bin\python" set "PYTHON_CMD=%PROJECT_ROOT%\.venv\bin\python"
REM Prefer the Python 3.14 user install where llama_cpp/numpy are correctly built
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python314\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PYTHON_CMD set "PYTHON_CMD=python"

cd /d "%PROJECT_ROOT%"
set PYTHONNOUSERSITE=1

echo   Starting server...
echo.
"%PYTHON_CMD%" -u -B "%PROJECT_ROOT%\inference\codette_server.py"
echo.
if errorlevel 1 (
    echo ERROR: Server exited with an error. See above for details.
) else (
    echo Server stopped.
)
echo.
pause
endlocal
