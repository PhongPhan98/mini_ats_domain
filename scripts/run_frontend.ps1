$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $Root "frontend")

if (-not (Test-Path ".env.local")) {
    Copy-Item ".env.local.example" ".env.local"
}
if (-not (Test-Path "node_modules")) {
    npm install
}
npm run dev
