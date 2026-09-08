# PowerShell FortiOS Fuzzing Toolkit

Complete Windows-native implementation of the FortiOS vulnerability fuzzing and testing framework. Provides comprehensive fuzzing capabilities with code injection and automated campaign orchestration.

## 📋 Overview

The PowerShell toolkit enables security researchers and penetration testers to:

- ✅ **Fuzz FortiOS endpoints** directly from Windows workstations
- ✅ **Discover vulnerabilities** using mutation-based fuzzing (7 strategies)
- ✅ **Inject code** into FortiOS via SSH or direct piping
- ✅ **Execute fuzzing campaigns** inside FortiOS kernel/CLI
- ✅ **Automate complete workflows** from discovery to reporting
- ✅ **Generate JSON reports** compatible with Python/Bash versions
- ✅ **Track persistent payloads** with auto-execution capability

## 🛠️ Tools Included

### 1. fortios_fuzzing_toolkit.ps1
Main fuzzing campaign runner for remote testing from Windows.

**Purpose:** Run mutation-based fuzzing against FortiOS SSL-VPN endpoints from a Windows workstation.

**Capabilities:**
- 5 endpoint-specific fuzzing strategies
- 7 mutation types (bit-flip, byte-flip, insert, delete, havoc, interesting values, size)
- Real-time vulnerability detection
- JSON reporting with vulnerability classification
- Progress tracking and statistics

**Usage:**
```powershell
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50 -IterationsPerEndpoint 100 -Verbose
```

**Output:**
- Console: Real-time progress and crash detection
- File: `fortios_fuzz_report_<ip>_<timestamp>.json`

---

### 2. fortios_code_injector.ps1
Uploads and executes fuzzing scripts directly within FortiOS environment.

**Purpose:** Deploy fuzzing code into FortiOS and execute it from within the system for deeper vulnerability discovery.

**Capabilities:**
- SSH connection management with password authentication
- 3 injection methods:
  - **SSH**: Upload via SCP, execute via SSH (most reliable)
  - **SCP+Execute**: Explicit two-step process
  - **Direct-Pipe**: Stream script directly into shell (no file transfer)
- Persistent payload installation for auto-execution
- FortiOS environment verification
- Remote result retrieval and logging

**Usage:**
```powershell
# Standard injection via SCP
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 `
    -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh `
    -ExecutionMethod ssh

# Persistent payload
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 `
    -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh `
    -Persistent

# Direct pipe (no file transfer)
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 `
    -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh `
    -ExecutionMethod direct-pipe
```

**Prerequisites:**
- SSH must be enabled on FortiOS
- Admin user credentials (typically `admin`)
- SSH client on Windows (built-in on Windows 10+)

---

### 3. fortios_automated_campaign.ps1
Complete multi-stage fuzzing campaign orchestrator.

**Purpose:** Run comprehensive vulnerability discovery workflow automatically.

**Workflow:**
1. **Stage 1** - Remote fuzz from Windows (SSL/TLS)
2. **Stage 2** - Inject and fuzz inside FortiOS (SSH)
3. **Stage 3** - Analyze vulnerabilities and correlate results
4. **Stage 4** - Generate consolidated JSON report

**Campaign Modes:**
- **quick** - 100 iterations per endpoint (total: ~500)
- **standard** - 100/500 mix (total: ~2500)
- **thorough** - 500 iterations per endpoint (total: ~2500+)

**Usage:**
```powershell
# Standard campaign
.\fortios_automated_campaign.ps1 -TargetHost 192.168.1.50 `
    -AdminPassword "fortinet" `
    -CampaignMode standard

# Thorough campaign with persistent payload
.\fortios_automated_campaign.ps1 -TargetHost 192.168.1.50 `
    -AdminPassword "fortinet" `
    -CampaignMode thorough `
    -Persistent

# Custom iterations
.\fortios_automated_campaign.ps1 -TargetHost 192.168.1.50 `
    -AdminPassword "fortinet" `
    -IterationsStage1 200 `
    -IterationsStage2 100
```

**Output:**
- Console: Real-time progress for all 4 stages
- Log File: `campaign_<timestamp>.log`
- Report: `campaign_<timestamp>_report.json` (consolidated results)
- Stage Reports: Individual JSON files for Stage 1 and 2

