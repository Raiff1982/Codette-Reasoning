@echo off
setlocal
REM Codette v2.4 RC+xi Web UI
REM Opens browser to http://localhost:7860
REM
REM v2.4 additions (May 26 2026): Phase 8 render/cognition separation
REM   (CognitionSubstrate + RenderLayer), coherence 0.572→0.700, Turing
REM   0.413→0.820, Cohen's d=8.31, Supabase live sync (951 cocoons),
REM   math adapter routing fix, anchor phrase recall, greeting fast-path,
REM   comprehensive template suppression (LOCK 6+7, 18-pattern scrubber).
REM   See docs/CHANGELOG_2026-05-26.md
REM
REM v2.3 additions (May 22 2026): full 10-adapter roster (orchestrator +
REM   constraint_tracker now load), Full Adapter Synthesis (SYNTHESIZE ALL),
REM   self-overclaiming hallucination signal (Signal 7), voice-reinforced
REM   behavioral retrain of all 8 perspectives, clean-query routing fix.
REM   See docs/CHANGELOG_2026-05-22.md
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
REM Model: Llama 3.1 8B quantized + 10 domain-specific LoRA adapters + orchestrator
REM         (Newton, DaVinci, Empathy, Philosophy, Quantum, Consciousness, Multi-Perspective, Systems, Constraint_Tracker, Orchestrator)
REM GPU: Full GPU acceleration (35 layers offloaded to CUDA)
REM Tests: 26 passing (e2e trace, debate trace, hallucination, drift detector)
REM

echo.
echo ============================================================
echo   Codette v2.4 RC+xi  --  Render/Cognition Separated
echo ============================================================
echo.
echo   All 12 trace event types wired and tested.
echo   Longitudinal drift detection active.
echo   Style-adaptive synthesis: register-matched output.
echo   UnifiedMemory bridge: FTS5 cross-system search enabled.
echo.
echo   Subsystems:
echo     * 10 LoRA adapters (Newton, DaVinci, Empathy, Philosophy,
echo         Quantum, Consciousness, Multi-Perspective, Systems, Constraint_Tracker, Orchestrator)
echo     * GPU acceleration enabled (35 layers on CUDA)
echo     * 7-layer consciousness stack (forge_with_debate)
echo     * QuantumSpiderweb + ResonantContinuityEngine
echo     * HallucinationGuard (Signal 7: self-overclaiming) + SycophancyGuard + AEGIS
echo     * Full Adapter Synthesis  --  SYNTHESIZE ALL (all 8 perspectives)
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
REM Prefer the standalone Python 3.14 install (in %LocalAppData%) — its main
REM site-packages has the correctly-built llama_cpp/numpy. (PYTHONNOUSERSITE=1
REM below is safe: these live in the main site-packages, not the per-user one.)
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python314\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PYTHON_CMD set "PYTHON_CMD=python"

cd /d "%PROJECT_ROOT%"
set PYTHONNOUSERSITE=1

echo   Starting server with GPU acceleration enabled...
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
