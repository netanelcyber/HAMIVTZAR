#Requires -Version 5.1
<#
.SYNOPSIS
    Remediates the common Windows Server 2019 vulnerabilities/misconfigurations
    documented in ../FINDINGS.md.

.DESCRIPTION
    By default this is a DRY RUN: it prints every change it would make
    without touching the system. Pass -Apply to actually make the changes.
    Requires an elevated (Run as Administrator) PowerShell session when
    -Apply is used.

    Individual fixes can be excluded via -Skip, using the same Id used in
    FINDINGS.md / Audit-WinServer2019.ps1 (Smb1, SmbSigning, RdpNla,
    PrintSpooler, Netlogon, WeakTls, LlmnrNbtNs, WDigest, LsaProtection,
    NtlmV1, AnonEnum, GuestAccount, PasswordPolicy, PowerShellV2, Firewall,
    Defender).

    Some changes (SMBv1 removal, PowerShell v2 removal, LSA protection)
    require a reboot to take effect.

.PARAMETER Apply
    Actually perform the changes. Without this switch, the script only
    prints what it would do.

.PARAMETER Skip
    Array of finding Ids to leave alone (e.g. -Skip PrintSpooler,RdpNla).

.EXAMPLE
    .\Harden-WinServer2019.ps1
    .\Harden-WinServer2019.ps1 -Apply
    .\Harden-WinServer2019.ps1 -Apply -Skip PrintSpooler,RdpNla
#>
[CmdletBinding()]
param(
    [switch]$Apply,
    [string[]]$Skip = @()
)

$ErrorActionPreference = 'Stop'
$rebootRequired = $false

