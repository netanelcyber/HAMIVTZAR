#!/usr/bin/env pwsh
<#
.SYNOPSIS
VDI File Analyzer
Complete analysis of VirtualBox VDI files - structure, contents, and vulnerabilities

.PARAMETER VDIPath
Path to VDI file

.PARAMETER AnalysisMode
'quick' - Basic info, 'deep' - Full extraction and analysis, 'forensic' - Complete filesystem scan

.PARAMETER OutputFormat
'text', 'json', or 'html'

.EXAMPLE
.\VDI_Analyzer.ps1 -VDIPath "C:\VirtualBox VMs\FortiGate-Lab\FortiGate-Lab.vdi" -AnalysisMode deep

.EXAMPLE
.\VDI_Analyzer.ps1 -VDIPath "C:\path\to\file.vdi" -AnalysisMode forensic -OutputFormat json
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$VDIPath,

    [Parameter(Mandatory=$false)]
    [ValidateSet('quick', 'deep', 'forensic')]
    [string]$AnalysisMode = 'deep',

    [Parameter(Mandatory=$false)]
    [ValidateSet('text', 'json', 'html')]
    [string]$OutputFormat = 'text',

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
# VDI FILE ANALYSIS
# ============================================================================

function Analyze-VDIHeader {
    param([string]$VDIPath)

    Write-InfoMsg "Analyzing VDI header..."

    $findings = @()

    try {
        $file = [System.IO.File]::OpenRead($VDIPath)
        $reader = New-Object System.IO.BinaryReader($file)

        # VDI Header structure
        $magicNumber = $reader.ReadBytes(4)
        $magicString = [System.Text.Encoding]::ASCII.GetString($magicNumber)

        $findings += @{
            Category = "VDI Header"
            Finding = "Magic: $magicString (VDI signature)"
            Type = "Structure"
        }

        # Version
        $versionMinor = $reader.ReadUInt16()
        $versionMajor = $reader.ReadUInt16()
        $findings += @{
            Category = "VDI Version"
            Finding = "Version: $versionMajor.$versionMinor"
            Type = "Info"
        }

        # Header size
        $headerSize = $reader.ReadUInt32()
        $findings += @{
            Category = "VDI Structure"
            Finding = "Header Size: $headerSize bytes"
            Type = "Info"
        }

        # Image type
        $imageType = $reader.ReadUInt32()
        $typeString = switch($imageType) {
            0 { "Dynamic (grows as needed)" }
            1 { "Static (full size pre-allocated)" }
            2 { "Fixed" }
            default { "Unknown ($imageType)" }
        }
        $findings += @{
            Category = "VDI Type"
            Finding = "Image Type: $typeString"
            Type = "Info"
        }

        # Image flags
        $imageFlags = $reader.ReadUInt32()
        if ($imageFlags -band 1) {
            $findings += @{
                Category = "VDI Flags"
                Finding = "VDI is marked as in-use"
                Type = "Warning"
            }
        }

        # Disk size
        $diskSize = $reader.ReadUInt64()
        $diskSizeGB = [math]::Round($diskSize / 1GB, 2)
        $findings += @{
            Category = "VDI Size"
            Finding = "Virtual Disk Size: $diskSizeGB GB"
            Type = "Info"
        }

        # Block size
        $blockSize = $reader.ReadUInt32()
        $findings += @{
            Category = "VDI Block"
            Finding = "Block Size: $([math]::Round($blockSize / 1MB, 2)) MB"
            Type = "Info"
        }

        $reader.Close()
        $file.Close()

        return $findings
    }
    catch {
        Write-ErrorMsg "Failed to read VDI header: $_"
        return $null
    }
}

