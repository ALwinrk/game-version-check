@echo off
cd /d "%~dp0"

:: check python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Install from https://www.python.org/downloads/
    echo Check "Add Python to PATH" during install.
    pause
    exit /b 1
)

:: auto install deps
python -c "import requests,openpyxl,google_play_scraper" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install --no-cache-dir requests beautifulsoup4 google-play-scraper curl_cffi openpyxl
    echo Done.
)

:menu
cls
echo.
echo   ==========================================
echo     Game Version Checker v3
echo   ==========================================
echo.
echo   [1] Check from Excel table
echo   [2] Check package(s) directly
echo   [0] Exit
echo.
set /p choice="   Select (0-2): "

if "%choice%"=="0" exit /b
if "%choice%"=="1" goto excel_mode
if "%choice%"=="2" goto pkg_mode
echo   Invalid option
pause
goto menu

:excel_mode
echo.
set /p excel_file="   Excel file path: "
if "%excel_file%"=="" (
    echo   No file path entered
    pause
    goto menu
)
set excel_file=%excel_file:"=%
if not exist "%excel_file%" (
    echo   [Error] File not found: %excel_file%
    pause
    goto menu
)
echo.
echo   ============================================
python game_version_checker.py "%excel_file%"
echo   ============================================
pause
goto menu

:pkg_mode
echo.
echo   Multiple packages: com.tencent.ig,com.miHoYo.GenshinImpact
echo.
set /p pkg_names="   Package name(s): "
if "%pkg_names%"=="" (
    echo   No package name entered
    pause
    goto menu
)
echo.
echo   (Optional) Current backend version(s) to compare:
echo   Same order as above, comma separated. e.g. 4.3.0,6.5.0
echo   Leave blank to use last saved record.
echo.
set /p cur_vers="   Current version(s): "
echo.
echo   ============================================
if "%cur_vers%"=="" (
    python game_version_checker.py --check "%pkg_names%"
) else (
    python game_version_checker.py --check "%pkg_names%" --current "%cur_vers%"
)
echo   ============================================
pause
goto menu
