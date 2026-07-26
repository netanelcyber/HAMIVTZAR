# Factory Lab - Windows Deployment Guide

## Overview

This guide shows how to integrate **Windows Server 2022** as the primary Active Directory domain controller and **Windows 11** as employee workstations into the factory lab environment.

**Architecture**:
- **Windows Server 2022 VMs**: AD DC, DHCP, DNS, File Server (can replace Samba)
- **Windows 11 Workstations**: 50 employee machines in different departments
- **Linux Containers**: OT systems (SCADA, PLC, MES) remain containerized

---

## Option A: Windows Server 2022 as AD/File Server (Hybrid Setup)

### 1. Requirements

- Hyper-V, KVM, or VirtualBox hypervisor
- Windows Server 2022 ISO (2-3 VMs recommended)
- Network connectivity to Linux container host
- 16+ GB RAM for Windows VMs, 16GB for Linux host

### 2. Windows Server 2022 VM Setup

#### 2.1 VM Configuration

```
VM Name: FACTORY-DC01
Specs:
  - CPU: 4 cores
  - RAM: 4 GB
  - Storage: 100 GB (C: 50GB, D: 50GB for data)
  - Network: Bridged or Host-only network shared with Linux
  - OS: Windows Server 2022 Standard/Datacenter
```

#### 2.2 Initial Windows Setup

```powershell
# Run as Administrator

# 1. Set computer name and IP
$newComputerName = "FACTORY-DC01"
$ipAddress = "10.0.1.100"
$gateway = "10.0.1.1"
$dns = @("10.0.1.100", "8.8.8.8")

Rename-Computer -NewName $newComputerName -Force -Restart

# After restart - set static IP
$adapter = Get-NetAdapter | Where-Object {$_.Status -eq "Up"}
New-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex `
  -IPAddress $ipAddress -PrefixLength 24 -DefaultGateway $gateway

Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex `
  -ServerAddresses $dns
```

#### 2.3 Install Active Directory Domain Services

```powershell
# Install AD DS role
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools

# Import deployment module
Import-Module ADDSDeployment

# Promote to domain controller
Install-ADDSForest `
  -DomainName "factory.local" `
  -DomainNetbiosName "FACTORY" `
  -ForestMode "Windows2016" `
  -DomainMode "Windows2016" `
  -InstallDns `
  -CreateDnsDelegation:$false `
  -NoRebootOnCompletion:$false `
  -Force:$true `
  -SafeModeAdministratorPassword (ConvertTo-SecureString "FactoryP@ss123!" -AsPlainText -Force)
```

#### 2.4 Install DHCP Server

```powershell
# Install DHCP
Install-WindowsFeature -Name DHCP -IncludeManagementTools

# Configure DHCP scope
Add-DhcpServerv4Scope -Name "Factory Lab" `
  -StartRange 10.0.1.150 -EndRange 10.0.1.250 `
  -SubnetMask 255.255.255.0

# Set DHCP options
Set-DhcpServerv4OptionValue -ScopeId 10.0.1.0 `
  -Router 10.0.1.1 -DnsServer 10.0.1.100 -DnsDomain factory.local

# Authorize DHCP
Add-DhcpServerInDC -DnsName factory-dc01.factory.local -IPAddress 10.0.1.100
```

#### 2.5 Install File Server

```powershell
# Install file server role
Install-WindowsFeature -Name File-Services -IncludeManagementTools

# Create shared folders
$shares = @(
    @{Name="Production"; Path="D:\Shares\Production"},
    @{Name="Engineering"; Path="D:\Shares\Engineering"},
    @{Name="Quality"; Path="D:\Shares\Quality"},
    @{Name="Maintenance"; Path="D:\Shares\Maintenance"},
    @{Name="Logistics"; Path="D:\Shares\Logistics"},
    @{Name="Backups"; Path="D:\Shares\Backups"}
)

foreach ($share in $shares) {
    # Create folder
    New-Item -ItemType Directory -Path $share.Path -Force | Out-Null
    
    # Create SMB share
    New-SmbShare -Name $share.Name -Path $share.Path -FullAccess "FACTORY\Domain Admins"
}
```

### 3. Create 50 Active Directory Users (PowerShell)

#### 3.1 User Creation Script

