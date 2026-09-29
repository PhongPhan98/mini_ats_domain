$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & py -3.12 -c "import sys; print(sys.version)" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.12 is required. Install it with: winget install -e --id Python.Python.3.12"
    }
    Write-Host "Creating Python 3.12 environment..."
    & py -3.12 -m venv .venv
    & ".venv\Scripts\python.exe" -m pip install --upgrade pip
    & ".venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
}
if (-not (Test-Path "backend\.env")) {
    Copy-Item "backend\.env.example" "backend\.env"
    Write-Host "Created backend\.env with SQLite, local login, and AI disabled."
}

& ".venv\Scripts\alembic.exe" -c "backend\alembic.ini" upgrade head
& ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000 --app-dir backend
