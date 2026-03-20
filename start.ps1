$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

if (Test-Path ".\.venv\Scripts\pythonw.exe") {
    Start-Process -FilePath ".\.venv\Scripts\pythonw.exe" -ArgumentList ".\run_ui.py" -WorkingDirectory $scriptDir
}
elseif (Test-Path ".\.venv\Scripts\python.exe") {
    & ".\.venv\Scripts\python.exe" ".\run_ui.py"
}
elseif (Get-Command pythonw -ErrorAction SilentlyContinue) {
    Start-Process -FilePath "pythonw" -ArgumentList ".\run_ui.py" -WorkingDirectory $scriptDir
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python ".\run_ui.py"
}
else {
    Write-Host "Python not found. Install Python or create .venv first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
