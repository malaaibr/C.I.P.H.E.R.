@echo off
setlocal
title DevNex Assistant Rebuild and Run
color 0A

cd /d "%~dp0"

set "PROJECT_ROOT=%CD%"
set "VENV_DIR=%PROJECT_ROOT%\.venv"
set "DIST_EXE=%PROJECT_ROOT%\dist\DevNex Assistant\DevNex Assistant.exe"

echo.
echo ==================================================
echo DevNex Assistant - Clean Rebuild and Run
echo ==================================================
echo Project: %PROJECT_ROOT%
echo.

set "STEP=0"
set "TOTAL_STEPS=8"

REM --------------------------------------------------
REM Verify Python is available before deleting anything
REM --------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo Python: %%v
echo.

REM --------------------------------------------------
REM Remove old local virtual environments and build output
REM Keep .env files intact; only delete environment directories
REM --------------------------------------------------
call :step "Clean local environments"
for %%d in (".venv" "venv" "env" ".env") do (
    if exist "%%~d\" (
        echo     Removing environment directory: %%~d
        rmdir /s /q "%%~d"
    )
)

for %%d in ("build" "dist" ".pytest_cache") do (
    if exist "%%~d\" (
        echo     Removing build artifact directory: %%~d
        rmdir /s /q "%%~d"
    )
)

if exist "__pycache__\" (
    echo     Removing local __pycache__
    rmdir /s /q "__pycache__"
)
call :ok

call :step "Create fresh virtual environment"
python -m venv "%VENV_DIR%"
if errorlevel 1 exit /b 1
call :ok

call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 exit /b 1

call :step "Upgrade packaging tools"
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1
call :ok

call :step "Install runtime and dev dependencies"
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
call :ok

call :step "Install build tooling and project package"
python -m pip install pyinstaller
if errorlevel 1 exit /b 1
python -m pip install -e .
if errorlevel 1 exit /b 1
call :ok

call :step "Prepare generated runtime configuration"
if not exist "generated_artifacts" mkdir "generated_artifacts"
python -c "from persistence.config_store import ConfigStore, DEFAULT_CONFIG; ConfigStore().save(DEFAULT_CONFIG)"
if errorlevel 1 exit /b 1
call :ok

call :step "Run compile and test validation"
python -m compileall -q .
if errorlevel 1 exit /b 1
python -m pytest -q
if errorlevel 1 exit /b 1
call :ok

call :step "Generate icon and rebuild executable"
python generate_icon.py
if errorlevel 1 (
    echo     WARN: Icon generation failed. Build will continue.
)
python -m PyInstaller devnex_assistant.spec --clean --noconfirm
if errorlevel 1 exit /b 1
call :ok

call :step "Launch built GUI"
if not exist "%DIST_EXE%" (
    echo [ERROR] Built executable not found:
    echo         %DIST_EXE%
    exit /b 1
)

start "" "%DIST_EXE%"
call :ok
echo.
echo ==================================================
echo Build and launch completed successfully.
echo Executable:
echo %DIST_EXE%
echo ==================================================
exit /b 0

:step
set /a STEP+=1
echo.
echo [%STEP%/%TOTAL_STEPS%] %~1
exit /b 0

:ok
echo     OK
exit /b 0
