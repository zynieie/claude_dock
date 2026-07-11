@echo off
chcp 65001 >nul
rem Claude Dock V2.9 build script
rem Usage: build.bat  (in this directory)

echo === [1/3] Generating dock.ico ===
python make_icon.py
if errorlevel 1 goto :err

echo === [2/3] Cleaning previous build ===
if exist build rmdir /S /Q build
if exist dist  rmdir /S /Q dist

echo === [3/3] Running PyInstaller ===
python -m PyInstaller --clean --noconfirm tray_main.spec
if errorlevel 1 goto :err

echo.
echo === Build complete ===
echo Output: dist\ClaudeDock\ClaudeDock.exe
echo To package as ZIP: see package.bat
exit /b 0

:err
echo.
echo === BUILD FAILED ===
exit /b 1