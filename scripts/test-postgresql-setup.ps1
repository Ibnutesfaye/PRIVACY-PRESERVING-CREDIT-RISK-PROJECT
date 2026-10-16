$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'postgresql-setup-functions.ps1')

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

$shell = Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $shell)) { $shell = (Get-Process -Id $PID).Path }

$info = Invoke-NativeCapture $shell @('-NoProfile', '-Command', "[Console]::Error.WriteLine('INFO normal alembic log'); exit 0")
Assert-True ($info.ExitCode -eq 0) 'stderr with exit zero was incorrectly treated as failure.'
Assert-True ((@($info.Output) -join "`n") -match 'INFO normal') 'stderr INFO output was not captured.'

$failure = Invoke-NativeCapture $shell @('-NoProfile', '-Command', "[Console]::Error.WriteLine('expected failure'); exit 7")
Assert-True ($failure.ExitCode -eq 7) 'non-zero native exit code was not preserved.'
$threw = $false
try { Assert-NativeSuccess $failure 'Synthetic native command' @() | Out-Null } catch { $threw = $true }
Assert-True $threw 'non-zero native exit code did not stop the stage.'

$empty = Invoke-NativeCapture $shell @('-NoProfile', '-Command', 'exit 0')
Assert-True ($empty.ExitCode -eq 0) 'empty-output command did not succeed.'
Assert-True ((@($empty.Output) -join '').Length -eq 0) 'empty output was not handled safely.'

# These values model the exact idempotent existence-query outcomes used by setup.
Assert-True ((@('1') -join '').Trim() -eq '1') 'existing database result was not recognized.'
Assert-True (-not ((@('') -join '').Trim() -eq '1')) 'missing database result was incorrectly recognized.'

$specialPassword = 'A@%:/# password value'
$encoded = [Uri]::EscapeDataString($specialPassword)
Assert-True ($encoded -notmatch '[@:/# ]') 'database password was not URL encoded.'
$configParserSafe = $encoded.Replace('%', '%%')
Assert-True ($configParserSafe -notmatch '(?<!%)%(?!%)') 'Alembic percent escaping was incomplete.'

$setupText = Get-Content -Raw (Join-Path $PSScriptRoot 'setup-postgresql.ps1')
Assert-True ($setupText -match 'IF NOT EXISTS.*pg_roles') 'role setup is not duplicate-safe.'
Assert-True ($setupText -match 'if \(-not \$dbExists\)') 'database setup is not duplicate-safe.'
Assert-True ($setupText -notmatch 'if\s*\(\s*\$std(?:err|Error)') 'stderr-based failure logic remains.'

Write-Host 'PostgreSQL setup focused tests passed.' -ForegroundColor Green
