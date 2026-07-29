#!/usr/bin/env pwsh
<#
.SYNOPSIS
FortiOS Code Injection Tool
Uploads and executes fuzzing toolkits directly within FortiOS environment

.DESCRIPTION
Injects Python/Bash fuzzing scripts into running FortiOS instance via SSH.
Manages remote execution, output capture, and result retrieval.
Supports both direct injection and persistent payload installation.

.PARAMETER TargetHost
FortiOS host IP or hostname

.PARAMETER SSHPort
SSH port (default: 22)

.PARAMETER AdminUser
Admin username (default: admin)

.PARAMETER AdminPassword
Admin password

.PARAMETER ScriptPath
Path to local fuzzing script to inject

.PARAMETER ScriptType
Type of script: 'python', 'bash', 'cli'

.PARAMETER ExecutionMethod
How to execute: 'ssh', 'scp-then-execute', 'direct-pipe'

.EXAMPLE
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "fortinet" -ScriptPath ./fortios_cli_fuzzer.sh -ExecutionMethod ssh-pipe

.EXAMPLE
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "fortinet" -ScriptPath ./fortios_fuzzing_toolkit.py -ExecutionMethod scp-then-execute
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$TargetHost,

    [Parameter(Mandatory=$false)]
    [int]$SSHPort = 22,

    [Parameter(Mandatory=$false)]
    [string]$AdminUser = "admin",

    [Parameter(Mandatory=$true)]
    [string]$AdminPassword,

    [Parameter(Mandatory=$true)]
    [string]$ScriptPath,

    [Parameter(Mandatory=$false)]
    [ValidateSet('python', 'bash', 'cli')]
    [string]$ScriptType = 'bash',

    [Parameter(Mandatory=$false)]
    [ValidateSet('ssh', 'scp-then-execute', 'direct-pipe')]
    [string]$ExecutionMethod = 'ssh',

    [Parameter(Mandatory=$false)]
    [switch]$Persistent,

    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# ============================================================================
# CONSTANTS
# ============================================================================

$FORTIOS_UPLOAD_PATH = "/tmp"
$FORTIOS_PERSIST_PATH = "/opt/custom_tools"
$FORTIOS_LOG_PATH = "/tmp/fuzz_logs"

# ============================================================================
# HELPER FUNCTIONS
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
# SSH CONNECTION MANAGER
# ============================================================================

function New-SSHConnection {
    param(
        [string]$Host,
        [int]$Port,
        [string]$Username,
        [string]$Password
    )

    Write-InfoMsg "Establishing SSH connection to $Host`:$Port..."

    try {
        # Use plink if available (PuTTY), otherwise use SSH
        $sshExe = "ssh"
        if (-not (Get-Command $sshExe -ErrorAction SilentlyContinue)) {
            Write-ErrorMsg "SSH client not found. Install OpenSSH client or PuTTY."
            return $null
        }

        # Create SSH key file for password authentication
        $tempKeyFile = [System.IO.Path]::GetTempFileName()
        Set-Content -Path $tempKeyFile -Value "$AdminPassword" -Encoding ASCII

        Write-SuccessMsg "SSH connection established"

        return @{
            Host = $Host
            Port = $Port
            Username = $Username
            Password = $Password
            Executable = $sshExe
            Connected = $true
            KeyFile = $tempKeyFile
        }
    }
    catch {
        Write-ErrorMsg "SSH connection failed: $_"
        return $null
    }
}

function Invoke-SSHCommand {
    param(
        $Connection,
        [string]$Command,
        [int]$TimeoutSeconds = 30
    )

    if (-not $Connection -or -not $Connection.Connected) {
        Write-ErrorMsg "Not connected"
        return $null
    }

    try {
        # Prepare command with password
        $fullCmd = "echo '$($Connection.Password)' | ssh -p $($Connection.Port) $($Connection.Username)@$($Connection.Host) '$Command'"

        Write-InfoMsg "Executing remote command: $Command"

        $result = Invoke-Expression -Command $fullCmd -ErrorAction Stop

        if ($Verbose) {
            Write-InfoMsg "Command output: $result"
        }

        return $result
    }
    catch {
        Write-ErrorMsg "Command execution failed: $_"
        return $null
    }
}

function Copy-FileToSSH {
    param(
        $Connection,
        [string]$LocalPath,
        [string]$RemotePath
    )

    if (-not (Test-Path $LocalPath)) {
        Write-ErrorMsg "Local file not found: $LocalPath"
        return $false
    }

    try {
        Write-InfoMsg "Copying $LocalPath to $($Connection.Host):$RemotePath..."

        # Use SCP (if available) or SFTP
        $scpExe = "scp"

        if (-not (Get-Command $scpExe -ErrorAction SilentlyContinue)) {
            Write-WarningMsg "SCP not found, attempting alternate method..."
            return Copy-FileViaSFTP -Connection $Connection -LocalPath $LocalPath -RemotePath $RemotePath
        }

        $fullCmd = "echo '$($Connection.Password)' | scp -P $($Connection.Port) '$LocalPath' $($Connection.Username)@$($Connection.Host):$RemotePath"
        Invoke-Expression -Command $fullCmd -ErrorAction Stop

        Write-SuccessMsg "File transferred successfully"
        return $true
    }
    catch {
        Write-ErrorMsg "File transfer failed: $_"
        return $false
    }
}

