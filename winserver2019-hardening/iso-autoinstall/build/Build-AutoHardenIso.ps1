#Requires -Version 5.1
<#
.SYNOPSIS
    Injects the Windows Server 2019 auto-hardening files into a source ISO
    and repacks a new bootable ISO, using the Windows ADK's oscdimg.exe.

.DESCRIPTION
    1. Mounts the source ISO.
    2. Copies its contents to a staging folder.
    3. Drops sources\$OEM$\$$\Setup\Scripts\SetupComplete.cmd (which runs
       Harden-WinServer2019.ps1 -Apply automatically at the end of Setup,
       as SYSTEM, before any logon) plus the hardening scripts themselves
       into the staging tree.
    4. Optionally copies autounattend.xml to the staging root (see
       -IncludeAnswerFile — this makes the install itself unattended and
       WIPES the target disk; off by default).
    5. Rebuilds a bootable ISO with oscdimg, preserving the source ISO's
       BIOS + UEFI boot images.

.PARAMETER SourceIsoPath
    Path to the original Windows Server 2019 ISO.

.PARAMETER OutputIsoPath
    Path to write the new ISO to.

.PARAMETER IncludeAnswerFile
    Also copy ..\autounattend.xml to the ISO root, making the whole install
    unattended. WIPES Disk 0 on the target machine with no prompt - see
    ../README.md before using this.

.PARAMETER Skip
    Finding Ids to pass through as -Skip to Harden-WinServer2019.ps1 at
    install time (e.g. PrintSpooler,RdpNla).

.PARAMETER OscdimgPath
    Path to oscdimg.exe if it's not on PATH. Defaults to the standard
    Windows ADK Deployment Tools install location.

.EXAMPLE
    .\Build-AutoHardenIso.ps1 -SourceIsoPath D:\iso\WS2019.iso -OutputIsoPath D:\iso\WS2019-autoharden.iso
.EXAMPLE
    .\Build-AutoHardenIso.ps1 -SourceIsoPath D:\iso\WS2019.iso -OutputIsoPath D:\iso\WS2019-autoharden.iso -IncludeAnswerFile -Skip PrintSpooler
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$SourceIsoPath,
    [Parameter(Mandatory)][string]$OutputIsoPath,
    [switch]$IncludeAnswerFile,
    [string[]]$Skip = @(),
    [string]$OscdimgPath = "${env:ProgramFiles(x86)}\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe"
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $SourceIsoPath)) { throw "Source ISO not found: $SourceIsoPath" }

$oscdimg = $OscdimgPath
if (-not (Test-Path $oscdimg)) {
    $onPath = Get-Command oscdimg.exe -ErrorAction SilentlyContinue
    if ($onPath) { $oscdimg = $onPath.Source }
    else {
        throw "oscdimg.exe not found. Install the Windows ADK 'Deployment Tools' feature " +
              "(https://learn.microsoft.com/windows-hardware/get-started/adk-install), or pass -OscdimgPath."
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$isoAutoinstallDir = Resolve-Path (Join-Path $PSScriptRoot '..')
$scriptsDir = Join-Path $repoRoot 'scripts'

$staging = Join-Path $env:TEMP "autoharden-iso-$(Get-Date -Format yyyyMMddHHmmss)"
New-Item -ItemType Directory -Path $staging -Force | Out-Null

Write-Host "Mounting $SourceIsoPath ..."
$mount = Mount-DiskImage -ImagePath $SourceIsoPath -PassThru
try {
    $vol = $mount | Get-Volume
    $driveLetter = "$($vol.DriveLetter):"

    Write-Host "Copying ISO contents to staging folder ($staging) ..."
    # /E: all subdirs incl. empty, /R:1 /W:1: don't hang on transient errors,
    # exit codes 0-7 from robocopy are success, not failure.
    robocopy "$driveLetter\" $staging /E /R:1 /W:1 /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed copying ISO contents (exit $LASTEXITCODE)" }

    $oemScriptsDir = Join-Path $staging 'sources\$OEM$\$$\Setup\Scripts'
    $hardeningDestDir = Join-Path $oemScriptsDir 'hardening'
    New-Item -ItemType Directory -Path $hardeningDestDir -Force | Out-Null

    Copy-Item (Join-Path $scriptsDir 'Harden-WinServer2019.ps1') $hardeningDestDir -Force
    Copy-Item (Join-Path $scriptsDir 'Audit-WinServer2019.ps1') $hardeningDestDir -Force

    $setupCompleteSrc = Join-Path $isoAutoinstallDir 'oem\$OEM$\$$\Setup\Scripts\SetupComplete.cmd'
    $setupCompleteContent = Get-Content $setupCompleteSrc -Raw
    if ($Skip.Count -gt 0) {
        $skipArg = " -Skip " + ($Skip -join ',')
        $setupCompleteContent = $setupCompleteContent -replace `
            '(Harden-WinServer2019\.ps1" -Apply)', "`$1$skipArg"
    }
    Set-Content -Path (Join-Path $oemScriptsDir 'SetupComplete.cmd') -Value $setupCompleteContent -Encoding ascii

    if ($IncludeAnswerFile) {
        Write-Host "Including autounattend.xml at ISO root (unattended install, WIPES Disk 0)." -ForegroundColor Yellow
        Copy-Item (Join-Path $isoAutoinstallDir 'autounattend.xml') (Join-Path $staging 'autounattend.xml') -Force
    }

    $etfsboot = Join-Path $staging 'boot\etfsboot.com'
    $efisys = Join-Path $staging 'efi\microsoft\boot\efisys.bin'
    if (-not (Test-Path $etfsboot) -or -not (Test-Path $efisys)) {
        throw "Couldn't find boot images ($etfsboot / $efisys) in the source ISO - is this a standard bootable Server 2019 media?"
    }

    Write-Host "Building $OutputIsoPath with oscdimg ..."
    $bootData = "2#p0,e,b$etfsboot#pEF,e,b$efisys"
    & $oscdimg -m -o -u2 -udfver102 "-bootdata:$bootData" -lWS2019_AUTOHARDEN $staging $OutputIsoPath
    if ($LASTEXITCODE -ne 0) { throw "oscdimg failed (exit $LASTEXITCODE)" }

    Write-Host "Done: $OutputIsoPath" -ForegroundColor Green
}
finally {
    Dismount-DiskImage -ImagePath $SourceIsoPath | Out-Null
    Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
}
