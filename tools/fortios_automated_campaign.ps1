#!/usr/bin/env pwsh
<#
.SYNOPSIS
FortiOS Automated Fuzzing Campaign Orchestrator
Runs complete fuzz-discover-inject workflow in single command

.DESCRIPTION
Orchestrates multi-stage fuzzing campaign:
1. Initial fuzz from attacker workstation (Windows)
2. Analyze discovered vulnerabilities
3. Inject and execute within FortiOS
4. Retrieve and consolidate results
5. Generate final report

.PARAMETER TargetHost
FortiOS target IP/hostname

.PARAMETER TargetPort
SSL-VPN port (default: 8443)

.PARAMETER AdminPassword
Admin password for SSH access

.PARAMETER IterationsStage1
Initial fuzz iterations from Windows (default: 100)

.PARAMETER IterationsStage2
In-system fuzz iterations after injection (default: 50)

.PARAMETER CampaignMode
'quick' (100 total), 'standard' (500 total), 'thorough' (2000 total)

.PARAMETER Persistent
Install fuzzer as persistent payload

.PARAMETER ReportPath
Directory to save final report

.EXAMPLE
.\fortios_automated_campaign.ps1 -TargetHost 192.168.1.50 -AdminPassword "fortinet" -CampaignMode standard

.EXAMPLE
.\fortios_automated_campaign.ps1 -TargetHost 192.168.1.50 -AdminPassword "fortinet" `
    -IterationsStage1 500 -IterationsStage2 500 -Persistent
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$TargetHost,

    [Parameter(Mandatory=$false)]
    [int]$TargetPort = 8443,

    [Parameter(Mandatory=$true)]
    [string]$AdminPassword,

    [Parameter(Mandatory=$false)]
    [int]$IterationsStage1 = 100,

    [Parameter(Mandatory=$false)]
    [int]$IterationsStage2 = 50,

    [Parameter(Mandatory=$false)]
    [ValidateSet('quick', 'standard', 'thorough')]
    [string]$CampaignMode = 'standard',

    [Parameter(Mandatory=$false)]
    [switch]$Persistent,

    [Parameter(Mandatory=$false)]
    [string]$ReportPath = "./fuzz_campaign_results",

    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Determine iterations based on campaign mode
switch ($CampaignMode) {
    'quick' {
        $IterationsStage1 = 50
        $IterationsStage2 = 25
    }
    'standard' {
        $IterationsStage1 = 100
        $IterationsStage2 = 50
    }
    'thorough' {
        $IterationsStage1 = 500
        $IterationsStage2 = 500
    }
}

$StartTime = Get-Date
$ReportDir = $ReportPath
$CampaignId = $StartTime.ToString("yyyyMMdd_HHmmss")

# ============================================================================
# LOGGING
# ============================================================================

function Initialize-Logging {
    if (-not (Test-Path $ReportDir)) {
        New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
    }

    $script:LogFile = Join-Path $ReportDir "campaign_$CampaignId.log"
    $script:ReportFile = Join-Path $ReportDir "campaign_$CampaignId_report.json"
}

function Log-Message {
    param(
        [string]$Message,
        [ValidateSet('INFO', 'SUCCESS', 'WARNING', 'ERROR')]
        [string]$Level = 'INFO'
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"

    switch ($Level) {
        'INFO'    { Write-Host "[*] $Message" -ForegroundColor Cyan }
        'SUCCESS' { Write-Host "[+] $Message" -ForegroundColor Green }
        'WARNING' { Write-Host "[!] $Message" -ForegroundColor Yellow }
        'ERROR'   { Write-Host "[-] $Message" -ForegroundColor Red }
    }

    Add-Content -Path $script:LogFile -Value $logEntry
}

# ============================================================================
# STAGE 1: REMOTE FUZZ (From Windows)
# ============================================================================

function Invoke-Stage1-RemoteFuzz {
    Log-Message "=============================================" INFO
    Log-Message "STAGE 1: Remote Fuzz Campaign" INFO
    Log-Message "=============================================" INFO
    Log-Message "Target: $TargetHost`:$TargetPort" INFO
    Log-Message "Iterations per endpoint: $IterationsStage1" INFO
    Log-Message "Execution mode: Windows → FortiOS (SSL)" INFO

    $stage1Start = Get-Date

    # Check if fuzzer script exists
    $fuzzerScript = "./fortios_fuzzing_toolkit.ps1"
    if (-not (Test-Path $fuzzerScript)) {
        Log-Message "Fuzzer script not found: $fuzzerScript" ERROR
        return $null
    }

    Log-Message "Starting remote fuzzing campaign..." INFO

    # Run fuzzer
    $fuzzerOutput = & $fuzzerScript -TargetHost $TargetHost `
                                     -TargetPort $TargetPort `
                                     -IterationsPerEndpoint $IterationsStage1 `
                                     -Verbose:$Verbose

    # Find generated report
    $reportPattern = "fortios_fuzz_report_$([regex]::Escape($TargetHost))_*.json"
    $reportFile = Get-ChildItem -Path ./ -Filter $reportPattern |
                  Sort-Object LastWriteTime -Descending |
                  Select-Object -First 1

    if ($reportFile) {
        Log-Message "Remote fuzz completed" SUCCESS
        Log-Message "Report generated: $($reportFile.Name)" SUCCESS

        $stage1Report = Get-Content $reportFile | ConvertFrom-Json

        # Copy to campaign directory
        Copy-Item -Path $reportFile.FullName -Destination (Join-Path $ReportDir "stage1_remote_fuzz.json")

        return $stage1Report
    }
    else {
        Log-Message "No report file generated" WARNING
        return $null
    }
}

# ============================================================================
# STAGE 2: LOCAL FUZZ (Inside FortiOS)
# ============================================================================

function Invoke-Stage2-LocalFuzz {
    param($Stage1Report)

    Log-Message "=============================================" INFO
    Log-Message "STAGE 2: Local Fuzz (Inside FortiOS)" INFO
    Log-Message "=============================================" INFO
    Log-Message "Injecting fuzzer into FortiOS system..." INFO
    Log-Message "Execution mode: FortiOS → Self (internal)" INFO
    Log-Message "Iterations per endpoint: $IterationsStage2" INFO

    # Check if injector script exists
    $injectorScript = "./fortios_code_injector.ps1"
    if (-not (Test-Path $injectorScript)) {
        Log-Message "Injector script not found: $injectorScript" ERROR
        return $null
    }

    # Use bash fuzzer for in-system execution
    $bashFuzzer = "./fortios_cli_fuzzer.sh"
    if (-not (Test-Path $bashFuzzer)) {
        Log-Message "Bash fuzzer script not found: $bashFuzzer" ERROR
        Log-Message "Required for in-system execution" ERROR
        return $null
    }

    Log-Message "Injecting code into FortiOS..." INFO

    # Inject and execute
    try {
        & $injectorScript -TargetHost $TargetHost `
                         -AdminPassword $AdminPassword `
                         -ScriptPath $bashFuzzer `
                         -ExecutionMethod scp-then-execute `
                         -Persistent:$Persistent `
                         -Verbose:$Verbose

        Log-Message "Code injection completed" SUCCESS

        # Attempt to retrieve results if available
        Log-Message "Retrieving execution results from FortiOS..." INFO

        return @{
            status = "injected"
            persistent = $Persistent
            script = $bashFuzzer
        }
    }
    catch {
        Log-Message "Code injection failed: $_" ERROR
        return $null
    }
}

