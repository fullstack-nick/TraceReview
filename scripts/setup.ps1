param([string]$Username = 'analyst')
. "$PSScriptRoot/common.ps1"
Push-Location $ProjectRoot
try {
    Assert-Tools
    Invoke-Checked uv sync --locked
    Push-Location frontend
    try {
        Invoke-Checked npm.cmd ci --no-audit --no-fund
        Invoke-Checked npx.cmd playwright install chromium
    } finally { Pop-Location }
    Invoke-Checked uv run --locked python backend/manage.py migrate --noinput
    Invoke-Checked uv run --locked python backend/manage.py init_analyst --username $Username
    Write-Output 'Setup complete. Run ./scripts/build.ps1, then ./scripts/start.ps1.'
} finally { Pop-Location }
