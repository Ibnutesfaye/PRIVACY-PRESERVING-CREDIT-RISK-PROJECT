$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $projectRoot 'backend\.runtime'
$statusPath = Join-Path $runtimeDir 'postgres-setup-status.json'
$helperPath = Join-Path $PSScriptRoot 'postgresql-setup-functions.ps1'
. $helperPath
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

function Write-Status([string]$State, [string]$Message) {
    @{ state = $State; message = $Message; completed_at = (Get-Date).ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding utf8
}

$postgresPassword = $null
$appPassword = $null
$adminPassword = $null
$encodedPassword = $null
$databaseUrl = $null
$jwtSecret = $null

try {
    Write-Status 'running' 'Waiting for local masked credentials.'
    Write-Host 'CipherScore PostgreSQL secure setup' -ForegroundColor Cyan
    Write-Host 'Passwords are masked and will not be printed.'

    $psqlCandidate = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue |
        ForEach-Object {
            $rawVersion = $_.Directory.Parent.Name
            $normalizedVersion = if ($rawVersion -match '^\d+$') { "$rawVersion.0" } else { $rawVersion }
            try {
                [PSCustomObject]@{
                    Version = [System.Version]$normalizedVersion
                    RawVersion = $rawVersion
                    Path = $_.FullName
                }
            } catch {
                Write-Warning "Ignoring unrecognized PostgreSQL version folder: $rawVersion"
            }
        } | Sort-Object Version -Descending | Select-Object -First 1
    if ($null -eq $psqlCandidate) { throw 'psql.exe was not found in a recognized PostgreSQL version folder.' }
    $psqlPath = $psqlCandidate.Path
    Write-Host "Using PostgreSQL $($psqlCandidate.RawVersion)."

    $pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw 'Project virtual-environment Python was not found at .venv\Scripts\python.exe.'
    }

    $postgresSecure = Read-Host 'PostgreSQL postgres password' -AsSecureString
    $postgresPassword = Convert-SecureToPlainText $postgresSecure
    $env:PGPASSWORD = $postgresPassword
    $adminArgs = @('-X', '-q', '-w', '-h', '127.0.0.1', '-p', '5432', '-U', 'postgres', '-d', 'postgres')
    $auth = Invoke-NativeCapture $psqlPath ($adminArgs + @('-tAc', 'SELECT 1'))
    Assert-NativeSuccess $auth 'PostgreSQL administrator authentication' @($postgresPassword) | Out-Null
    if ((@($auth.Output) -join '').Trim() -ne '1') { throw 'PostgreSQL administrator verification returned an unexpected result.' }

    $appSecure = Read-Host 'New password for credit_risk_app' -AsSecureString
    $appPassword = Convert-SecureToPlainText $appSecure
    if ($appPassword.Length -lt 16) { throw 'Application database password must contain at least 16 characters.' }
    $escapedAppPassword = $appPassword.Replace("'", "''")
    $allSecrets = @($postgresPassword, $appPassword, $escapedAppPassword)
    $roleSql = @"
DO `$setup`$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'credit_risk_app') THEN
    CREATE ROLE credit_risk_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '$escapedAppPassword';
  ELSE
    ALTER ROLE credit_risk_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '$escapedAppPassword';
  END IF;
