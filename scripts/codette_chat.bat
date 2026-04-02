@echo off
setlocal
REM Codette Chat - Double-click to launch
REM No console window needed (uses pythonw.exe)
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "PYTHONW_CMD="
if exist "%PROJECT_ROOT%\.venv\Scripts\pythonw.exe" set "PYTHONW_CMD=%PROJECT_ROOT%\.venv\Scripts\pythonw.exe"
if not defined PYTHONW_CMD if exist "%LocalAppData%\Programs\Python\Python312\pythonw.exe" set "PYTHONW_CMD=%LocalAppData%\Programs\Python\Python312\pythonw.exe"
if not defined PYTHONW_CMD if exist "%LocalAppData%\Programs\Python\Python311\pythonw.exe" set "PYTHONW_CMD=%LocalAppData%\Programs\Python\Python311\pythonw.exe"
if defined PYTHONW_CMD (
    start "" "%PYTHONW_CMD%" "%PROJECT_ROOT%\inference\codette_chat_ui.py"
) else (
    start "" pythonw "%PROJECT_ROOT%\inference\codette_chat_ui.py"
)
endlocal
