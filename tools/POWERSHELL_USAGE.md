# FortiOS PowerShell Fuzzing Toolkit - Usage Guide

## Overview

The PowerShell implementation provides Windows-native fuzzing capabilities with equivalent functionality to Python and Bash versions.

## Prerequisites

- PowerShell 5.1 or higher
- .NET Framework 4.5+
- For SSH injection: OpenSSH client (Windows 10+ built-in) or PuTTY
- For SSL connections: .NET SSL/TLS support (built-in)

## Available Tools

### 1. fortios_fuzzing_toolkit.ps1
Main fuzzing campaign runner for Windows environments.

**Features:**
- 5 endpoint-specific fuzzing strategies
- SSL/TLS connection handling via .NET
- Automatic vulnerability detection
- JSON report generation (compatible with Python version)
- Progress tracking and real-time status

**Basic Usage:**
```powershell
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50 -TargetPort 8443 -IterationsPerEndpoint 100
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| TargetHost | string | Required | Target FortiOS IP/hostname |
| TargetPort | int | 8443 | SSL-VPN port |
| IterationsPerEndpoint | int | 100 | Mutations per endpoint |
| Verbose | switch | false | Enable detailed output |

**Examples:**

```powershell
# Quick fuzz (100 iterations each)
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50

# Comprehensive fuzz (500 iterations)
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50 -IterationsPerEndpoint 500

# Verbose output
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50 -Verbose

# Custom port
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50 -TargetPort 9443
```

**Output:**
- Console: Real-time progress and results
- JSON Report: `fortios_fuzz_report_<ip>_<timestamp>.json`

**Example Report Structure:**
```json
{
  "target": "192.168.1.50",
  "port": 8443,
  "timestamp": "2026-07-29T12:34:56Z",
  "total_crashes": 25,
  "total_iterations": 500,
  "vulnerabilities_by_type": {
    "Authentication Bypass": 5,
    "Format String": 8,
    "Buffer Overflow": 7,
    "Path Traversal": 3,
    "Denial of Service": 2
  },
  "crashes": [...]
}
```

---

### 2. fortios_code_injector.ps1
Injects fuzzing code directly into running FortiOS instances via SSH.

**Features:**
- SSH connection management
- Multi-method code injection (SSH pipe, SCP+execute, direct piping)
- Persistent payload installation
- FortiOS environment verification
- Result retrieval and logging

**Basic Usage:**
```powershell
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh -ExecutionMethod ssh
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| TargetHost | string | Required | FortiOS IP/hostname |
| SSHPort | int | 22 | SSH port |
| AdminUser | string | admin | Admin username |
| AdminPassword | string | Required | Admin password |
| ScriptPath | string | Required | Local script to inject |
| ScriptType | string | bash | Script type: python, bash, cli |
| ExecutionMethod | string | ssh | Method: ssh, scp-then-execute, direct-pipe |
| Persistent | switch | false | Install as persistent payload |
| Verbose | switch | false | Enable detailed output |

**Execution Methods:**

1. **SSH** - Upload via SCP, execute via SSH
   ```powershell
   .\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "pass" `
       -ScriptPath ./fortios_cli_fuzzer.sh -ExecutionMethod ssh
   ```

2. **SCP+Execute** - Same as SSH, explicit
   ```powershell
   .\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "pass" `
       -ScriptPath ./fortios_cli_fuzzer.sh -ExecutionMethod scp-then-execute
   ```

3. **Direct Pipe** - Pipe script directly into shell
   ```powershell
   .\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "pass" `
       -ScriptPath ./fortios_cli_fuzzer.sh -ExecutionMethod direct-pipe
   ```

4. **Persistent** - Install as auto-executing payload
   ```powershell
   .\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "pass" `
       -ScriptPath ./fortios_cli_fuzzer.sh -Persistent
   ```

**Examples:**

```powershell
# Inject Bash fuzzer via SSH
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh -ScriptType bash

# Inject Python fuzzer via SCP
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "fortinet" `
    -ScriptPath ./fortios_fuzzing_toolkit.py -ScriptType python `
    -ExecutionMethod scp-then-execute

# Install persistent payload
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh -Persistent -Verbose

# Pipe directly (no file transfer)
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh -ExecutionMethod direct-pipe
```

**SSH Requirements:**
- FortiOS SSH service must be enabled
- Admin credentials required
- SSH key-based auth not supported (password auth only)

**Output:**
- Console: Injection status and results
- Remote Log: `/tmp/fuzz_logs/execution_<timestamp>.log`

---

## Execution Scenarios

### Scenario 1: Quick Local Fuzz (Windows Workstation)
```powershell
# Run direct fuzzing from Windows against lab FortiOS
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50 -IterationsPerEndpoint 50

# Check results
Get-Content fortios_fuzz_report_*.json | ConvertFrom-Json | Format-Table
```

### Scenario 2: Deep Fuzz + Code Injection
```powershell
# Step 1: Pre-fuzz from Windows to discover vulnerabilities
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50 -IterationsPerEndpoint 200 -Verbose

# Step 2: Inject fuzzer directly into FortiOS
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh -ExecutionMethod ssh

# Step 3: Analyze combined results
```

### Scenario 3: Persistent Payload Installation
```powershell
# Install fuzzer as auto-executing payload
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 `
    -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh `
    -Persistent

# FortiOS will now execute fuzzer automatically on reboot/system startup
```