```powershell
# Create departments
$departments = @(
    @{Name="Production"; OU="OU=Production,DC=factory,DC=local"},
    @{Name="Maintenance"; OU="OU=Maintenance,DC=factory,DC=local"},
    @{Name="Quality Assurance"; OU="OU=QualityAssurance,DC=factory,DC=local"},
    @{Name="Logistics"; OU="OU=Logistics,DC=factory,DC=local"},
    @{Name="Engineering"; OU="OU=Engineering,DC=factory,DC=local"},
    @{Name="Management"; OU="OU=Management,DC=factory,DC=local"}
)

# Create OUs
foreach ($dept in $departments) {
    New-ADOrganizationalUnit -Name $dept.Name -Path "DC=factory,DC=local" -ProtectedFromAccidentalDeletion $false
}

# Create groups per department
foreach ($dept in $departments) {
    New-ADGroup -Name $dept.Name -GroupScope Global -Path $dept.OU
}

# User data (50 users)
$users = @(
    @{First="John"; Last="Smith"; Dept="Production"; Role="Line Operator"},
    @{First="Sarah"; Last="Johnson"; Dept="Production"; Role="Line Lead"},
    @{First="Michael"; Last="Brown"; Dept="Maintenance"; Role="Technician"},
    # ... Add 47 more users (use CSV import for production)
)

# Create users
foreach ($user in $users) {
    $username = "$($user.First.ToLower()).$($user.Last.ToLower())"
    $password = "FactoryP@ss123!" | ConvertTo-SecureString -AsPlainText -Force
    $dept = $user.Dept
    $ou = ($departments | Where-Object {$_.Name -eq $dept}).OU
    
    New-ADUser -Name $user.First `
      -GivenName $user.First `
      -Surname $user.Last `
      -SamAccountName $username `
      -UserPrincipalName "$username@factory.local" `
      -Path $ou `
      -AccountPassword $password `
      -Enabled $true `
      -Title $user.Role `
      -Department $dept
    
    Add-ADGroupMember -Identity $dept -Members $username
}
```

#### 3.2 Import Users from CSV

```powershell
# Create CSV file: employees.csv
# Format: FirstName,LastName,Department,Role

$employees = Import-Csv -Path "C:\temp\employees.csv"