---

## 🎯 Vulnerability Detection

The toolkit detects and classifies 5 major vulnerability types:

| Vulnerability | CVSS Score | Detection Method | Impact |
|---------------|-----------|------------------|--------|
| **Path Traversal** | 9.8 | Response contains `/etc/passwd` or file content | Critical |
| **Buffer Overflow** | 7.8-8.6 | Service crash or timeout on oversized payload | High |
| **Authentication Bypass** | 4.31 | Success response without valid credentials | Medium |
| **Format String** | 4.46 | Memory addresses leaked in response (0x...) | Medium |
| **Denial of Service** | 4.02 | Service exhaustion after connection flood | Medium |

## 📊 Mutation Strategies

Each endpoint uses specialized mutations:

1. **Auth Endpoint** (SSL-VPN Auth)
   - Empty password replacement
   - Credential manipulation
   - Format string injection
   - Buffer overflow attempts
   - Invalid authentication headers

2. **Session Endpoint** (Session List)
   - Buffer overflow (512-byte payload)
   - Format string patterns
   - Path traversal injection
   - Invalid session types
   - Extreme padding

3. **Log Endpoint** (Log Messages)
   - Format string fuzzing (10 variants)
   - Repeating patterns
   - Memory leak detection
   - Log bypass attempts

4. **File Endpoint** (File Request)
   - Path traversal patterns (6 variants)
   - URL encoding bypass
   - Directory navigation
   - File access attempts

5. **Connection Endpoint** (Resource Exhaustion)
   - Buffer exhaustion (10KB payloads)
   - Maximum size requests (64KB)
   - Payload repetition
   - Memory exhaustion attempts

## 🔧 System Requirements

| Component | Requirement | Notes |
|-----------|------------|-------|
| OS | Windows 10+ | PowerShell 5.1+ built-in |
| Runtime | .NET Framework 4.5+ | Usually pre-installed |
| Network | Network access to target | Port 8443 (SSL-VPN), 22 (SSH) |
| SSH Client | OpenSSH or PuTTY | Windows 10+ has OpenSSH |
| Scripting | PowerShell | Not PowerShell Core (Core v7+ works too) |

## 📝 Usage Examples

### Example 1: Quick Vulnerability Discovery
```powershell
# Fuzz from Windows workstation
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50

# Check results
$report = Get-Content fortios_fuzz_report_*.json | ConvertFrom-Json
$report.vulnerabilities_by_type
```

### Example 2: Deep Exploitation Analysis
```powershell
# Stage 1: Fuzz remotely
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50 `
    -IterationsPerEndpoint 500 -Verbose

# Stage 2: Inject into FortiOS
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 `
    -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh `
    -ExecutionMethod ssh

# Analyze both results
Compare-Object $stage1Results $stage2Results
```

### Example 3: Persistent Testing
```powershell
# Install fuzzer as persistent payload
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 `
    -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh `
    -Persistent

# FortiOS now runs fuzzer automatically at startup
# Results saved to: /tmp/fuzz_logs/execution_*.log
```

### Example 4: Multi-Target Campaign
```powershell
# Fuzz multiple targets
$targets = @("192.168.1.50", "192.168.1.51", "192.168.1.52")

foreach ($target in $targets) {
    Write-Host "Fuzzing $target..."
    .\fortios_fuzzing_toolkit.ps1 -TargetHost $target -IterationsPerEndpoint 100
}

# Consolidate results
$allReports = Get-Content fortios_fuzz_report_*.json | 
    ForEach-Object { ConvertFrom-Json $_ }

$allReports | 
    ForEach-Object { $_.vulnerabilities_by_type } |
    Measure-Object -Sum | Format-Table -AutoSize
```

## 📁 Output Structure

### Fuzzing Report Format
```json
{
  "target": "192.168.1.50",
  "port": 8443,
  "timestamp": "2026-07-29T14:23:45Z",
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
    }
  ]
}
```

### Automated Campaign Report Format
```json
{
  "campaign_metadata": {
    "campaign_id": "20260729_142345",
    "target": "192.168.1.50",
    "mode": "standard",
    "duration_seconds": 486.23
  },
  "stage1_remote_fuzz": { ... },
  "stage2_local_fuzz": { ... },
  "summary": {
    "total_fuzz_iterations": 1000,
    "total_vulnerabilities": 45,
    "persistent_payload_installed": true
  }
}
```

## ⚙️ Configuration

All tools use command-line parameters for configuration. Key parameters:

```powershell
# Universal parameters
-TargetHost                 # Required: Target IP/hostname
-TargetPort                 # SSL port (default: 8443)
-AdminPassword              # Required for injection (default: none)
-Verbose                    # Enable detailed output
-Persistent                 # Install as persistent payload

