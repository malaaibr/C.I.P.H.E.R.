@echo off
setlocal enabledelayedexpansion
title DevNex Assistant  —  Build Tool
color 0B

echo.
echo  +================================================+
echo  ^|   DevNex Assistant  v1.0.0  ^|  Build for Win   ^|
echo  +================================================+
echo.

REM ── Working directory = folder containing this script ──────────────────────
cd /d "%~dp0"

REM ── 0. Verify Python ────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found in PATH.
    echo  Install Python 3.11+ from https://python.org and try again.
    goto :fail
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  Python: %%v

REM ── 1. Install runtime dependencies ────────────────────────────────────────
echo.
echo  [1/4]  Installing runtime dependencies...
pip install -r requirements.txt --quiet --no-warn-script-location
if errorlevel 1 goto :fail
echo          done.

REM ── 2. Install build-only tools ────────────────────────────────────────────
echo  [2/4]  Installing build tools  (pillow + pyinstaller)...
pip install pillow pyinstaller --quiet --no-warn-script-location
if errorlevel 1 goto :fail
echo          done.

REM ── 3. Generate multi-resolution ICO ───────────────────────────────────────
echo  [3/4]  Generating icon  (assets/devnex.ico)...
python generate_icon.py
if errorlevel 1 (
    echo  [WARN] Icon generation failed — build will continue without custom icon.
    REM  Create a dummy ico so PyInstaller does not abort
    if not exist assets mkdir assets
    copy nul assets\devnex.ico >nul 2>&1
)

REM ── 4. PyInstaller ─────────────────────────────────────────────────────────
echo  [4/4]  Running PyInstaller...
echo.
pyinstaller devnex_assistant.spec --clean --noconfirm
if errorlevel 1 goto :fail

REM ── Success ─────────────────────────────────────────────────────────────────
echo.
echo  +================================================+
echo  ^|   BUILD COMPLETE                               ^|
echo  ^|                                                ^|
echo  ^|   Executable:                                  ^|
echo  ^|   dist\DevNex Assistant\DevNex Assistant.exe   ^|
echo  +================================================+
echo.
goto :end

:fail
echo.
echo  +================================================+
echo  ^|   BUILD FAILED  —  see output above            ^|
echo  +================================================+
echo.
exit /b 1

:end
endlocal