END
`$setup`$;
"@
    $role = Invoke-NativeCapture $psqlPath ($adminArgs + @('-v', 'ON_ERROR_STOP=1')) $roleSql -HasInput
    Assert-NativeSuccess $role 'Application role setup' $allSecrets | Out-Null

    $dbCheck = Invoke-NativeCapture $psqlPath ($adminArgs + @('-tAc', "SELECT 1 FROM pg_database WHERE datname='privacy_credit_risk'"))
    Assert-NativeSuccess $dbCheck 'Database existence check' $allSecrets | Out-Null
    $dbExists = ((@($dbCheck.Output) -join '').Trim() -eq '1')
    if (-not $dbExists) {
        $createDb = Invoke-NativeCapture $psqlPath ($adminArgs + @('-v', 'ON_ERROR_STOP=1', '-c', 'CREATE DATABASE privacy_credit_risk OWNER credit_risk_app'))
        Assert-NativeSuccess $createDb 'Database creation' $allSecrets | Out-Null
    }
    $owner = Invoke-NativeCapture $psqlPath ($adminArgs + @('-v', 'ON_ERROR_STOP=1', '-c', 'ALTER DATABASE privacy_credit_risk OWNER TO credit_risk_app'))
    Assert-NativeSuccess $owner 'Database ownership update' $allSecrets | Out-Null

    $databaseAdminArgs = @('-X', '-q', '-w', '-h', '127.0.0.1', '-p', '5432', '-U', 'postgres', '-d', 'privacy_credit_risk', '-v', 'ON_ERROR_STOP=1')
    $grantSql = @"
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO credit_risk_app;
GRANT CONNECT, TEMPORARY ON DATABASE privacy_credit_risk TO credit_risk_app;
GRANT USAGE, CREATE ON SCHEMA public TO credit_risk_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO credit_risk_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO credit_risk_app;
ALTER DEFAULT PRIVILEGES FOR ROLE credit_risk_app IN SCHEMA public GRANT ALL ON TABLES TO credit_risk_app;
ALTER DEFAULT PRIVILEGES FOR ROLE credit_risk_app IN SCHEMA public GRANT ALL ON SEQUENCES TO credit_risk_app;
"@
    $grants = Invoke-NativeCapture $psqlPath $databaseAdminArgs $grantSql -HasInput
    Assert-NativeSuccess $grants 'Schema and privilege setup' $allSecrets | Out-Null

    $adminEmail = (Read-Host 'Initial admin email').Trim()
    $adminName = (Read-Host 'Initial admin display name').Trim()
    if ([string]::IsNullOrWhiteSpace($adminEmail)) { throw 'Initial admin email is required.' }
    if ([string]::IsNullOrWhiteSpace($adminName)) { throw 'Initial admin display name is required.' }
    $adminSecure = Read-Host 'Initial admin password (14+ chars, upper/lower/digit/symbol)' -AsSecureString
    $adminPassword = Convert-SecureToPlainText $adminSecure

    $encodedPassword = [Uri]::EscapeDataString($appPassword)
    $databaseUrl = "postgresql+psycopg://credit_risk_app:$encodedPassword@127.0.0.1:5432/privacy_credit_risk"
    $jwtResult = Invoke-NativeCapture $pythonPath @('-c', 'import secrets; print(secrets.token_urlsafe(48))')
    Assert-NativeSuccess $jwtResult 'JWT secret generation' $allSecrets | Out-Null
    $jwtSecret = (@($jwtResult.Output) -join '').Trim()
    if ([string]::IsNullOrWhiteSpace($jwtSecret)) { throw 'JWT secret generation returned an empty value.' }
    $allSecrets = @($postgresPassword, $appPassword, $escapedAppPassword, $encodedPassword, $databaseUrl, $jwtSecret, $adminPassword)

    $env:ADMIN_DATABASE_URL = $databaseUrl
    $env:ADMIN_JWT_SECRET = $jwtSecret
    $env:ADMIN_SEED_EMAIL = $adminEmail
    $env:ADMIN_SEED_NAME = $adminName
    $env:ADMIN_SEED_PASSWORD = $adminPassword
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue

    $envLines = @(
        "ADMIN_DATABASE_URL=$databaseUrl",
        "ADMIN_JWT_SECRET=$jwtSecret",
        'ADMIN_ACCESS_TOKEN_MINUTES=15',
        'ADMIN_REFRESH_TOKEN_DAYS=7',
        'ADMIN_MAX_FAILED_LOGINS=5',
        'ADMIN_LOCKOUT_MINUTES=15'
    )
    [IO.File]::WriteAllLines((Join-Path $projectRoot '.env'), $envLines, [Text.UTF8Encoding]::new($false))

    Push-Location $projectRoot
    try {
        $migration = Invoke-NativeCapture $pythonPath @('-m', 'alembic', 'upgrade', 'head')
        Assert-NativeSuccess $migration 'Alembic migration' $allSecrets -ShowOutput | Out-Null

        $seed = Invoke-NativeCapture $pythonPath @('-m', 'backend.scripts.seed_admin')
        Assert-NativeSuccess $seed 'Initial administrator seed/update' $allSecrets -ShowOutput | Out-Null

        $current = Invoke-NativeCapture $pythonPath @('-m', 'alembic', 'current')
        $currentText = Assert-NativeSuccess $current 'Alembic revision verification' $allSecrets -ShowOutput
        if ($currentText -notmatch '\(head\)') { throw 'Alembic did not report the database at the head revision.' }

        $verify = Invoke-NativeCapture $pythonPath @('-m', 'backend.scripts.verify_postgresql_setup')
        Assert-NativeSuccess $verify 'PostgreSQL and administrator verification' $allSecrets -ShowOutput | Out-Null
    } finally {
        Pop-Location
    }

    Write-Status 'complete' 'PostgreSQL database, migrations, admin update, and verification completed.'
    Write-Host 'Setup completed successfully. You may close this window.' -ForegroundColor Green
} catch {
    $line = $_.InvocationInfo.ScriptLineNumber
    $stack = if ($_.ScriptStackTrace) { $_.ScriptStackTrace } else { '' }
    $secrets = @($databaseUrl, $appPassword, $encodedPassword, $postgresPassword, $jwtSecret, $adminPassword)
    $diagnostic = Protect-Secrets -Text "Setup failed at line ${line}: $($_.Exception.Message)" -Secrets $secrets
    $safeStack = Protect-Secrets -Text $stack -Secrets $secrets
    Write-Status 'failed' $diagnostic
    Write-Error $diagnostic -ErrorAction Continue
    if (-not [string]::IsNullOrWhiteSpace($safeStack)) { Write-Error $safeStack -ErrorAction Continue }
} finally {
    $postgresPassword = $null
    $appPassword = $null
    $adminPassword = $null
    $jwtSecret = $null
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:ADMIN_SEED_PASSWORD -ErrorAction SilentlyContinue
}
