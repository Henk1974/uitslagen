@echo off
rem Bouwt dist\Uitslagen\Uitslagen.exe en daarna installer\Uitslagen-installatie.exe.
rem Vereist: py -m pip install --user pyinstaller  en  winget install JRSoftware.InnoSetup
cd /d "%~dp0"

py -m PyInstaller --noconfirm --clean --windowed --icon uitslagen.ico --name Uitslagen uitslagen_app.py
if errorlevel 1 goto fout

set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
"%ISCC%" installer.iss
if errorlevel 1 goto fout

echo.
echo Klaar: installer\Uitslagen-installatie.exe
exit /b 0

:fout
echo.
echo Bouwen mislukt.
pause
exit /b 1