# Fuzzer-specific
-IterationsPerEndpoint      # Mutations per endpoint (default: 100)

# Injector-specific
-AdminUser                  # SSH user (default: admin)
-SSHPort                    # SSH port (default: 22)
-ScriptPath                 # Path to script to inject
-ScriptType                 # Script type: python, bash, cli
-ExecutionMethod            # ssh, scp-then-execute, direct-pipe

# Campaign-specific
-CampaignMode              # quick, standard, thorough
-ReportPath                # Directory for reports (default: ./fuzz_campaign_results)
```

## 🔗 Integration

### With Python Version
```powershell
# Run Python fuzzer first
python3 .\fortios_fuzzing_toolkit.py 192.168.1.50

# Validate with PowerShell
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50

# Compare results
$pyReport = Get-Content fortios_fuzz_report_*.json -TotalCount 1 | ConvertFrom-Json
$psReport = Get-Content fortios_fuzz_report_*.json -TotalCount -1 | ConvertFrom-Json
Compare-Object $pyReport $psReport -Property total_crashes
```

### With Bash Version
```powershell
# Inject bash fuzzer into FortiOS
.\fortios_code_injector.ps1 -TargetHost 192.168.1.50 `
    -AdminPassword "fortinet" `
    -ScriptPath ./fortios_cli_fuzzer.sh `
    -ScriptType bash
```

### With CI/CD Pipelines
```powershell
# GitHub Actions example
.\fortios_fuzzing_toolkit.ps1 `
    -TargetHost $env:FORTIOS_HOST `
    -TargetPort 8443 `
    -IterationsPerEndpoint 100

# Save results
Get-Content fortios_fuzz_report_*.json | 
    Out-File fuzz_results_$([datetime]::Now.ToString("yyyyMMdd_HHmmss")).json
```

## 📖 Documentation

- **POWERSHELL_USAGE.md** - Comprehensive usage guide with all parameters
- **POWERSHELL_QUICK_START.txt** - Quick reference for common commands
- **tools/fortios_cli_fuzzer.sh** - Bash version for FortiOS CLI execution
- **tools/fortios_fuzzing_toolkit.py** - Python version with same functionality

## ⚠️ Security & Legal

**This toolkit is designed for:**
- ✅ Authorized penetration testing
- ✅ Security research in isolated lab environments
- ✅ Vulnerability discovery for responsible disclosure
- ✅ Authorized testing with explicit permission

**Not for:**
- ❌ Unauthorized access to systems
- ❌ Production environment testing without approval
- ❌ Malicious purposes
- ❌ Denial of service attacks against non-authorized targets

**Responsible Use:**
- Only test systems you own or have explicit written permission to test
- Use in isolated lab environments
- Follow coordinated disclosure practices
- Report vulnerabilities responsibly
- Never exploit vulnerabilities in unauthorized contexts

## 🤝 Contributing

All scripts follow consistent patterns for easy maintenance:
- Common mutation strategies across all implementations
- Compatible JSON reporting format
- Consistent parameter naming
- Detailed inline documentation

For contributions, ensure compatibility with Python and Bash versions.

## 📄 License

Part of HAMIVTZAR CVE research framework.
For research and authorized testing only.

---

**Quick Start:**
```powershell
# 1. Quick fuzz
.\fortios_fuzzing_toolkit.ps1 -TargetHost 192.168.1.50

# 2. Comprehensive campaign
.\fortios_automated_campaign.ps1 -TargetHost 192.168.1.50 `
    -AdminPassword "fortinet" -CampaignMode standard

# 3. View results
$report = Get-Content fortios_fuzz_report_*.json | ConvertFrom-Json
$report.vulnerabilities_by_type
```

See **POWERSHELL_QUICK_START.txt** for more examples.