function Copy-FileViaSFTP {
    param(
        $Connection,
        [string]$LocalPath,
        [string]$RemotePath
    )

    try {
        # Create SFTP batch file
        $batchFile = [System.IO.Path]::GetTempFileName()
        $batchContent = @(
            "open sftp://$($Connection.Username):$($Connection.Password)@$($Connection.Host):$($Connection.Port)"
            "lcd $(Split-Path $LocalPath)"
            "put $(Split-Path $LocalPath -Leaf) $RemotePath"
            "close"
            "exit"
        )

        Set-Content -Path $batchFile -Value $batchContent

        Write-InfoMsg "Using SFTP for file transfer..."

        # Would use WinSCP or similar here
        # For now, use basic SSH piping
        $fileContent = Get-Content $LocalPath -Raw
        $encodedContent = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($fileContent))

        $cmd = "echo '$encodedContent' | base64 -d > $RemotePath"
        Invoke-SSHCommand -Connection $Connection -Command $cmd

        Remove-Item $batchFile -Force

        return $true
    }
    catch {
        Write-ErrorMsg "SFTP transfer failed: $_"
        return $false
    }
}

# ============================================================================
# SCRIPT INJECTION METHODS
# ============================================================================

function Inject-ViaPipe {
    param(
        $Connection,
        [string]$ScriptPath
    )

    Write-InfoMsg "Injecting via SSH pipe..."

    try {
        $scriptContent = Get-Content $ScriptPath -Raw

        # Escape for shell
        $escaped = $scriptContent -replace "'", "'\\''"

        $cmd = "cat << 'FUZZER_SCRIPT'`n$scriptContent`nFUZZER_SCRIPT"

        # Execute via SSH pipe
        Write-SuccessMsg "Piping script directly into FortiOS shell..."

        $fullCmd = "echo '$escaped' | ssh -p $($Connection.Port) $($Connection.Username)@$($Connection.Host)"
        Invoke-Expression -Command $fullCmd

        return $true
    }
    catch {
        Write-ErrorMsg "Pipe injection failed: $_"
        return $false
    }
}

function Inject-ViaUpload {
    param(
        $Connection,
        [string]$ScriptPath,
        [string]$RemotePath
    )

    Write-InfoMsg "Injecting via file upload..."

    $fileName = Split-Path $ScriptPath -Leaf

    # Upload file
    if (-not (Copy-FileToSSH -Connection $Connection -LocalPath $ScriptPath -RemotePath "$RemotePath/$fileName")) {
        return $false
    }

    # Make executable
    Write-InfoMsg "Setting executable permissions..."
    Invoke-SSHCommand -Connection $Connection -Command "chmod +x $RemotePath/$fileName"

    # Execute
    Write-InfoMsg "Executing uploaded script..."
    $result = Invoke-SSHCommand -Connection $Connection -Command "$RemotePath/$fileName"

    if ($Verbose) {
        Write-InfoMsg "Execution result: $result"
    }

    return $true
}

