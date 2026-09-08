#!/usr/bin/env pwsh
<#
.SYNOPSIS
FortiOS Binary Analyzer & Debugger
Windows PowerShell Edition - Analyzes FortiGate binaries for vulnerabilities

.PARAMETER VDIPath
Path to VDI file

.PARAMETER BinaryPath
Path to binary to analyze (after mounting)

.PARAMETER ExtractMode
Extract binary first or analyze mounted volume

.EXAMPLE
.\Binary_Debugger.ps1 -VDIPath "C:\VirtualBox VMs\FortiGate-Lab\FortiGate-Lab.vdi"

.EXAMPLE
.\Binary_Debugger.ps1 -BinaryPath "C:\temp\fortios\bin\sslvpnd"
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$VDIPath,

    [Parameter(Mandatory=$false)]
    [string]$BinaryPath,

    [Parameter(Mandatory=$false)]
    [string]$ExtractMode = "copy",

    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# ============================================================================
# LOGGING
# ============================================================================

function Write-InfoMsg {
    param([string]$Message)
    Write-Host "[*] $Message" -ForegroundColor Cyan
}

function Write-SuccessMsg {
    param([string]$Message)
    Write-Host "[+] $Message" -ForegroundColor Green
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "[-] $Message" -ForegroundColor Red
}

function Write-WarningMsg {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

# ============================================================================
# VDI MOUNTING (Windows)
# ============================================================================

function Mount-VDI {
    param([string]$VDIPath)

    Write-InfoMsg "Attempting to mount VDI: $VDIPath"

    # Check if 7-Zip is available
    $7zipPath = "C:\Program Files\7-Zip\7z.exe"
    if (-not (Test-Path $7zipPath)) {
        $7zipPath = "C:\Program Files (x86)\7-Zip\7z.exe"
    }

    if (Test-Path $7zipPath) {
        Write-SuccessMsg "7-Zip found, using for extraction"

        $mountPath = "C:\temp\fortios_extract"
        New-Item -ItemType Directory -Path $mountPath -Force | Out-Null

        & $7zipPath x $VDIPath -o"$mountPath" -y | Out-Null

        Write-SuccessMsg "VDI extracted to: $mountPath"
        return $mountPath
    }
    else {
        Write-WarningMsg "7-Zip not found, trying alternative methods"
        return $null
    }
}

function Extract-BinaryFromVDI {
    param(
        [string]$VDIPath,
        [string]$TargetBinary = "sslvpnd"
    )

    Write-InfoMsg "Extracting binary from VDI..."

    $tempDir = "C:\temp\fortios_binaries"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

    # Try mounting with 7-Zip
    $mountPath = Mount-VDI -VDIPath $VDIPath

    if ($mountPath) {
        # Find the binary
        $binaryPath = Get-ChildItem -Path $mountPath -Recurse -Filter $TargetBinary -ErrorAction SilentlyContinue |
                      Select-Object -First 1

        if ($binaryPath) {
            Copy-Item -Path $binaryPath.FullName -Destination "$tempDir\$TargetBinary" -Force
            Write-SuccessMsg "Binary extracted: $tempDir\$TargetBinary"
            return "$tempDir\$TargetBinary"
        }
    }

    return $null
}

# ============================================================================
# BINARY ANALYSIS
# ============================================================================

function Analyze-Binary {
    param([string]$BinaryPath)

    Write-InfoMsg "Starting binary analysis of: $BinaryPath"

    $findings = @()

    # 1. File properties
    Write-InfoMsg "Analyzing file properties..."
    $fileInfo = Get-Item $BinaryPath
    $findings += @{
        Type = "File Analysis"
        Finding = "File size: $([math]::Round($fileInfo.Length / 1MB, 2)) MB"
        Severity = "INFO"
    }

    $findings += @{
        Type = "File Analysis"
        Finding = "Created: $($fileInfo.CreationTime)"
        Severity = "INFO"
    }

    # 2. Check if executable
    if ($BinaryPath -match "\.(exe|elf|bin)$" -or (Get-Content $BinaryPath -AsByteStream -TotalCount 4 | Select-Object -First 1) -eq 0x7F) {
        $findings += @{
            Type = "File Analysis"
            Finding = "File is executable binary"
            Severity = "HIGH"
        }
    }

    # 3. String analysis
    Write-InfoMsg "Extracting and analyzing strings..."
    try {
        $strings = [System.Text.Encoding]::ASCII.GetString((Get-Content $BinaryPath -AsByteStream)) -split "`0"

        $suspiciousPatterns = @{
            "Buffer Overflow" = @("gets", "strcpy", "sprintf", "scanf", "strcat")
            "Path Traversal" = @("/etc/passwd", "/root/.ssh", "/etc/shadow", "../../../")
            "Auth Bypass" = @("admin", "password", "auth", "authenticate", "unauthorized")
            "SQL Injection" = @("SELECT", "INSERT", "UPDATE", "DELETE", "DROP")
            "Command Injection" = @("system", "exec", "shell", "cmd", "bash")
        }

        foreach ($category in $suspiciousPatterns.Keys) {
            foreach ($pattern in $suspiciousPatterns[$category]) {
                $matches = $strings | Where-Object { $_ -match [regex]::Escape($pattern) } | Select-Object -First 3

                if ($matches) {
                    foreach ($match in $matches) {
                        if ($match.Length -gt 0 -and $match.Length -lt 100) {
                            $findings += @{
                                Type = "String Analysis"
                                Finding = "$category - Found: '$($match.Trim())'"
                                Severity = "MEDIUM"
                            }
                        }
                    }
                }
            }
        }
    }
    catch {
        Write-WarningMsg "String extraction failed: $_"
    }

    # 4. Check for common vulnerable functions
    Write-InfoMsg "Checking for vulnerable patterns..."

    $binaryContent = Get-Content $BinaryPath -AsByteStream -ReadCount 0
    $binaryHex = -join ($binaryContent | ForEach-Object { "{0:X2}" -f $_ })

    # Look for common function signatures
    if ($binaryHex -match "c3") {  # x86 RET
        $findings += @{
            Type = "Architecture"
            Finding = "Binary appears to be x86/x64 (contains RET instructions)"
            Severity = "INFO"
        }
    }

    # 5. Check for security features
    Write-InfoMsg "Analyzing security features..."

    # Simple heuristics based on file size and content patterns
    $fileSize = $fileInfo.Length
    if ($fileSize -gt 1MB) {
        $findings += @{
            Type = "Size Analysis"
            Finding = "Large binary ($([math]::Round($fileSize / 1MB, 2)) MB) - may indicate debug symbols stripped"
            Severity = "LOW"
        }
    }

    # Look for common library signatures
    $libSignatures = @{
        "OpenSSL" = "OpenSSL|SSL_|EVP_"
        "LibC" = "libc|malloc|free|memcpy"
        "FortiOS" = "fortios|fortigate|cmdb"
    }

    foreach ($lib in $libSignatures.Keys) {
        if ($binaryHex -match $libSignatures[$lib]) {
            $findings += @{
                Type = "Library Detection"
                Finding = "Found library: $lib"
                Severity = "INFO"
            }
        }
    }

    return $findings
}

# ============================================================================
# REPORTING
# ============================================================================

function Generate-Report {
    param([array]$Findings, [string]$BinaryPath)

    Write-Host ""
    Write-SuccessMsg "==========================================="
    Write-SuccessMsg "BINARY ANALYSIS REPORT"
    Write-SuccessMsg "==========================================="
    Write-InfoMsg "Binary: $BinaryPath"
    Write-InfoMsg "Total Findings: $($Findings.Count)"
    Write-SuccessMsg "==========================================="
    Write-Host ""

    if (-not $Findings -or $Findings.Count -eq 0) {
        Write-InfoMsg "No findings"
        return
    }

    # Group by severity
    $critical = $Findings | Where-Object { $_.Severity -eq "CRITICAL" }
    $high = $Findings | Where-Object { $_.Severity -eq "HIGH" }
    $medium = $Findings | Where-Object { $_.Severity -eq "MEDIUM" }
    $low = $Findings | Where-Object { $_.Severity -eq "LOW" }
    $info = $Findings | Where-Object { $_.Severity -eq "INFO" }

    if ($critical) {
        Write-WarningMsg "[CRITICAL] ($($critical.Count))"
        $critical | ForEach-Object { Write-WarningMsg "  - $($_.Type): $($_.Finding)" }
        Write-Host ""
    }

    if ($high) {
        Write-WarningMsg "[HIGH] ($($high.Count))"
        $high | ForEach-Object { Write-WarningMsg "  - $($_.Type): $($_.Finding)" }
        Write-Host ""
    }

    if ($medium) {
        Write-InfoMsg "[MEDIUM] ($($medium.Count))"
        $medium | ForEach-Object { Write-InfoMsg "  - $($_.Type): $($_.Finding)" }
        Write-Host ""
    }

    if ($low) {
        Write-InfoMsg "[LOW] ($($low.Count))"
        $low | Select-Object -First 5 | ForEach-Object { Write-InfoMsg "  - $($_.Type): $($_.Finding)" }
    }

    Write-Host ""
    Write-SuccessMsg "==========================================="

    # Save JSON report
    $reportFile = "binary_analysis_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    $report = @{
        binary = $BinaryPath
        timestamp = Get-Date -Format o
        total_findings = $Findings.Count
        critical = $critical.Count
        high = $high.Count
        medium = $medium.Count
        low = $low.Count
        findings = $Findings
    }

    $report | ConvertTo-Json | Set-Content -Path $reportFile -Encoding UTF8
    Write-SuccessMsg "Report saved to: $reportFile"
}

