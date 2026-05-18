@echo off
setlocal

echo ========================================
echo   HathiTrust Downloader - optimized EXE
echo ========================================
echo.

set "VENV=.pack-venv"
set "PY=%VENV%\Scripts\python.exe"
set "OUT_NAME=HathiTrust-Downloader-v2.0.1"
set "OUT_EXE=dist\%OUT_NAME%.exe"

if not exist "%PY%" (
    echo [ERROR] Cannot find %PY%
    echo.
    echo Please create the packaging environment first:
    echo   C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe -m venv .pack-venv
    echo   .pack-venv\Scripts\python.exe -m pip install --upgrade pip pyinstaller customtkinter DrissionPage
    echo.
    pause
    exit /b 1
)

tasklist /FI "IMAGENAME eq %OUT_NAME%.exe" 2>NUL | find /I "%OUT_NAME%.exe" >NUL
if not errorlevel 1 (
    echo [ERROR] %OUT_NAME%.exe is currently running.
    echo.
    echo Please close the app before rebuilding, then run this script again.
    echo Target file:
    echo   %OUT_EXE%
    echo.
    pause
    exit /b 1
)

"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --optimize 2 ^
    --name "%OUT_NAME%" ^
    --add-data "%VENV%\Lib\site-packages\customtkinter;customtkinter" ^
    --hidden-import DrissionPage ^
    --exclude-module pytest ^
    --exclude-module unittest ^
    --exclude-module doctest ^
    --exclude-module pydoc ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module PIL ^
    --exclude-module PyQt5 ^
    --exclude-module PyQt6 ^
    --exclude-module PySide6 ^
    --exclude-module IPython ^
    --exclude-module jupyter ^
    --exclude-module notebook ^
    gui.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo   Build failed.
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Build complete:
echo   dist\%OUT_NAME%.exe
echo ========================================
pause
