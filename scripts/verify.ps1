param([switch]$IncludeDev)
. "$PSScriptRoot/common.ps1"
Push-Location $ProjectRoot
$previousMode = $env:TRACEREVIEW_E2E_MODE
try {
    Assert-Tools
    Assert-FreePort 8001
    if ($IncludeDev) { Assert-FreePort 5174 }
    Invoke-Checked uv run --locked python backend/manage.py check
    Invoke-Checked uv run --locked python backend/manage.py makemigrations --check --dry-run
    Invoke-Checked uv run --locked python backend/manage.py test --noinput
    Push-Location frontend
    try {
        Invoke-Checked npm.cmd run lint
        Invoke-Checked npm.cmd run typecheck
    } finally { Pop-Location }
    & "$PSScriptRoot/build.ps1"
    Push-Location frontend
    try {
        $env:TRACEREVIEW_E2E_MODE = 'built'
        Invoke-Checked npx.cmd playwright test
        if ($IncludeDev) {
            $env:TRACEREVIEW_E2E_MODE = 'dev'
            Invoke-Checked npx.cmd playwright test
        }
    } finally { Pop-Location }
    Write-Output 'All local checks passed.'
} finally {
    $env:TRACEREVIEW_E2E_MODE = $previousMode
    Pop-Location
}