# ============================================================================
# MAIN
# ============================================================================

function Start-BinaryDebugger {
    Write-Host ""
    Write-SuccessMsg "==========================================="
    Write-SuccessMsg "FORTIOS BINARY DEBUGGER (PowerShell)"
    Write-SuccessMsg "==========================================="
    Write-Host ""

    # Determine binary path
    $targetBinary = $BinaryPath

    if (-not $targetBinary) {
        if ($VDIPath -and (Test-Path $VDIPath)) {
            Write-InfoMsg "VDI path provided: $VDIPath"
            $targetBinary = Extract-BinaryFromVDI -VDIPath $VDIPath -TargetBinary "sslvpnd"
        }
        else {
            Write-ErrorMsg "No binary path or VDI path provided"
            Write-InfoMsg "Usage:"
            Write-InfoMsg "  .\Binary_Debugger.ps1 -BinaryPath 'C:\path\to\binary'"
            Write-InfoMsg "  .\Binary_Debugger.ps1 -VDIPath 'C:\path\to\file.vdi'"
            return
        }
    }

    if (-not (Test-Path $targetBinary)) {
        Write-ErrorMsg "Binary not found: $targetBinary"
        return
    }

    # Run analysis
    $findings = Analyze-Binary -BinaryPath $targetBinary

    # Generate report
    Generate-Report -Findings $findings -BinaryPath $targetBinary

    Write-SuccessMsg "Analysis complete!"
}

# ============================================================================
# ENTRY POINT
# ============================================================================

Start-BinaryDebugger
