@echo off
setlocal
REM Codette v2.0 Web UI - Ollama Backend
REM Uses Ollama for inference instead of llama_cpp
REM Opens browser automatically to localhost:7860
REM
REM PREREQUISITES:
REM   1. Install Ollama: https://ollama.com/download
REM   2. Ollama must be running (it auto-starts on install)
REM   3. Custom Codette models auto-detected from J:\.ollama
REM      Preferred: codette-ultimate-v6 (8B F16, 3.6GB, RC+xi baked in)
REM
REM BENEFITS over llama_cpp:
REM   - Proper GPU acceleration (auto-detected)
REM   - KV cache management (faster follow-up queries)
REM   - Concurrent request support
REM   - Model stays warm between requests
REM   - Much faster inference (10-50x on GPU)
REM
REM OPTIONAL ENVIRONMENT VARIABLES:
REM   CODETTE_OLLAMA_MODEL  - Model name (default: llama3.1:8b-instruct-q4_K_M)
REM   CODETTE_OLLAMA_URL    - Ollama server URL (default: http://localhost:11434)
REM
REM All 12 layers of the consciousness stack still work:
REM   - Guardian + AEGIS ethics
REM   - Behavioral locks (via system prompts instead of LoRA)
REM   - Memory cocoons (SQLite + JSON)
REM   - CocoonSynthesizer + introspection
REM   - File attachment support
REM   - Phase 6 + Phase 7 routing
REM

echo.
echo ============================================================
echo   Codette v2.0 - Ollama Backend
echo ============================================================
echo.
echo   Backend: Ollama (GPU-accelerated inference)
echo   All consciousness stack layers active
echo.
echo   Make sure Ollama is running (auto-detects custom Codette models)
echo   Default model: codette-ultimate-v6 (8B F16, RC+xi baked in)
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
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python314\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PYTHON_CMD set "PYTHON_CMD=python"

cd /d "%PROJECT_ROOT%"
set PYTHONNOUSERSITE=1
set CODETTE_BACKEND=ollama
if not defined OLLAMA_MODELS set "OLLAMA_MODELS=%PROJECT_ROOT%\.ollama"
set OLLAMA_VULKAN=1

echo   Starting server with Ollama backend...
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
