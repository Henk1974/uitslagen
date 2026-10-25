@echo off
if /i "%~1"=="/console" goto run
if /i not "%~1"=="/background" (
    start "" wscript.exe //B //NoLogo "%~dp0uitslagen-verborgen.vbs"
    exit /b
)
:run
cd /d "%~dp0"
set "BACKGROUND=%~1"
py -c "import requests, bs4, pandas, openpyxl" 2>nul || py -m pip install --user -r requirements.txt
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