# ============================================================================
# STAGE 3: ANALYSIS & CONSOLIDATION
# ============================================================================

function Invoke-Stage3-Analysis {
    param(
        $Stage1Report,
        $Stage2Report
    )

    Log-Message "=============================================" INFO
    Log-Message "STAGE 3: Analysis & Consolidation" INFO
    Log-Message "=============================================" INFO

    if ($Stage1Report) {
        Log-Message "Stage 1 discovered $($Stage1Report.total_crashes) vulnerabilities" INFO

        # Analyze vulnerability distribution
        Log-Message "Vulnerability distribution:" INFO
        foreach ($type in $Stage1Report.vulnerabilities_by_type.Keys) {
            $count = $Stage1Report.vulnerabilities_by_type[$type]
            Log-Message "  [$count] $type" INFO
        }
    }

    if ($Stage2Report) {
        Log-Message "Stage 2 injection: $($Stage2Report.status)" INFO
        if ($Stage2Report.persistent) {
            Log-Message "Persistent payload installed - will auto-execute on system boot" SUCCESS
        }
    }

    # Identify highest-risk vulnerabilities
    if ($Stage1Report) {
        Log-Message "High-risk vulnerabilities identified:" WARNING

        $vuln = $Stage1Report.vulnerabilities_by_type
        if ($vuln.'Path Traversal' -gt 0) {
            Log-Message "  [CRITICAL] Path Traversal: $($vuln.'Path Traversal') instances" WARNING
        }
        if ($vuln.'Buffer Overflow' -gt 0) {
            Log-Message "  [HIGH] Buffer Overflow: $($vuln.'Buffer Overflow') instances" WARNING
        }
        if ($vuln.'Authentication Bypass' -gt 0) {
            Log-Message "  [MEDIUM] Authentication Bypass: $($vuln.'Authentication Bypass') instances" WARNING
        }
    }
}

