@echo off
echo ========================================
echo   HathiTrust Downloader - 打包为 EXE
echo ========================================
echo.

E:\2025\venv\Scripts\pyinstaller.exe --noconfirm --onefile --windowed ^
    --name "HathiTrust-Downloader" ^
    --add-data "E:\2025\venv\Lib\site-packages\customtkinter;customtkinter" ^
    --hidden-import=DrissionPage ^
    --hidden-import=customtkinter ^
    gui.py

echo.
echo ========================================
echo   打包完成! EXE 位于 dist\ 目录
echo ========================================
pause
