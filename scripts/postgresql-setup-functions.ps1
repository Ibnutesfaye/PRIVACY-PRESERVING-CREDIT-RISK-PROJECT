function Convert-SecureToPlainText {
    param([AllowNull()][Security.SecureString]$SecureValue)

    if ($null -eq $SecureValue) { throw 'Password input was not captured.' }
    $pointer = [IntPtr]::Zero
    try {
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        if ($null -eq $plain) { throw 'Password conversion returned no value.' }
        return $plain
    } finally {
        if ($pointer -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        }
    }
}

function Protect-Secrets {
    param(
        [AllowNull()][string]$Text,
        [AllowEmptyCollection()][object[]]$Secrets = @()
    )

    $safe = if ($null -eq $Text) { '' } else { $Text }
    foreach ($secret in @($Secrets)) {
        if ($null -eq $secret) { continue }
        $secretText = [string]$secret
        if ($secretText.Length -gt 0) {
            $safe = $safe.Replace($secretText, '[REDACTED]')
        }
    }
    # Defense in depth for URLs not captured by exact-value replacement.
    $safe = [regex]::Replace(
        $safe,
        '(?i)(postgres(?:ql)?(?:\+[^:\s/]+)?://[^:\s/@]+:)[^@\s]+(@)',
        '$1[REDACTED]$2'
    )
    return $safe
}

function Invoke-NativeCapture {
    param(
        [Parameter(Mandatory)][string]$Executable,
        [AllowEmptyCollection()][string[]]$Arguments = @(),
        [AllowNull()][string]$InputText,
        [switch]$HasInput
    )

    $previousErrorPreference = $ErrorActionPreference
    $hasNativePreference = Test-Path variable:PSNativeCommandUseErrorActionPreference
    if ($hasNativePreference) {
        $previousNativePreference = $PSNativeCommandUseErrorActionPreference
    }
    try {
        # Native programs commonly use stderr for ordinary logging. Prevent
        # PowerShell from converting that stream into a terminating ErrorRecord.
        $ErrorActionPreference = 'Continue'
        if ($hasNativePreference) { $PSNativeCommandUseErrorActionPreference = $false }
        if ($HasInput) {
            $captured = @($InputText | & $Executable @Arguments 2>&1)
        } else {
            $captured = @(& $Executable @Arguments 2>&1)
        }
        $nativeExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorPreference
        if ($hasNativePreference) {
            $PSNativeCommandUseErrorActionPreference = $previousNativePreference
        }
    }

    if ($null -eq $nativeExitCode) {
        throw "Native command did not provide an exit code: $Executable"
    }
    [PSCustomObject]@{
        ExitCode = [int]$nativeExitCode
        Output = @($captured)
    }
}

function Assert-NativeSuccess {
    param(
        [Parameter(Mandatory)]$Result,
        [Parameter(Mandatory)][string]$Stage,
        [AllowEmptyCollection()][object[]]$Secrets = @(),
        [switch]$ShowOutput
    )

    $safeOutput = Protect-Secrets -Text (@($Result.Output) -join [Environment]::NewLine) -Secrets $Secrets
    if ([int]$Result.ExitCode -ne 0) {
        $suffix = if ([string]::IsNullOrWhiteSpace($safeOutput)) { '' } else { "`n$safeOutput" }
        throw "$Stage failed with exit code $($Result.ExitCode).$suffix"
    }
    if ($ShowOutput -and -not [string]::IsNullOrWhiteSpace($safeOutput)) {
        $safeOutput -split '\r?\n' | ForEach-Object { Write-Host $_ }
    }
    return $safeOutput
}
