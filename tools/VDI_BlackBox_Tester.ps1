#!/usr/bin/env pwsh
<#
.SYNOPSIS
VDI BlackBox Tester - Complete FortiGate Testing Suite
Combines VDI analysis + network fuzzing + code injection in single workflow

.DESCRIPTION
Automated testing pipeline:
1. Analyze VDI file structure
2. Extract and scan for vulnerabilities
3. Start VirtualBox machine
4. Run network fuzzing
5. Inject code and test internally
6. Generate comprehensive report

.PARAMETER VDIPath
Path to VDI file

.PARAMETER VMName
VirtualBox VM name (for starting/stopping)

.PARAMETER TargetIP
FortiGate IP address (auto-detect if not provided)

.PARAMETER AdminPassword
FortiGate admin password for SSH injection

.PARAMETER TestMode
'quick' (fast), 'standard' (balanced), 'thorough' (deep)

.PARAMETER AutoStart
Automatically start VirtualBox VM

.EXAMPLE
.\VDI_BlackBox_Tester.ps1 -VDIPath "C:\VirtualBox VMs\FortiGate-Lab\FortiGate-Lab.vdi" `
    -VMName "FortiGate-Lab" -AdminPassword "admin" -TestMode standard -AutoStart

.EXAMPLE
.\VDI_BlackBox_Tester.ps1 -VDIPath "C:\path\to\file.vdi" -TargetIP "10.255.1.1" -TestMode thorough
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$VDIPath,

    [Parameter(Mandatory=$false)]
    [string]$VMName,

    [Parameter(Mandatory=$false)]
    [string]$TargetIP,

    [Parameter(Mandatory=$false)]
    [string]$AdminPassword = "admin",

    [Parameter(Mandatory=$false)]
    [ValidateSet('quick', 'standard', 'thorough')]
    [string]$TestMode = 'standard',

    [Parameter(Mandatory=$false)]
    [switch]$AutoStart,

    [Parameter(Mandatory=$false)]
    [switch]$NoInjection
)

# ============================================================================
# CONFIGURATION
# ============================================================================

$script:StartTime = Get-Date
$script:Results = @{
    Timestamp = $script:StartTime
    Mode = $TestMode
    VDIPath = $VDIPath
    Stages = @()
}

$IterationMap = @{
    'quick' = @{ Iterations = 100; Connections = 5 }
    'standard' = @{ Iterations = 500; Connections = 10 }
    'thorough' = @{ Iterations = 1000; Connections = 15 }
}

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
# STAGE 1: VDI ANALYSIS
# ============================================================================

function Invoke-Stage1-VDIAnalysis {
    Write-SuccessMsg "============================================="
    Write-SuccessMsg "STAGE 1: VDI FILE ANALYSIS"
    Write-SuccessMsg "============================================="

    $stageStart = Get-Date

    # Run VDI analyzer
    $vdiAnalyzerScript = Join-Path (Split-Path $PSCommandPath) "VDI_Analyzer.ps1"

    if (Test-Path $vdiAnalyzerScript) {
        Write-InfoMsg "Running VDI analyzer..."

        $analysis = & $vdiAnalyzerScript -VDIPath $VDIPath -AnalysisMode deep -OutputFormat json
    }
    else {
        Write-WarningMsg "VDI analyzer not found, skipping detailed analysis"
        $analysis = @{ Status = "Skipped" }
    }

    $stageDuration = (Get-Date) - $stageStart

    $script:Results.Stages += @{
        Name = "VDI Analysis"
        Duration = $stageDuration.TotalSeconds
        Status = "Complete"
        Details = $analysis
    }

    Write-SuccessMsg "VDI Analysis complete: $([math]::Round($stageDuration.TotalSeconds, 2))s"
    Write-Host ""

    return $analysis
}

# ============================================================================
# STAGE 2: VM START (Optional)
# ============================================================================

function Invoke-Stage2-VMStart {
    if (-not $AutoStart -or -not $VMName) {
        Write-InfoMsg "Skipping VM start (use -AutoStart to enable)"
        return $false
    }

    Write-SuccessMsg "============================================="
    Write-SuccessMsg "STAGE 2: START VIRTUALBOX VM"
    Write-SuccessMsg "============================================="

    $stageStart = Get-Date

    Write-InfoMsg "Starting VM: $VMName"

    try {
        # Check if VirtualBox is installed
        $vboxPath = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
        if (-not (Test-Path $vboxPath)) {
            $vboxPath = "C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe"
        }

        if (-not (Test-Path $vboxPath)) {
            Write-ErrorMsg "VirtualBox not found"
            return $false
        }

        # Start VM
        & $vboxPath startvm $VMName --type headless

        Write-SuccessMsg "VM started: $VMName"
        Write-InfoMsg "Waiting 30 seconds for FortiGate to boot..."

        Start-Sleep -Seconds 30

        $script:Results.Stages += @{
            Name = "VM Start"
            Duration = (Get-Date - $stageStart).TotalSeconds
            Status = "Complete"
            VM = $VMName
        }

        Write-SuccessMsg "VM ready"
        Write-Host ""

        return $true
    }
    catch {
        Write-ErrorMsg "Failed to start VM: $_"
        return $false
    }
}

# ============================================================================
# STAGE 3: AUTO-DETECT IP (Optional)
# ============================================================================

function Invoke-Stage3-DetectIP {
    if ($TargetIP) {
        Write-InfoMsg "Using provided IP: $TargetIP"
        return $TargetIP
    }

    Write-SuccessMsg "============================================="
    Write-SuccessMsg "STAGE 3: AUTO-DETECT FORTIGATE IP"
    Write-SuccessMsg "============================================="

    $stageStart = Get-Date

    Write-InfoMsg "Scanning network for FortiGate..."

    # Check common IP ranges
    $commonIPs = @("192.168.1.50", "10.255.1.1", "192.168.1.1", "10.0.0.1")

    foreach ($ip in $commonIPs) {
        Write-InfoMsg "Testing $ip..."

        if (Test-NetConnection -ComputerName $ip -Port 8443 -InformationLevel Quiet -ErrorAction SilentlyContinue) {
            Write-SuccessMsg "FortiGate found at: $ip"

            $script:Results.Stages += @{
                Name = "IP Detection"
                Duration = (Get-Date - $stageStart).TotalSeconds
                Status = "Complete"
                DetectedIP = $ip
            }

            Write-Host ""
            return $ip
        }
    }

    Write-WarningMsg "Could not auto-detect FortiGate IP"
    return $null
}

# ============================================================================
# STAGE 4: NETWORK FUZZING
# ============================================================================

function Invoke-Stage4-NetworkFuzzing {
    param([string]$TargetIP)

    Write-SuccessMsg "============================================="
    Write-SuccessMsg "STAGE 4: NETWORK FUZZING"
    Write-SuccessMsg "============================================="

    if (-not $TargetIP) {
        Write-ErrorMsg "No target IP provided"
        return $null
    }

    $stageStart = Get-Date

    $fuzzerScript = Join-Path (Split-Path $PSCommandPath) "fortios_fuzzing_toolkit_optimized.ps1"

    if (-not (Test-Path $fuzzerScript)) {
        Write-ErrorMsg "Fuzzer script not found"
        return $null
    }

    Write-InfoMsg "Running optimized fuzzer..."
    Write-InfoMsg "Mode: $TestMode"

    $config = $IterationMap[$TestMode]

    try {
        # Run fuzzer
        & $fuzzerScript -TargetHost $TargetIP `
            -IterationsPerEndpoint $config.Iterations `
            -ParallelConnections $config.Connections

        # Get latest report
        $reportFile = Get-ChildItem -Path ".\" -Filter "fortios_fuzz_report_*.json" |
                      Sort-Object LastWriteTime -Descending |
                      Select-Object -First 1

        if ($reportFile) {
            $report = Get-Content $reportFile.FullName | ConvertFrom-Json
        }
        else {
            $report = @{ Status = "No report generated" }
        }

        $stageDuration = (Get-Date) - $stageStart

        $script:Results.Stages += @{
            Name = "Network Fuzzing"
            Duration = $stageDuration.TotalSeconds
            Status = "Complete"
            TargetIP = $TargetIP
            Iterations = $config.Iterations
            Crashes = $report.total_crashes
            Report = $reportFile.FullName
        }

        Write-SuccessMsg "Fuzzing complete: $([math]::Round($stageDuration.TotalSeconds, 2))s"
        Write-SuccessMsg "Vulnerabilities found: $($report.total_crashes)"
        Write-Host ""

        return $report
    }
    catch {
        Write-ErrorMsg "Fuzzing failed: $_"
        return $null
    }
}

# ============================================================================
# STAGE 5: CODE INJECTION
# ============================================================================

function Invoke-Stage5-CodeInjection {
    param([string]$TargetIP)

    if ($NoInjection -or -not $TargetIP) {
        Write-InfoMsg "Skipping code injection"
        return $null
    }

    Write-SuccessMsg "============================================="
    Write-SuccessMsg "STAGE 5: CODE INJECTION & INTERNAL TESTING"
    Write-SuccessMsg "============================================="

    $stageStart = Get-Date

    $injectorScript = Join-Path (Split-Path $PSCommandPath) "fortios_code_injector.ps1"

    if (-not (Test-Path $injectorScript)) {
        Write-ErrorMsg "Injector script not found"
        return $null
    }

    Write-InfoMsg "Injecting fuzzer into FortiGate..."

    try {
        & $injectorScript -TargetHost $TargetIP `
            -AdminPassword $AdminPassword `
            -ScriptPath (Join-Path (Split-Path $PSCommandPath) "fortios_cli_fuzzer.sh") `
            -ExecutionMethod ssh

        $stageDuration = (Get-Date) - $stageStart

        $script:Results.Stages += @{
            Name = "Code Injection"
            Duration = $stageDuration.TotalSeconds
            Status = "Complete"
            TargetIP = $TargetIP
        }

        Write-SuccessMsg "Injection complete: $([math]::Round($stageDuration.TotalSeconds, 2))s"
        Write-Host ""

        return @{ Status = "Success" }
    }
    catch {
        Write-ErrorMsg "Injection failed: $_"
        return $null
    }
}

