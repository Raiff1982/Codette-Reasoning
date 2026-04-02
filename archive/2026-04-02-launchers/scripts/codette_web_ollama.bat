@echo off
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

cd /d "J:\codette-clean"
set PYTHONNOUSERSITE=1
set PATH=J:\;J:\Lib\site-packages\Library\bin;%PATH%
set CODETTE_BACKEND=ollama
set OLLAMA_MODELS=J:\.ollama
set OLLAMA_VULKAN=1

echo   Starting server with Ollama backend...
echo.
J:\python.exe -u -B "J:\codette-clean\inference\codette_server.py"
echo.
if errorlevel 1 (
    echo ERROR: Server exited with an error. See above for details.
) else (
    echo Server stopped.
)
echo.
pause
