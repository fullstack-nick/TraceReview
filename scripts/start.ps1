param([int]$Port = 8000)
. "$PSScriptRoot/common.ps1"
Push-Location $ProjectRoot
try {
    Assert-FreePort $Port
    if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) { throw 'Frontend build missing. Run ./scripts/build.ps1 first.' }
    if (-not (Test-Path -LiteralPath '.local/tracereview.sqlite3')) { throw 'Database missing. Run ./scripts/setup.ps1 first.' }
    Invoke-Checked uv run --locked python backend/manage.py migrate --check
    Invoke-Checked uv run --locked python scripts/serve_local.py --port $Port
} finally { Pop-Location }
