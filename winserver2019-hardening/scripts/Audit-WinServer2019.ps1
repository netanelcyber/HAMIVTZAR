#Requires -Version 5.1
<#
.SYNOPSIS
    Read-only security audit for the common Windows Server 2019
    vulnerabilities/misconfigurations documented in ../FINDINGS.md.

.DESCRIPTION
    Makes NO changes to the system. Checks each finding's current state and
    prints a PASS/FAIL report. Intended to be run before and after
    Harden-WinServer2019.ps1 to verify effect.

.PARAMETER ReportPath
    Optional file path to also write the report to (in addition to stdout).

.EXAMPLE
    .\Audit-WinServer2019.ps1
    .\Audit-WinServer2019.ps1 -ReportPath .\output\audit-report.txt
#>
[CmdletBinding()]
param(
    [string]$ReportPath
)

$ErrorActionPreference = 'Stop'
$results = [System.Collections.Generic.List[object]]::new()

function Add-Result {
    param([string]$Id, [string]$Severity, [string]$Title, [bool]$Pass, [string]$Detail)
    $results.Add([pscustomobject]@{
        Id       = $Id
        Severity = $Severity
        Title    = $Title
        Status   = if ($Pass) { 'PASS' } else { 'FAIL' }
        Detail   = $Detail
    })
}

function Get-RegValue {
    param([string]$Path, [string]$Name, $Default = $null)
    try {
        $item = Get-ItemProperty -Path $Path -Name $Name -ErrorAction Stop
        return $item.$Name
    } catch {
        return $Default
    }
}

# --- Smb1 -------------------------------------------------------------
try {
    $smb1 = Get-WindowsOptionalFeature -Online -FeatureName SMB1Protocol -ErrorAction Stop
    Add-Result 'Smb1' 'Critical' 'SMBv1 enabled (EternalBlue/WannaCry)' `
        ($smb1.State -eq 'Disabled') "State=$($smb1.State)"
} catch {
    Add-Result 'Smb1' 'Critical' 'SMBv1 enabled (EternalBlue/WannaCry)' $true 'Feature not present'
}

# --- SmbSigning ---------------------------------------------------------
$srvSig = Get-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' 'RequireSecuritySignature' 0
Add-Result 'SmbSigning' 'High' 'SMB signing not required' ($srvSig -eq 1) "RequireSecuritySignature=$srvSig"

# --- RdpNla ---------------------------------------------------------
$nla = Get-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' 'UserAuthentication' 0
Add-Result 'RdpNla' 'Critical' 'RDP without Network Level Authentication' ($nla -eq 1) "UserAuthentication=$nla"

# --- PrintSpooler ---------------------------------------------------------
try {
    $spooler = Get-Service -Name Spooler -ErrorAction Stop
    Add-Result 'PrintSpooler' 'Critical' 'Print Spooler running (PrintNightmare)' `
        ($spooler.Status -eq 'Stopped') "Status=$($spooler.Status) StartType=$($spooler.StartType)"
} catch {
    Add-Result 'PrintSpooler' 'Critical' 'Print Spooler running (PrintNightmare)' $true 'Service not present'
}

# --- Netlogon (Zerologon) ------------------------------------------------
$zl = Get-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters' 'FullSecureChannelProtection' 0
Add-Result 'Netlogon' 'Critical' 'Zerologon mitigation not enforced' ($zl -eq 1) "FullSecureChannelProtection=$zl"

