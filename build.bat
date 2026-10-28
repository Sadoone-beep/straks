@echo off
rem Builds dist\Straks.exe (single file, no console).
cd /d "%~dp0"
python -m pip install --quiet pyinstaller pystray Pillow || exit /b 1
python tools\make_icon.py || exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Straks ^
  --icon assets\straks.ico ^
  --add-data "assets\straks.ico;assets" ^
  --hidden-import pystray._win32 ^
  straks_app.py
if errorlevel 1 exit /b 1
echo.
echo Done: dist\Straks.exe