### Scenario 4: Multiple Endpoints
```powershell
# Fuzz multiple FortiOS instances
$targets = @("192.168.1.50", "192.168.1.51", "192.168.1.52")

foreach ($target in $targets) {
    Write-Host "[*] Fuzzing $target..."
    .\fortios_fuzzing_toolkit.ps1 -TargetHost $target -IterationsPerEndpoint 100
}

# Combine all reports
Get-Content fortios_fuzz_report_*.json | 
    ForEach-Object { ConvertFrom-Json $_ } | 
    Export-Csv -Path combined_results.csv
```

---

## Output Formats

### Console Output Example:
```
[*] =========================================
[*] FORTIOS 8.0.0 FUZZING CAMPAIGN (PowerShell)
[*] =========================================
[*] Target: 192.168.1.50:8443

[*] Fuzzing: SSL-VPN Auth
[*] Iterations: 100
[!] CRASH at iter 5: Authentication Bypass
[!] CRASH at iter 23: Buffer Overflow
[+] Progress: 25/100
...
[+] SSL-VPN Auth: 5 vulnerabilities found

[+] =========================================
[+] CAMPAIGN SUMMARY
[+] =========================================
[+] Total Iterations: 500
[+] Total Vulnerabilities Found: 25

[!] VULNERABILITIES DETECTED:
[!]   [5] Authentication Bypass
[!]   [8] Format String
[!]   [7] Buffer Overflow
[!]   [3] Path Traversal
[!]   [2] Denial of Service
[+] =========================================
```

### JSON Report Example:
```json
{
  "target": "192.168.1.50",
  "port": 8443,
  "timestamp": "2026-07-29T14:23:45.123456Z",
  "total_crashes": 25,
  "total_iterations": 500,
  "vulnerabilities_by_type": {
    "Authentication Bypass": 5,
    "Format String": 8,
    "Buffer Overflow": 7,
    "Path Traversal": 3,
    "Denial of Service": 2
  },
  "crashes": [
    {
      "iteration": 5,
      "type": "Authentication Bypass",
      "payload_size": 256,
      "response_size": 1024,
      "timestamp": "2026-07-29T14:23:47Z"
    },
    ...
  ]
}
```

---

## Troubleshooting

### Issue: "SSL connection timeout"
**Solution:** Check network connectivity and port 8443 is accessible
```powershell
Test-NetConnection -ComputerName 192.168.1.50 -Port 8443
```

### Issue: "SSH connection refused"
**Solution:** Verify SSH is enabled on FortiOS and credentials are correct
```powershell
# Test SSH connectivity
ssh -p 22 admin@192.168.1.50

# Enable SSH on FortiOS (if disabled)
# Login to web UI → System Settings → Administration → Access Profile
```

### Issue: "No vulnerabilities detected"
**Solution:** Increase iteration count or verify target is vulnerable version
```powershell
# Run more comprehensive fuzz
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50 -IterationsPerEndpoint 500 -Verbose
```

### Issue: "File transfer failed (SCP)"
**Solution:** Use direct-pipe method instead
```powershell
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "pass" `
    -ScriptPath ./fortios_cli_fuzzer.sh -ExecutionMethod direct-pipe
```

---

## Comparison: Python vs PowerShell vs Bash

| Feature | Python | PowerShell | Bash |
|---------|--------|-----------|------|
| Native Windows | ✓ | ✓ | ✗ (WSL/Cygwin) |
| Native Linux/FortiOS | ✓ | ✗ | ✓ |
| SSL Support | ✓ | ✓ | ✓ (netcat) |
| SSH Support | ✓ | ✓ | ✓ |
| Report Format | JSON | JSON | JSON |
| Compatibility | Any Python 3.6+ | PowerShell 5.1+ | Bash 4.0+ |
| Execution Time (100 iter) | ~45s | ~60s | ~30s |

---

## Integration with CI/CD

### PowerShell Script in GitHub Actions:
```yaml
name: FortiOS Fuzz Test

on: [push]

jobs:
  fuzz:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run FortiOS Fuzzer
        run: |
          .\tools\fortios_fuzzing_toolkit.ps1 `
            -TargetHost ${{ secrets.FORTIOS_HOST }} `
            -Verbose
      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: fuzz-results
          path: fortios_fuzz_report_*.json
```

---

## Security Considerations

⚠️ **Important:**
- Only use on authorized, isolated lab environments
- Inject code only with explicit permission
- Store credentials securely (use -AdminPassword parameter cautiously)
- Consider using credential managers or environment variables:
  ```powershell
  $password = Read-Host -AsSecureString "Enter admin password"
  .\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword ($password | ConvertFrom-SecureString)
  ```

---

## Integration with Existing Toolchain

### Combined Workflow:
```powershell
# 1. Run Python fuzz first (baseline)
python3 .\fortios_fuzzing_toolkit.py 192.168.1.50 8443 100

# 2. Run PowerShell fuzz (validation)
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50 -IterationsPerEndpoint 100

# 3. Inject code into FortiOS for internal testing
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh

# 4. Compare results
$pythonReport = Get-Content fortios_fuzz_report_192.168.1.50*.json | ConvertFrom-Json | Select -First 1
$psReport = Get-Content fortios_fuzz_report_192.168.1.50*.json | ConvertFrom-Json | Select -Last 1

Compare-Object $pythonReport.vulnerabilities_by_type $psReport.vulnerabilities_by_type
```

---

## Support

For issues or feature requests, refer to the main HAMIVTZAR project documentation.