function Invoke-Fix {
    param(
        [Parameter(Mandatory)][string]$Id,
        [Parameter(Mandatory)][string]$Description,
        [Parameter(Mandatory)][scriptblock]$Action,
        [switch]$NeedsReboot
    )
    if ($Skip -contains $Id) {
        Write-Host "[SKIP] $Id - $Description" -ForegroundColor DarkGray
        return
    }
    if (-not $Apply) {
        Write-Host "[DRY-RUN] $Id - $Description" -ForegroundColor Yellow
        return
    }
    try {
        & $Action
        Write-Host "[APPLIED] $Id - $Description" -ForegroundColor Green
        if ($NeedsReboot) { $script:rebootRequired = $true }
    } catch {
        Write-Host "[ERROR] $Id - $Description :: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Set-RegValue {
    param([string]$Path, [string]$Name, $Value, [string]$Type = 'DWord')
    if (-not (Test-Path $Path)) { New-Item -Path $Path -Force | Out-Null }
    New-ItemProperty -Path $Path -Name $Name -Value $Value -PropertyType $Type -Force | Out-Null
}

if ($Apply -and -not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated (Administrator) PowerShell session to use -Apply."
}

if (-not $Apply) {
    Write-Host "Running in DRY-RUN mode. No changes will be made. Pass -Apply to apply fixes.`n" -ForegroundColor Cyan
}

# --- Smb1 -------------------------------------------------------------
Invoke-Fix -Id 'Smb1' -Description 'Disable SMBv1 protocol feature' -NeedsReboot -Action {
    Disable-WindowsOptionalFeature -Online -FeatureName SMB1Protocol -NoRestart -ErrorAction SilentlyContinue | Out-Null
}

# --- SmbSigning ---------------------------------------------------------
Invoke-Fix -Id 'SmbSigning' -Description 'Require SMB signing (server + workstation)' -Action {
    Set-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' 'RequireSecuritySignature' 1
    Set-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters' 'RequireSecuritySignature' 1
}

# --- RdpNla ---------------------------------------------------------
Invoke-Fix -Id 'RdpNla' -Description 'Enable Network Level Authentication for RDP' -Action {
    Set-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' 'UserAuthentication' 1
}

# --- PrintSpooler ---------------------------------------------------------
Invoke-Fix -Id 'PrintSpooler' -Description 'Disable Print Spooler service (PrintNightmare)' -Action {
    Stop-Service -Name Spooler -Force -ErrorAction SilentlyContinue
    Set-Service -Name Spooler -StartupType Disabled
    Set-RegValue 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Printers\PointAndPrint' 'RestrictDriverInstallationToAdministrators' 1
}

# --- Netlogon (Zerologon) ------------------------------------------------
Invoke-Fix -Id 'Netlogon' -Description 'Enforce Netlogon secure channel (Zerologon)' -Action {
    Set-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters' 'FullSecureChannelProtection' 1
}

# --- WeakTls ---------------------------------------------------------
Invoke-Fix -Id 'WeakTls' -Description 'Disable SSL 2.0/3.0, TLS 1.0/1.1, and weak ciphers; enable TLS 1.2' -Action {
    $weakProtocols = @('SSL 2.0', 'SSL 3.0', 'TLS 1.0', 'TLS 1.1')
    foreach ($proto in $weakProtocols) {
        foreach ($side in @('Server', 'Client')) {
            $path = "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\$proto\$side"
            Set-RegValue $path 'Enabled' 0
            Set-RegValue $path 'DisabledByDefault' 1
        }
    }
    foreach ($side in @('Server', 'Client')) {
        $path = "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.2\$side"
        Set-RegValue $path 'Enabled' 1
        Set-RegValue $path 'DisabledByDefault' 0
    }
    $weakCiphers = @('RC4 128/128', 'RC4 64/128', 'RC4 56/128', 'RC4 40/128', 'DES 56/56', 'Triple DES 168', 'NULL')
    foreach ($cipher in $weakCiphers) {
        $path = "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Ciphers\$cipher"
        Set-RegValue $path 'Enabled' 0
    }
}

# --- LlmnrNbtNs ---------------------------------------------------------
Invoke-Fix -Id 'LlmnrNbtNs' -Description 'Disable LLMNR and NetBIOS name resolution' -Action {
    Set-RegValue 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient' 'EnableMulticast' 0
    $adapters = Get-CimInstance Win32_NetworkAdapterConfiguration -Filter 'IPEnabled = TRUE'
    foreach ($adapter in $adapters) {
        # TcpipNetbiosOptions: 0=default(DHCP), 1=enable, 2=disable
        Invoke-CimMethod -InputObject $adapter -MethodName SetTcpipNetbios -Arguments @{ TcpipNetbiosOptions = 2 } | Out-Null
    }
}

# --- WDigest ---------------------------------------------------------
Invoke-Fix -Id 'WDigest' -Description 'Disable WDigest plaintext credential caching' -Action {
    Set-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' 'UseLogonCredential' 0
}

# --- LsaProtection ---------------------------------------------------------
Invoke-Fix -Id 'LsaProtection' -Description 'Enable LSA protection (RunAsPPL)' -NeedsReboot -Action {
    Set-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' 'RunAsPPL' 1
}

# --- NtlmV1 ---------------------------------------------------------
Invoke-Fix -Id 'NtlmV1' -Description 'Restrict authentication to NTLMv2 only' -Action {
    Set-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' 'LmCompatibilityLevel' 5
}

# --- AnonEnum ---------------------------------------------------------
Invoke-Fix -Id 'AnonEnum' -Description 'Restrict anonymous SAM/share enumeration' -Action {
    Set-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' 'RestrictAnonymous' 1
    Set-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' 'RestrictAnonymousSAM' 1
}

# --- GuestAccount ---------------------------------------------------------
Invoke-Fix -Id 'GuestAccount' -Description 'Disable built-in Guest account' -Action {
    Disable-LocalUser -Name 'Guest' -ErrorAction SilentlyContinue
}

# --- PasswordPolicy ---------------------------------------------------------
Invoke-Fix -Id 'PasswordPolicy' -Description 'Enforce minimum password length 14 and account lockout policy' -Action {
    net accounts /minpwlen:14 /lockoutthreshold:5 /lockoutduration:15 /lockoutwindow:15 | Out-Null
}

# --- PowerShellV2 ---------------------------------------------------------
Invoke-Fix -Id 'PowerShellV2' -Description 'Remove legacy PowerShell v2 engine' -NeedsReboot -Action {
    Disable-WindowsOptionalFeature -Online -FeatureName MicrosoftWindowsPowerShellV2Root -NoRestart -ErrorAction SilentlyContinue | Out-Null
}

# --- Firewall ---------------------------------------------------------
Invoke-Fix -Id 'Firewall' -Description 'Enable Windows Firewall on all profiles' -Action {
    Set-NetFirewallProfile -Profile Domain, Public, Private -Enabled True
}

# --- Defender ---------------------------------------------------------
Invoke-Fix -Id 'Defender' -Description 'Enable Windows Defender real-time protection' -Action {
    if (Get-Command Set-MpPreference -ErrorAction SilentlyContinue) {
        Set-MpPreference -DisableRealtimeMonitoring $false
    }
}

Write-Host ''
if (-not $Apply) {
    Write-Host 'Dry run complete. Re-run with -Apply to make these changes.' -ForegroundColor Cyan
} elseif ($rebootRequired) {
    Write-Host 'One or more changes require a reboot to take effect (SMBv1 removal, PowerShell v2 removal, LSA protection).' -ForegroundColor Yellow
} else {
    Write-Host 'Hardening complete.' -ForegroundColor Green
}

Write-Host 'Reminder: these are defense-in-depth mitigations, not a substitute for keeping Windows Update current (BlueKeep/Zerologon/PrintNightmare all have security-update fixes too).'
