@echo off
cd /d "%~dp0"
echo.
echo   ============================================
echo     Game Version Checker v5 — Build EXE
echo   ============================================
echo.
echo   Cleaning previous build...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
echo.
echo   Building standalone EXE...
echo.
pyinstaller --clean --noconfirm gvc_gui.spec
echo.
if exist "dist\游戏版本排查工具.exe" (
    echo   ============================================
    echo     Build SUCCESS!
    echo     Output: dist\游戏版本排查工具.exe
    echo   ============================================
    echo.
    for %%A in ("dist\游戏版本排查工具.exe") do echo   Size: %%~zA bytes
) else (
    echo   ============================================
    echo     Build FAILED — check errors above
    echo   ============================================
)
echo.
pause