# ============================================================================
# STAGE 4: REPORT GENERATION
# ============================================================================

function New-CampaignReport {
    param(
        $Stage1Report,
        $Stage2Report
    )

    Log-Message "=============================================" INFO
    Log-Message "STAGE 4: Generating Final Report" INFO
    Log-Message "=============================================" INFO

    $endTime = Get-Date
    $duration = $endTime - $StartTime

    $report = @{
        campaign_metadata = @{
            campaign_id = $CampaignId
            target = $TargetHost
            target_port = $TargetPort
            mode = $CampaignMode
            start_time = $StartTime.ToString("o")
            end_time = $endTime.ToString("o")
            duration_seconds = $duration.TotalSeconds
        }

        stage1_remote_fuzz = $Stage1Report

        stage2_local_fuzz = $Stage2Report

        summary = @{
            total_fuzz_iterations = $IterationsStage1 + $IterationsStage2
            total_vulnerabilities = if ($Stage1Report) { $Stage1Report.total_crashes } else { 0 }
            persistent_payload_installed = $Persistent
            campaign_success = $true
        }
    }

    # Save consolidated report
    $json = ConvertTo-Json -InputObject $report -Depth 10
    Set-Content -Path $script:ReportFile -Value $json -Encoding UTF8

    Log-Message "Campaign report saved to: $($script:ReportFile)" SUCCESS

    return $report
}

# ============================================================================
# FINAL SUMMARY
# ============================================================================

function Show-CampaignSummary {
    param($FinalReport)

    Log-Message "=============================================" INFO
    Log-Message "CAMPAIGN SUMMARY" INFO
    Log-Message "=============================================" INFO

    $meta = $FinalReport.campaign_metadata
    $summary = $FinalReport.summary

    Log-Message "Campaign ID: $($meta.campaign_id)" INFO
    Log-Message "Target: $($meta.target):$($meta.target_port)" INFO
    Log-Message "Mode: $($meta.mode)" INFO
    Log-Message "Duration: $([math]::Round($meta.duration_seconds, 2))s" INFO
    Log-Message ""  INFO
    Log-Message "Results:" INFO
    Log-Message "  Total Iterations: $($summary.total_fuzz_iterations)" SUCCESS
    Log-Message "  Vulnerabilities Found: $($summary.total_vulnerabilities)" SUCCESS
    Log-Message "  Persistent Payload: $(if ($summary.persistent_payload_installed) {'Installed'} else {'Not Installed'})" INFO
    Log-Message ""  INFO
    Log-Message "Reports:" INFO
    Log-Message "  Campaign Report: $(Split-Path $script:ReportFile -Leaf)" INFO
    Log-Message "  Campaign Log: $(Split-Path $script:LogFile -Leaf)" INFO
    Log-Message "  Report Directory: $ReportDir" INFO
    Log-Message "=============================================" INFO
}

# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

function Start-AutomatedCampaign {
    Log-Message "=========================================" INFO
    Log-Message "FORTIOS AUTOMATED FUZZING CAMPAIGN" INFO
    Log-Message "=========================================" INFO
    Log-Message "Campaign Mode: $CampaignMode" INFO
    Log-Message "Campaign ID: $CampaignId" INFO
    Log-Message ""  INFO

    # Stage 1: Remote Fuzz
    $stage1Report = Invoke-Stage1-RemoteFuzz
    Log-Message ""  INFO

    # Stage 2: Local Fuzz (Code Injection)
    $stage2Report = Invoke-Stage2-LocalFuzz -Stage1Report $stage1Report
    Log-Message ""  INFO

    # Stage 3: Analysis
    Invoke-Stage3-Analysis -Stage1Report $stage1Report -Stage2Report $stage2Report
    Log-Message ""  INFO

    # Stage 4: Generate Final Report
    $finalReport = New-CampaignReport -Stage1Report $stage1Report -Stage2Report $stage2Report
    Log-Message ""  INFO

    # Display Summary
    Show-CampaignSummary -FinalReport $finalReport

    return $finalReport
}

# ============================================================================
# ENTRY POINT
# ============================================================================

Initialize-Logging
Start-AutomatedCampaign
