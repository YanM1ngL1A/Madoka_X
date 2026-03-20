@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

echo Installing or upgrading PyInstaller...
".venv\Scripts\python.exe" -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo Failed to install PyInstaller.
    pause
    exit /b 1
)

echo Building GUI executable...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "XCrawlerProject.spec"
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo Creating shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$project = Resolve-Path '.'; " ^
  "$target = Join-Path $project 'dist\\Madoka_X.exe'; " ^
  "$shortcut = Join-Path $project 'Madoka_X.lnk'; " ^
  "$shell = New-Object -ComObject WScript.Shell; " ^
  "$link = $shell.CreateShortcut($shortcut); " ^
  "$link.TargetPath = $target; " ^
  "$link.WorkingDirectory = $project; " ^
  "$link.IconLocation = $target; " ^
  "$link.Save()"
if errorlevel 1 (
    echo Failed to create shortcut.
    pause
    exit /b 1
)

echo.
echo Build complete.
echo EXE output: %~dp0dist\Madoka_X.exe
echo Shortcut: %~dp0Madoka_X.lnk
pause