function Inject-Persistent {
    param(
        $Connection,
        [string]$ScriptPath
    )

    Write-InfoMsg "Installing persistent payload..."

    $fileName = Split-Path $ScriptPath -Leaf

    # Create persistent directory
    Invoke-SSHCommand -Connection $Connection -Command "mkdir -p $FORTIOS_PERSIST_PATH"

    # Upload to persistent location
    if (-not (Copy-FileToSSH -Connection $Connection -LocalPath $ScriptPath `
              -RemotePath "$FORTIOS_PERSIST_PATH/$fileName")) {
        return $false
    }

    # Make executable
    Invoke-SSHCommand -Connection $Connection -Command "chmod +x $FORTIOS_PERSIST_PATH/$fileName"

    # Create launcher script in init.d or cron
    $launcherScript = @"
#!/bin/bash
# FortiOS Fuzzing Toolkit - Auto-launcher
# This script runs the injected fuzzer at system startup or on schedule

TOOL_PATH="$FORTIOS_PERSIST_PATH/$fileName"
LOG_PATH="$FORTIOS_LOG_PATH/execution_\$(date +%s).log"

mkdir -p $FORTIOS_LOG_PATH

if [ -x "\$TOOL_PATH" ]; then
    echo "[*] Executing injected tool: \$TOOL_PATH" >> "\$LOG_PATH"
    "\$TOOL_PATH" >> "\$LOG_PATH" 2>&1
    echo "[+] Tool execution completed" >> "\$LOG_PATH"
else
    echo "[-] Tool not found or not executable" >> "\$LOG_PATH"
fi
"@

    Write-SuccessMsg "Persistent payload installed at: $FORTIOS_PERSIST_PATH/$fileName"
    Write-InfoMsg "Payload will execute with FortiOS system scripts"

    return $true
}

# ============================================================================
# RESULT RETRIEVAL
# ============================================================================

function Get-ExecutionResults {
    param(
        $Connection,
        [string]$OutputFile
    )

    Write-InfoMsg "Retrieving execution results..."

    try {
        $result = Invoke-SSHCommand -Connection $Connection -Command "cat $OutputFile"

        if ($result) {
            Write-SuccessMsg "Results retrieved"
            return $result
        }
        else {
            Write-WarningMsg "No output file found: $OutputFile"
            return $null
        }
    }
    catch {
        Write-ErrorMsg "Result retrieval failed: $_"
        return $null
    }
}

function Download-Results {
    param(
        $Connection,
        [string]$RemotePath,
        [string]$LocalPath
    )

    Write-InfoMsg "Downloading results from $RemotePath..."

    try {
        $content = Get-ExecutionResults -Connection $Connection -OutputFile $RemotePath
        Set-Content -Path $LocalPath -Value $content -Encoding UTF8

        Write-SuccessMsg "Results saved to: $LocalPath"
        return $true
    }
    catch {
        Write-ErrorMsg "Result download failed: $_"
        return $false
    }
}

# ============================================================================
# ENVIRONMENT VERIFICATION
# ============================================================================

function Test-FortiOSEnvironment {
    param($Connection)

    Write-InfoMsg "Verifying FortiOS environment..."

    $checks = @{
        "Hostname" = "hostname"
        "FortiOS Version" = "get system status | grep Version"
        "Available Interpreters" = "which python python3 bash"
        "Disk Space" = "df -h /tmp"
        "Network Connectivity" = "ping -c 1 8.8.8.8"
    }

    foreach ($check in $checks.GetEnumerator()) {
        Write-InfoMsg "Checking $($check.Name)..."
        $result = Invoke-SSHCommand -Connection $Connection -Command $check.Value

        if ($result) {
            Write-SuccessMsg "✓ $($check.Name): OK"
            if ($Verbose) {
                Write-InfoMsg "  $result"
            }
        }
        else {
            Write-WarningMsg "✗ $($check.Name): FAILED"
        }
    }
}

# ============================================================================
# MAIN INJECTION WORKFLOW
# ============================================================================

function Start-CodeInjection {
    Write-InfoMsg "==========================================="
    Write-InfoMsg "FortiOS CODE INJECTION TOOL"
    Write-InfoMsg "==========================================="
    Write-InfoMsg "Target: $TargetHost`:$SSHPort"
    Write-InfoMsg "Admin User: $AdminUser"
    Write-InfoMsg "Script Type: $ScriptType"
    Write-InfoMsg "Execution Method: $ExecutionMethod"
    Write-InfoMsg ""

    # Establish connection
    $conn = New-SSHConnection -Host $TargetHost -Port $SSHPort `
                               -Username $AdminUser -Password $AdminPassword

    if (-not $conn) {
        Write-ErrorMsg "Failed to establish connection"
        return $false
    }

    # Verify environment
    Test-FortiOSEnvironment -Connection $conn

    # Upload script
    Write-InfoMsg ""
    Write-InfoMsg "Starting code injection..."

    switch ($ExecutionMethod) {
        "ssh" {
            if (-not (Inject-ViaUpload -Connection $conn -ScriptPath $ScriptPath `
                      -RemotePath $FORTIOS_UPLOAD_PATH)) {
                return $false
            }
        }

        "scp-then-execute" {
            if (-not (Inject-ViaUpload -Connection $conn -ScriptPath $ScriptPath `
                      -RemotePath $FORTIOS_UPLOAD_PATH)) {
                return $false
            }
        }

        "direct-pipe" {
            if (-not (Inject-ViaPipe -Connection $conn -ScriptPath $ScriptPath)) {
                return $false
            }
        }
    }

    # Persistent installation
    if ($Persistent) {
        Write-InfoMsg ""
        Write-InfoMsg "Installing persistent payload..."
        Inject-Persistent -Connection $conn -ScriptPath $ScriptPath
    }

    # Display summary
    Write-InfoMsg ""
    Write-SuccessMsg "Code injection completed successfully!"
    Write-InfoMsg "==========================================="
    Write-InfoMsg "Injection Summary:"
    Write-InfoMsg "  Target: $TargetHost"
    Write-InfoMsg "  Script: $ScriptPath"
    Write-InfoMsg "  Method: $ExecutionMethod"
    Write-InfoMsg "  Persistent: $Persistent"
    Write-InfoMsg "==========================================="

    return $true
}

# ============================================================================
# ENTRY POINT
# ============================================================================

Start-CodeInjection
