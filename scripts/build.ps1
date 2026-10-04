. "$PSScriptRoot/common.ps1"
Push-Location $ProjectRoot
try {
    Assert-Tools
    Push-Location frontend
    try { Invoke-Checked npm.cmd run build } finally { Pop-Location }
    Invoke-Checked uv run --locked python backend/manage.py collectstatic --noinput
    Invoke-Checked uv run --locked python scripts/build_metadata.py
    Write-Output 'Local build ready. Run ./scripts/start.ps1.'
} finally { Pop-Location }