# ============================================================================
# FINAL REPORT
# ============================================================================

function Generate-FinalReport {
    Write-SuccessMsg "============================================="
    Write-SuccessMsg "BLACKBOX TEST REPORT"
    Write-SuccessMsg "============================================="
    Write-InfoMsg "Test Mode: $TestMode"
    Write-InfoMsg "VDI: $VDIPath"
    Write-InfoMsg "Total Duration: $([math]::Round((Get-Date - $script:StartTime).TotalSeconds, 2))s"
    Write-SuccessMsg "============================================="
    Write-Host ""

    Write-SuccessMsg "STAGES COMPLETED:"
    foreach ($stage in $script:Results.Stages) {
        Write-SuccessMsg "  ✓ $($stage.Name) - $([math]::Round($stage.Duration, 2))s"
        if ($stage.Crashes) {
            Write-InfoMsg "    Vulnerabilities: $($stage.Crashes)"
        }
    }

    Write-Host ""
    Write-SuccessMsg "============================================="

    # Save JSON report
    $reportFile = "blackbox_test_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    $script:Results | ConvertTo-Json -Depth 5 | Set-Content -Path $reportFile -Encoding UTF8

    Write-SuccessMsg "Report saved: $reportFile"
}

# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

function Start-BlackBoxTest {
    Write-Host ""
    Write-SuccessMsg "=========================================="
    Write-SuccessMsg "VDI BLACKBOX TESTER"
    Write-SuccessMsg "=========================================="
    Write-InfoMsg "Mode: $TestMode"
    Write-InfoMsg "VDI: $VDIPath"
    Write-Host ""

    # Validate VDI
    if (-not (Test-Path $VDIPath)) {
        Write-ErrorMsg "VDI not found: $VDIPath"
        return
    }

    # Stage 1: VDI Analysis
    Invoke-Stage1-VDIAnalysis

    # Stage 2: VM Start
    Invoke-Stage2-VMStart

    # Stage 3: Detect IP
    $detectedIP = Invoke-Stage3-DetectIP

    if (-not $detectedIP) {
        Write-ErrorMsg "Could not detect FortiGate IP"
        Write-InfoMsg "Provide IP manually: -TargetIP <ip>"
        return
    }

    # Stage 4: Fuzzing
    Invoke-Stage4-NetworkFuzzing -TargetIP $detectedIP

    # Stage 5: Injection
    Invoke-Stage5-CodeInjection -TargetIP $detectedIP

    # Final Report
    Generate-FinalReport
}

# ============================================================================
# ENTRY POINT
# ============================================================================

Start-BlackBoxTest
