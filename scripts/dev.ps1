. "$PSScriptRoot/common.ps1"
Push-Location $ProjectRoot
$backendProcess = $null
try {
    Assert-Tools
    Assert-FreePort 8000
    Assert-FreePort 5173
    $env:TRACEREVIEW_DEBUG = '1'
    $uvPath = (Get-Command uv).Source
    $backendProcess = Start-Process -FilePath $uvPath -ArgumentList @('run','--locked','python','backend/manage.py','runserver','127.0.0.1:8000','--noreload') -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput '.local/dev-server.out.log' -RedirectStandardError '.local/dev-server.err.log'
    Write-Output 'Development workspace: http://127.0.0.1:5173. Press Ctrl+C to stop.'
    Push-Location frontend
    try { Invoke-Checked npm.cmd run dev } finally { Pop-Location }
} finally {
    if ($backendProcess -and -not $backendProcess.HasExited) {
        # taskkill /T targets only the process tree started by this script.
        & taskkill.exe /PID $backendProcess.Id /T /F 2>$null | Out-Null
    }
    Remove-Item Env:TRACEREVIEW_DEBUG -ErrorAction SilentlyContinue
    Pop-Location
}
