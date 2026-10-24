@echo off
cd /d "%~dp0"
set "BACKGROUND=%~1"
py -m pip install --user requests beautifulsoup4 pandas openpyxl
if errorlevel 1 (
    echo.
    echo Installatie van de benodigde Python-pakketten is mislukt.
    echo Controleer of Python is geinstalleerd en beschikbaar is via 'py'.
    if /i not "%BACKGROUND%"=="/background" pause
    exit /b 1
)
py main.py
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" if /i not "%BACKGROUND%"=="/background" pause
exit /b %EXIT_CODE%