function Extract-VDIContents {
    param([string]$VDIPath)

    Write-InfoMsg "Extracting VDI contents..."

    # Check for 7-Zip
    $7zipPath = "C:\Program Files\7-Zip\7z.exe"
    if (-not (Test-Path $7zipPath)) {
        $7zipPath = "C:\Program Files (x86)\7-Zip\7z.exe"
    }

    if (-not (Test-Path $7zipPath)) {
        Write-WarningMsg "7-Zip not found - skipping extraction"
        return $null
    }

    $extractPath = "C:\temp\vdi_extract_$(Get-Random)"
    New-Item -ItemType Directory -Path $extractPath -Force | Out-Null

    Write-InfoMsg "Extracting to: $extractPath"

    try {
        & $7zipPath x $VDIPath -o"$extractPath" -y 2>&1 | Out-Null
        Write-SuccessMsg "Extraction complete"
        return $extractPath
    }
    catch {
        Write-ErrorMsg "Extraction failed: $_"
        return $null
    }
}

function Analyze-FileSystem {
    param([string]$ExtractPath)

    Write-InfoMsg "Analyzing filesystem..."

    $findings = @()

    # Find interesting directories
    $interestingDirs = @(
        "/bin", "/sbin", "/etc", "/opt", "/root", "/home",
        "/var/log", "/var/cache", "/usr/local"
    )

    foreach ($dir in $interestingDirs) {
        $fullPath = Join-Path $ExtractPath $dir.TrimStart("/")
        if (Test-Path $fullPath) {
            $fileCount = (Get-ChildItem -Path $fullPath -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            $findings += @{
                Category = "Directory"
                Finding = "Found: $dir ($fileCount files)"
                Type = "Info"
            }
        }
    }

    return $findings
}

function Find-SuspiciousFiles {
    param([string]$ExtractPath)

    Write-InfoMsg "Searching for suspicious files..."

    $findings = @()

    # Suspicious file patterns
    $patterns = @{
        "Configuration Files" = @("*.conf", "*.cfg", "*.config", "*.xml", "*.json")
        "Credentials" = @("*password*", "*secret*", "*key*", "*.pem", "*.key", "*.cert")
        "Binaries" = @("httpsd", "sslvpnd", "cmdb", "fortiosctl", "fgfm")
        "Logs" = @("*.log", "syslog", "messages")
        "SSH Keys" = @("authorized_keys", "id_rsa", "id_dsa")
    }

    foreach ($category in $patterns.Keys) {
        foreach ($pattern in $patterns[$category]) {
            try {
                $files = Get-ChildItem -Path $ExtractPath -Recurse -Filter $pattern `
                    -File -ErrorAction SilentlyContinue | Select-Object -First 10

                foreach ($file in $files) {
                    $relativePath = $file.FullName.Replace($ExtractPath, "")
                    $findings += @{
                        Category = $category
                        Finding = "Found: $relativePath ($([math]::Round($file.Length / 1KB, 1)) KB)"
                        Type = "File"
                        Path = $file.FullName
                        Size = $file.Length
                    }
                }
            }
            catch {
                # Silently continue
            }
        }
    }

    return $findings
}

function Find-Vulnerabilities {
    param([string]$ExtractPath)

    Write-InfoMsg "Scanning for vulnerabilities..."

    $findings = @()

    # Check for known vulnerable patterns
    $vulnPatterns = @{
        "Hard-coded Credentials" = @("admin:admin", "password123", "default_pass")
        "Weak Permissions" = @("chmod 777", "chmod 666", "chmod 644 /root")
        "Missing Security" = @("no firewall", "root access", "debug mode")
    }

    # Search config files
    $configFiles = Get-ChildItem -Path $ExtractPath -Recurse -Filter "*.conf" `
        -File -ErrorAction SilentlyContinue | Select-Object -First 20

    foreach ($configFile in $configFiles) {
        try {
            $content = Get-Content $configFile.FullName -Raw -ErrorAction SilentlyContinue

            if ($content -match "admin|password|secret|key") {
                $findings += @{
                    Category = "Configuration"
                    Finding = "Suspicious content in: $($configFile.Name)"
                    Type = "Vulnerability"
                    Path = $configFile.FullName
                    Severity = "MEDIUM"
                }
            }
        }
        catch {
            # Continue
        }
    }

    return $findings
}

# ============================================================================
# QUICK ANALYSIS (Fast)
# ============================================================================

function Invoke-QuickAnalysis {
    param([string]$VDIPath)

    Write-SuccessMsg "Running QUICK analysis..."
    Write-Host ""

    $results = @{
        Timestamp = Get-Date -Format o
        Mode = "Quick"
        VDIPath = $VDIPath
        FileInfo = $null
        HeaderAnalysis = $null
    }

    # File info
    $fileInfo = Get-Item $VDIPath
    $results.FileInfo = @{
        Size = "$([math]::Round($fileInfo.Length / 1GB, 2)) GB"
        Created = $fileInfo.CreationTime
        Modified = $fileInfo.LastWriteTime
    }

    Write-SuccessMsg "File Size: $($results.FileInfo.Size)"
    Write-SuccessMsg "Created: $($results.FileInfo.Created)"

    # Header analysis
    $headerFindings = Analyze-VDIHeader -VDIPath $VDIPath
    $results.HeaderAnalysis = $headerFindings

    foreach ($finding in $headerFindings) {
        Write-SuccessMsg "$($finding.Category): $($finding.Finding)"
    }

    return $results
}

# ============================================================================
# DEEP ANALYSIS (Extraction + Filesystem)
# ============================================================================

function Invoke-DeepAnalysis {
    param([string]$VDIPath)

    Write-SuccessMsg "Running DEEP analysis..."
    Write-Host ""

    $results = @{
        Timestamp = Get-Date -Format o
        Mode = "Deep"
        VDIPath = $VDIPath
        HeaderAnalysis = $null
        FileSystemAnalysis = $null
        SuspiciousFiles = $null
    }

    # Header
    $headerFindings = Analyze-VDIHeader -VDIPath $VDIPath
    $results.HeaderAnalysis = $headerFindings

    # Extract
    $extractPath = Extract-VDIContents -VDIPath $VDIPath

    if ($extractPath) {
        # Filesystem analysis
        Write-InfoMsg "Scanning filesystem..."
        $fsFindings = Analyze-FileSystem -ExtractPath $extractPath
        $results.FileSystemAnalysis = $fsFindings

        # Find suspicious files
        $suspFiles = Find-SuspiciousFiles -ExtractPath $extractPath
        $results.SuspiciousFiles = $suspFiles

        foreach ($file in $suspFiles) {
            Write-WarningMsg "$($file.Category): $($file.Finding)"
        }

        # Cleanup
        Write-InfoMsg "Cleaning up temporary files..."
        Remove-Item -Path $extractPath -Recurse -Force -ErrorAction SilentlyContinue
    }

    return $results
}

# ============================================================================
# FORENSIC ANALYSIS (Complete)
# ============================================================================

function Invoke-ForensicAnalysis {
    param([string]$VDIPath)

    Write-SuccessMsg "Running FORENSIC analysis..."
    Write-Host ""

    $results = Invoke-DeepAnalysis -VDIPath $VDIPath
    $results.Mode = "Forensic"

    # Extract again for vulnerability scanning
    $extractPath = Extract-VDIContents -VDIPath $VDIPath

    if ($extractPath) {
        Write-InfoMsg "Scanning for vulnerabilities..."
        $vulnFindings = Find-Vulnerabilities -ExtractPath $extractPath
        $results.Vulnerabilities = $vulnFindings

        foreach ($vuln in $vulnFindings) {
            Write-WarningMsg "$($vuln.Category): $($vuln.Finding) [Severity: $($vuln.Severity)]"
        }

        Remove-Item -Path $extractPath -Recurse -Force -ErrorAction SilentlyContinue
    }

    return $results
}

# ============================================================================
# REPORTING
# ============================================================================

function Generate-TextReport {
    param($AnalysisResults)

    Write-Host ""
    Write-SuccessMsg "=========================================="
    Write-SuccessMsg "VDI ANALYSIS REPORT"
    Write-SuccessMsg "=========================================="
    Write-InfoMsg "Mode: $($AnalysisResults.Mode)"
    Write-InfoMsg "VDI: $($AnalysisResults.VDIPath)"
    Write-InfoMsg "Time: $($AnalysisResults.Timestamp)"
    Write-SuccessMsg "=========================================="
    Write-Host ""

    if ($AnalysisResults.FileInfo) {
        Write-InfoMsg "FILE INFORMATION:"
        Write-InfoMsg "  Size: $($AnalysisResults.FileInfo.Size)"
        Write-InfoMsg "  Created: $($AnalysisResults.FileInfo.Created)"
        Write-InfoMsg "  Modified: $($AnalysisResults.FileInfo.Modified)"
        Write-Host ""
    }

    if ($AnalysisResults.HeaderAnalysis) {
        Write-SuccessMsg "HEADER ANALYSIS:"
        foreach ($finding in $AnalysisResults.HeaderAnalysis) {
            Write-InfoMsg "  $($finding.Category): $($finding.Finding)"
        }
        Write-Host ""
    }

    if ($AnalysisResults.FileSystemAnalysis) {
        Write-SuccessMsg "FILESYSTEM ANALYSIS:"
        foreach ($finding in $AnalysisResults.FileSystemAnalysis | Select-Object -First 10) {
            Write-InfoMsg "  $($finding.Finding)"
        }
        Write-Host ""
    }

    if ($AnalysisResults.SuspiciousFiles) {
        Write-WarningMsg "SUSPICIOUS FILES: ($($AnalysisResults.SuspiciousFiles.Count))"
        foreach ($file in $AnalysisResults.SuspiciousFiles | Select-Object -First 15) {
            Write-WarningMsg "  $($file.Category): $($file.Finding)"
        }
        Write-Host ""
    }

    if ($AnalysisResults.Vulnerabilities) {
        Write-WarningMsg "VULNERABILITIES: ($($AnalysisResults.Vulnerabilities.Count))"
        foreach ($vuln in $AnalysisResults.Vulnerabilities | Select-Object -First 10) {
            Write-WarningMsg "  [$($vuln.Severity)] $($vuln.Category): $($vuln.Finding)"
        }
        Write-Host ""
    }

    Write-SuccessMsg "=========================================="
}

function Generate-JSONReport {
    param($AnalysisResults, [string]$OutputPath)

    $json = $AnalysisResults | ConvertTo-Json -Depth 5
    Set-Content -Path $OutputPath -Value $json -Encoding UTF8

    Write-SuccessMsg "JSON report saved: $OutputPath"
}

# ============================================================================
# MAIN
# ============================================================================

function Start-VDIAnalyzer {
    Write-Host ""
    Write-SuccessMsg "=========================================="
    Write-SuccessMsg "VDI FILE ANALYZER"
    Write-SuccessMsg "=========================================="
    Write-InfoMsg "VDI: $VDIPath"
    Write-InfoMsg "Mode: $AnalysisMode"
    Write-InfoMsg "Format: $OutputFormat"
    Write-Host ""

    # Validate VDI file
    if (-not (Test-Path $VDIPath)) {
        Write-ErrorMsg "VDI file not found: $VDIPath"
        return
    }

    # Run analysis
    $results = switch ($AnalysisMode) {
        'quick' { Invoke-QuickAnalysis -VDIPath $VDIPath }
        'deep' { Invoke-DeepAnalysis -VDIPath $VDIPath }
        'forensic' { Invoke-ForensicAnalysis -VDIPath $VDIPath }
    }

    # Generate report
    switch ($OutputFormat) {
        'text' {
            Generate-TextReport -AnalysisResults $results
        }
        'json' {
            $reportFile = "vdi_analysis_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
            Generate-JSONReport -AnalysisResults $results -OutputPath $reportFile
        }
        'html' {
            Write-WarningMsg "HTML format not yet implemented"
        }
    }

    Write-SuccessMsg "Analysis complete!"
}

# ============================================================================
# ENTRY POINT
# ============================================================================

Start-VDIAnalyzer
