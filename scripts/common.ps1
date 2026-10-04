$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Checked {
    param([Parameter(Mandatory)][string]$Executable, [Parameter(ValueFromRemainingArguments)][string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Executable exited with code $LASTEXITCODE." }
}

function Assert-FreePort {
    param([int]$Port)
    $listeners = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($listeners) { throw "Port $Port is in use. Stop that service or choose a free port explicitly; no process was stopped." }
}

function Assert-Tools {
    foreach ($tool in @('uv', 'node', 'npm.cmd')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Required tool missing: $tool. See README.md." }
    }
    $nodeVersion = (& node -p 'process.versions.node').Trim()
    if ([version]$nodeVersion -lt [version]'24.19.0' -or [version]$nodeVersion -ge [version]'25.0.0') { throw 'Use Node.js 24.19 or newer in the 24.x series.' }
}