foreach ($emp in $employees) {
    $username = "$($emp.FirstName.ToLower()).$($emp.LastName.ToLower())"
    $password = "FactoryP@ss123!" | ConvertTo-SecureString -AsPlainText -Force
    
    New-ADUser -Name "$($emp.FirstName) $($emp.LastName)" `
      -GivenName $emp.FirstName `
      -Surname $emp.LastName `
      -SamAccountName $username `
      -UserPrincipalName "$username@factory.local" `
      -Path "OU=$($emp.Department),DC=factory,DC=local" `
      -AccountPassword $password `
      -Enabled $true `
      -Title $emp.Role `
      -Department $emp.Department
    
    Add-ADGroupMember -Identity $emp.Department -Members $username
}
```

### 4. Configure File Server ACLs

```powershell
# Set NTFS permissions for Production share
$acl = Get-Acl "D:\Shares\Production"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "FACTORY\Production",
    "Modify",
    "ContainerInherit,ObjectInherit",
    "None",
    "Allow"
)
$acl.AddAccessRule($rule)
Set-Acl -Path "D:\Shares\Production" -AclObject $acl

# Repeat for other departments...
```

---

## Option B: Windows 11 Workstations

### 1. Windows 11 VM Setup

#### 1.1 VM Configuration (per workstation)

```
VM Name: WS-[USERNAME] (e.g., WS-JOHN-SMITH)
Specs:
  - CPU: 2 cores
  - RAM: 4 GB
  - Storage: 60 GB
  - Network: Bridged/Host-only (same as DC)
  - OS: Windows 11 Pro/Enterprise
```

#### 1.2 Initial Setup Script

```powershell
# Run as Administrator on each Windows 11 VM

# Set computer name
$username = "john.smith"  # or whatever
$computerName = "WS-$($username.ToUpper())"
Rename-Computer -NewName $computerName -Force

# Get network info from DHCP
# (Or set static IP if needed)

# Wait for network
Start-Sleep -Seconds 10

# Join domain
$domain = "factory.local"
$ou = "CN=Computers,DC=factory,DC=local"
$cred = New-Object System.Management.Automation.PSCredential(
    "factory\Administrator",
    (ConvertTo-SecureString "FactoryP@ss123!" -AsPlainText -Force)
)

Add-Computer -DomainName $domain -Credential $cred -OUPath $ou -Force -Restart
```

#### 1.3 Deploy Windows 11 Workstations Automatically

```powershell
# On Windows Server 2022 DC - deploy to 50 workstations

# Option 1: Windows Deployment Services (WDS)
# Install WDS role, configure boot image, reference image

# Option 2: DBAN (Darik's Boot and Nuke) + custom image
# Create master image with factory applications pre-installed

# Option 3: PowerShell Direct (for Hyper-V VMs)
$vmList = Get-VM | Where-Object {$_.Name -like "WS-*"}

foreach ($vm in $vmList) {
    $cred = New-Object PSCredential("Administrator", (ConvertTo-SecureString "Temp123!" -AsPlainText -Force))
    
    Invoke-Command -VMName $vm.Name -Credential $cred -ScriptBlock {
        Add-Computer -DomainName "factory.local" `
          -Credential (New-Object PSCredential("factory\Administrator", (ConvertTo-SecureString "FactoryP@ss123!" -AsPlainText -Force))) `
          -Force -Restart
    }
}
```

### 2. Install Applications on Windows 11

```powershell
# Run on each Windows 11 workstation

# Map network shares
New-PSDrive -Name "P" -PSProvider FileSystem -Root "\\factory-dc01\Production"
New-PSDrive -Name "E" -PSProvider FileSystem -Root "\\factory-dc01\Engineering"

# Install factory-specific software
# - HMI clients (e.g., Wonderware, Ignition Client)
# - Remote desktop tools
# - VPN clients
# - Manufacturing software

# Example: Install Wonderware client
msiexec /i "Wonderware-Client-2023.msi" /quiet /norestart

# Install Chrome
choco install googlechrome -y

# Install VS Code (for engineers)
choco install vscode -y
```

---

## Option C: Hybrid Linux + Windows Integrated Setup

### 1. Network Bridge Configuration

```bash
# On Linux host - Create bridge for VMs
# Edit /etc/network/interfaces

auto br0
iface br0 inet static
    address 10.0.1.1
    netmask 255.255.255.0
    bridge_ports eth0
    bridge_stp off
    bridge_fd 0
```

### 2. Connect Docker to Windows Network

```bash
# Configure docker-compose networks
# Use "host" network mode if Windows VMs are on same physical network
# Or use a bridge network that Windows VMs can also access
```

### 3. DNS Configuration

```bash
# Linux containers resolve to Windows DC
# Edit /etc/docker/daemon.json

{
  "dns": ["10.0.1.100", "8.8.8.8"],
  "dns-search": ["factory.local"]
}
```

---

## Integration with Linux Container Lab

### 1. Linux Services Point to Windows AD

```yaml
# docker-compose.yml updates for Windows AD
services:
  samba-ad:
    # Can be disabled if using Windows Server 2022
    profiles: ["linux-only"]
  
  # Other services reference Windows DC
  mes-app:
    environment:
      AD_SERVER: "10.0.1.100"
      AD_DOMAIN: "factory.local"
  
  nginx-gateway:
    environment:
      AD_AUTHENTICATION: "ldap://10.0.1.100:389"
```

### 2. LDAP/LDAPS Configuration for Services

```python
# In MES app or services
import ldap

# Connect to Windows Server AD
ldap_server = "ldap://10.0.1.100:389"
# or TLS: ldaps://10.0.1.100:636

conn = ldap.initialize(ldap_server)
conn.bind_s("factory\\username", "password")

# Search for users
result = conn.search_s(
    "CN=Users,DC=factory,DC=local",
    ldap.SCOPE_SUBTREE,
    "(sAMAccountName=john.smith)"
)
```

---

## Deployment Workflow

### Phase 1: Windows Infrastructure (Day 1)
```powershell
1. Create Windows Server 2022 VM
2. Install AD DS, DHCP, DNS
3. Create domain (factory.local)
4. Create 6 OUs (departments)
5. Create security groups
6. Create 50 AD users
7. Install file server
8. Configure SMB shares
9. Set NTFS permissions
```

### Phase 2: Windows Workstations (Day 1-2)
```powershell
1. Create 50 Windows 11 VMs
2. Configure DHCP (or static IPs)
3. Join all to factory.local domain
4. Install factory applications
5. Map department shares
6. Deploy group policies
7. Verify domain membership
```

### Phase 3: Linux Integration (Day 2)
```bash
1. Update docker-compose to use Windows AD (10.0.1.100)
2. Update LDAP/DNS references
3. Test authentication from containers
4. Configure services to use Windows file server
5. Verify cross-platform communication
6. Test workstation access to Linux services
```

### Phase 4: Full Integration (Day 3)
```bash
1. Windows 11 workstations access:
   - MES via browser (http://10.0.1.31:8000)
   - SCADA dashboards
   - OPC-UA from industrial HMI
2. Linux containers authenticate via Windows AD
3. File sharing works cross-platform
4. Monitoring/logging centralized
5. Run integration tests
```

---

## Group Policy Templates for Windows 11

### 1. Security Policies

```xml
<!-- Create in Group Policy Editor (gpedit.msc) -->

Computer Configuration:
  - Windows Settings > Security Settings > Password Policy
    - Minimum password length: 12
    - Password complexity: Enabled
  - Windows Settings > Security Settings > Account Lockout Policy
    - Lockout duration: 30 minutes
    - Lockout threshold: 5 attempts

User Configuration:
  - Windows Settings > Internet Explorer Maintenance
  - Administrative Templates > System > User Profiles
```

### 2. Department-Based Policies

```powershell
# Production department policy
New-GPO -Name "Production-Department-Policy"
New-GPLink -Name "Production-Department-Policy" -Target "OU=Production,DC=factory,DC=local"

# Map network drives
Set-GPPrefRegistryValue -Name "Production-Department-Policy" `
  -Key "HKCU\Network\P" `
  -ValueName "RemotePath" `
  -Value "\\factory-dc01\Production" `
  -Action Update
```

---

## Backup & Disaster Recovery

### Windows Server AD Backup

```powershell
# Weekly AD backup
$backupPath = "D:\Backups\AD-$(Get-Date -Format 'yyyy-MM-dd')"
New-Item -ItemType Directory -Path $backupPath -Force

# Full system state backup
wbadmin start systemstatebackup -backupTarget:$backupPath -quiet

# Export users to CSV
Get-ADUser -Filter * -Properties * | Export-Csv "C:\temp\ad_users_backup.csv"
```

### Restore Procedures

```powershell
# Restore single user
$user = Import-Csv "C:\temp\ad_users_backup.csv" | Select-Object -First 1
New-ADUser -Identity $user.SamAccountName -Instance ([ADUser]$user)

# Full system state restore (requires Safe Mode)
wbadmin start systemstaterecovery -backupTarget:\\network\share -version:MM/DD/YYYY-HH:MM
```

---

## Monitoring & Logging

### Windows Event Logs to Centralized Location

```powershell
# Configure event forwarding
# On DC, enable Windows Remote Management
winrm quickconfig

# On workstations, create subscription
wecutil cs subscription.xml

# subscription.xml content:
# <Subscription>
#   <SubscriptionId>Factory-Workstations</SubscriptionId>
#   <SubscriptionType>SourceInitiated</SubscriptionType>
#   <ContentFormat>Events</ContentFormat>
#   <Locale Language="en-US"/>
#   <Query>
#     <Select Path="Security">*[System[(Level=1 or Level=2 or Level=3)]]</Select>
#     <Select Path="System">*[System[(Level=1 or Level=2)]]</Select>
#   </Query>
# </Subscription>
```

### Syslog Integration

```powershell
# Forward Windows logs to Linux syslog
# Install Snare Agent or similar forwarding service
# Configure to send to 10.0.1.70 (ELK stack or syslog server)
```

---

## Testing & Validation

```powershell
# Verify domain connectivity
net ads info

# Check user creation
Get-ADUser -Filter * | Measure-Object

# Test file sharing
Test-Path \\factory-dc01\Production

# Verify DHCP
Get-DhcpServerv4Scope

# Check DNS resolution
Resolve-DnsName factory.local -Server 10.0.1.100

# Test user authentication
$cred = New-Object PSCredential("factory\john.smith", (ConvertTo-SecureString "pass" -AsPlainText -Force))
Invoke-Command -ComputerName ws-john-smith -Credential $cred -ScriptBlock {whoami}
```

---

## Troubleshooting

### Cannot join domain from Windows 11
```powershell
# Check connectivity to DC
Test-NetConnection 10.0.1.100 -Port 389
nslookup factory-dc01.factory.local

# Check time sync (AD requires <5 min difference)
w32tm /query /status

# Manual domain join with verbose output
Add-Computer -DomainName factory.local -Verbose -Force -Restart
```

### Users cannot access shares
```powershell
# Check permissions
Get-Acl \\factory-dc01\Production

# Verify user group membership
Get-ADUser john.smith | Get-ADMemberOf
```

---

## Quick Start

1. **Windows Server 2022 Setup**: 30 minutes
2. **AD + 50 Users**: 15 minutes (scripted)
3. **File Servers**: 15 minutes
4. **50 Windows 11 VMs**: 2-4 hours (can be parallelized)
5. **Integration**: 30 minutes

**Total estimated time: 3-5 hours for full setup**