# --- WeakTls ---------------------------------------------------------
$weakProtocols = @('SSL 2.0', 'SSL 3.0', 'TLS 1.0', 'TLS 1.1')
$enabledWeak = @()
foreach ($proto in $weakProtocols) {
    $base = "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\$proto"
    foreach ($side in @('Server', 'Client')) {
        $enabled = Get-RegValue "$base\$side" 'Enabled' 1  # SChannel default is enabled if key absent
        if ($enabled -ne 0) { $enabledWeak += "$proto/$side" }
    }
}
Add-Result 'WeakTls' 'High' 'Deprecated TLS/SSL protocols enabled' ($enabledWeak.Count -eq 0) `
    ($(if ($enabledWeak.Count -eq 0) { 'All disabled' } else { "Enabled: $($enabledWeak -join ', ')" }))

# --- LlmnrNbtNs ---------------------------------------------------------
$llmnr = Get-RegValue 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient' 'EnableMulticast' 1
Add-Result 'LlmnrNbtNs' 'Medium' 'LLMNR enabled' ($llmnr -eq 0) "EnableMulticast=$llmnr"

# --- WDigest ---------------------------------------------------------
$wdigest = Get-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' 'UseLogonCredential' 1
Add-Result 'WDigest' 'High' 'WDigest credential caching enabled' ($wdigest -eq 0) "UseLogonCredential=$wdigest"

# --- LsaProtection ---------------------------------------------------------
$runAsPPL = Get-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' 'RunAsPPL' 0
Add-Result 'LsaProtection' 'High' 'LSA protection (RunAsPPL) not enabled' ($runAsPPL -eq 1) "RunAsPPL=$runAsPPL"

# --- NtlmV1 ---------------------------------------------------------
$lmLevel = Get-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' 'LmCompatibilityLevel' 3
Add-Result 'NtlmV1' 'Medium' 'NTLMv1/LM authentication permitted' ($lmLevel -ge 5) "LmCompatibilityLevel=$lmLevel"

# --- AnonEnum ---------------------------------------------------------
$restrictAnon = Get-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' 'RestrictAnonymous' 0
$restrictAnonSam = Get-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' 'RestrictAnonymousSAM' 0
Add-Result 'AnonEnum' 'Medium' 'Anonymous SAM/share enumeration allowed' `
    (($restrictAnon -eq 1) -and ($restrictAnonSam -eq 1)) `
    "RestrictAnonymous=$restrictAnon RestrictAnonymousSAM=$restrictAnonSam"

# --- GuestAccount ---------------------------------------------------------
try {
    $guest = Get-LocalUser -Name 'Guest' -ErrorAction Stop
    Add-Result 'GuestAccount' 'Medium' 'Built-in Guest account enabled' (-not $guest.Enabled) "Enabled=$($guest.Enabled)"
} catch {
    Add-Result 'GuestAccount' 'Medium' 'Built-in Guest account enabled' $true 'Account not found'
}

# --- PasswordPolicy ---------------------------------------------------------
$netAccounts = net accounts 2>$null
$minLenLine = $netAccounts | Where-Object { $_ -match 'Minimum password length' }
$minLen = 0
if ($minLenLine -and ($minLenLine -match '(\d+)')) { $minLen = [int]$Matches[1] }
$lockoutLine = $netAccounts | Where-Object { $_ -match 'Lockout threshold' }
$lockoutThreshold = $null
if ($lockoutLine -and ($lockoutLine -match '(\d+|Never)')) { $lockoutThreshold = $Matches[1] }
$passPass = ($minLen -ge 14) -and ($lockoutThreshold -and $lockoutThreshold -ne 'Never' -and $lockoutThreshold -ne '0')
Add-Result 'PasswordPolicy' 'Medium' 'Weak local password/lockout policy' $passPass `
    "MinLength=$minLen LockoutThreshold=$lockoutThreshold"

# --- PowerShellV2 ---------------------------------------------------------
try {
    $psv2 = Get-WindowsOptionalFeature -Online -FeatureName MicrosoftWindowsPowerShellV2Root -ErrorAction Stop
    Add-Result 'PowerShellV2' 'Medium' 'PowerShell v2 engine installed' ($psv2.State -eq 'Disabled') "State=$($psv2.State)"
} catch {
    Add-Result 'PowerShellV2' 'Medium' 'PowerShell v2 engine installed' $true 'Feature not present'
}

# --- Firewall ---------------------------------------------------------
try {
    $profiles = Get-NetFirewallProfile -ErrorAction Stop
    $disabled = $profiles | Where-Object { -not $_.Enabled }
    Add-Result 'Firewall' 'Low' 'Windows Firewall disabled on a profile' ($disabled.Count -eq 0) `
        ($(if ($disabled.Count -eq 0) { 'All profiles enabled' } else { "Disabled: $($disabled.Name -join ', ')" }))
} catch {
    Add-Result 'Firewall' 'Low' 'Windows Firewall disabled on a profile' $false 'Unable to query firewall profiles'
}

# --- Defender ---------------------------------------------------------
try {
    $mp = Get-MpComputerStatus -ErrorAction Stop
    Add-Result 'Defender' 'Low' 'Defender real-time protection disabled' `
        $mp.RealTimeProtectionEnabled "RealTimeProtectionEnabled=$($mp.RealTimeProtectionEnabled)"
} catch {
    Add-Result 'Defender' 'Low' 'Defender real-time protection disabled' $true 'Defender not present (third-party AV assumed)'
}

# --- Report ---------------------------------------------------------
$sevOrder = @{ Critical = 0; High = 1; Medium = 2; Low = 3; Info = 4 }
$sorted = $results | Sort-Object { $sevOrder[$_.Severity] }, Id

$lines = @()
$lines += "Windows Server 2019 Security Audit — $(Get-Date -Format u)"
$lines += "Host: $env:COMPUTERNAME"
$lines += ''
$lines += ($sorted | Format-Table -AutoSize Status, Severity, Id, Title, Detail | Out-String)

$failCount = ($sorted | Where-Object Status -eq 'FAIL').Count
$lines += "Summary: $($sorted.Count) checks, $failCount FAIL, $($sorted.Count - $failCount) PASS"

$output = $lines -join "`n"
Write-Output $output

if ($ReportPath) {
    $dir = Split-Path -Parent $ReportPath
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $output | Out-File -FilePath $ReportPath -Encoding utf8
    Write-Host "`nReport written to $ReportPath"
}
