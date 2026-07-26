# Windows Factory Lab - Complete Deployment Guide

**Step-by-step deployment of enterprise Windows Server 2022 factory infrastructure**

---

## Pre-Deployment Checklist

### Hardware Requirements
- [ ] 3x Windows Server 2022 VMs (Hyper-V / VMware / KVM)
  - CPU: 4 cores each
  - RAM: 8 GB each
  - Disk: 100 GB each (50GB OS + 50GB data)
  - Network: Bridged adapter, 10.0.1.0/24 subnet

- [ ] 1x SQL Server 2022 instance
  - RAM: 8-16 GB dedicated
  - Disk: 100+ GB (databases will grow)

- [ ] 50x Windows 11 Pro/Enterprise VMs
  - CPU: 2 cores each
  - RAM: 4 GB each
  - Disk: 60 GB each

### Software Requirements
- [ ] Windows Server 2022 Datacenter ISO (3 copies)
- [ ] SQL Server 2022 Enterprise media
- [ ] Windows 11 Pro/Enterprise media
- [ ] .NET Framework 6+ Runtime
- [ ] PowerShell 7+

### Network Requirements
- [ ] Subnet: 10.0.1.0/24
- [ ] Gateway: 10.0.1.1
- [ ] DNS Servers: 10.0.1.100 (DC01), 8.8.8.8 (fallback)
- [ ] DHCP: Enabled (10.0.1.150 - 10.0.1.250)

---

## PHASE 1: Deploy First Domain Controller (FACTORY-DC01)

### Step 1.1: Create VM and Install OS

**Hyper-V Example:**
```powershell
New-VM -Name "FACTORY-DC01" `
    -MemoryStartupBytes 8GB `
    -NewVHDPath "D:\VMs\FACTORY-DC01.vhdx" `
    -NewVHDSizeBytes 100GB `
    -SwitchName "FactorySwitch"

# Attach Windows Server 2022 ISO and boot to install
```

### Step 1.2: Post-OS Installation Configuration

**Run these commands as Administrator:**

```powershell
# Set computer name
$computerName = "FACTORY-DC01"
Rename-Computer -NewName $computerName -Force

# Set static IP
$adapter = Get-NetAdapter | Select-Object -First 1
Remove-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex -Confirm:$false -ErrorAction SilentlyContinue
Remove-NetRoute -InterfaceIndex $adapter.InterfaceIndex -Confirm:$false -ErrorAction SilentlyContinue

New-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex `
    -IPAddress "10.0.1.100" `
    -PrefixLength 24 `
    -DefaultGateway "10.0.1.1"

Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex `
    -ServerAddresses ("10.0.1.100", "8.8.8.8")

# Restart (required after rename and IP change)
Restart-Computer -Force
```

**After restart, run:**

```powershell
# Install AD DS, DNS, DHCP roles
Install-WindowsFeature -Name AD-Domain-Services, DNS, DHCP, RSAT-ADDS-Tools `
    -IncludeManagementTools -IncludeAllSubFeature

# Restart again
Restart-Computer -Force
```

### Step 1.3: Promote to Domain Controller

**After restart:**

```powershell
# Set safe mode password
$safeModePassword = ConvertTo-SecureString "SafeModeP@ss2024!" -AsPlainText -Force

# Install AD Forest
Install-ADDSForest `
    -CreateDnsDelegation:$false `
    -DomainMode "Windows2022" `
    -DomainName "factory.local" `
    -DomainNetbiosName "FACTORY" `
    -ForestMode "Windows2022" `
    -InstallDns:$true `
    -SafeModeAdministratorPassword $safeModePassword `
    -NoRebootOnCompletion:$false `
    -Force:$true
```

**Server will restart automatically. After restart:**

### Step 1.4: Configure DHCP

```powershell
# Add DHCP server to AD
Add-DhcpServerInDC -DnsName "factory-dc01.factory.local" `
    -IPAddress "10.0.1.100"

# Create DHCP scope for workstations
Add-DhcpServerv4Scope -Name "Factory Workstations" `
    -StartRange "10.0.1.150" `
    -EndRange "10.0.1.250" `
    -SubnetMask "255.255.255.0"

# Configure DHCP options
Set-DhcpServerv4OptionValue -ScopeId "10.0.1.0" `
    -Router "10.0.1.1" `
    -DnsServer "10.0.1.100" `
    -DnsDomain "factory.local"

# Set lease duration
Set-DhcpServerv4Scope -ScopeId "10.0.1.0" `
    -LeaseDuration ([TimeSpan]::FromDays(7))

# Start DHCP service
Start-Service DHCPServer
```

### Step 1.5: Create Organizational Units

```powershell
# Create department OUs
$departments = @(
    "Production",
    "Engineering", 
    "Quality Assurance",
    "Logistics",
    "Maintenance",
    "Management"
)

foreach ($dept in $departments) {
    New-ADOrganizationalUnit -Name $dept `
        -Path "DC=factory,DC=local" `
        -ProtectedFromAccidentalDeletion $false
    
    Write-Host "Created OU: $dept"
}

# Create service accounts OU
New-ADOrganizationalUnit -Name "Service Accounts" `
    -Path "DC=factory,DC=local" `
    -ProtectedFromAccidentalDeletion $false

# Create computers OU
New-ADOrganizationalUnit -Name "Computers" `
    -Path "DC=factory,DC=local" `
    -ProtectedFromAccidentalDeletion $false
```

### Step 1.6: Create Security Groups

```powershell
# Create department groups
$departments = @(
    "Production",
    "Engineering",
    "Quality Assurance",
    "Logistics",
    "Maintenance",
    "Management"
)

foreach ($dept in $departments) {
    New-ADGroup -Name $dept `
        -GroupScope Global `
        -GroupCategory Security `
        -Path "OU=$dept,DC=factory,DC=local" `
        -Description "Members of $dept department"
    
    Write-Host "Created group: $dept"
}

# Create functional groups
$functionalGroups = @(
    @{Name="OT-Administrators"; Desc="OT System Admins"},
    @{Name="PLC-Programmers"; Desc="PLC Engineering"; OU="Service Accounts"},
    @{Name="File-Server-Admins"; Desc="File Server Admin"; OU="Service Accounts"},
    @{Name="Historian-Admin"; Desc="Historian DB Admin"; OU="Service Accounts"},
    @{Name="SCADA-Operators"; Desc="SCADA Operation"; OU="Service Accounts"},
    @{Name="Safety-Officers"; Desc="Safety Team"; OU="Service Accounts"}
)

foreach ($group in $functionalGroups) {
    New-ADGroup -Name $group.Name `
        -GroupScope Global `
        -GroupCategory Security `
        -Path "OU=$($group.OU),DC=factory,DC=local" `
        -Description $group.Desc
    
    Write-Host "Created functional group: $($group.Name)"
}
```

---

## PHASE 2: Create 50 Employee Accounts

### Step 2.1: Create Employee Data

Create file `C:\Scripts\employees.csv`:

```csv
FirstName,LastName,Department,Role,Title
John,Smith,Production,Operator,Production Line Operator
Sarah,Johnson,Production,Lead,Production Line Lead
Michael,Brown,Production,Supervisor,Shift Supervisor
Jennifer,Davis,Production,Operator,Production Line Operator
David,Wilson,Production,Handler,Material Handler
Emily,Martinez,Production,Operator,Production Line Operator
Robert,Anderson,Production,Lead,Production Line Lead
Jessica,Taylor,Production,Operator,Production Line Operator
James,Moore,Production,Supervisor,Shift Supervisor
Linda,Jackson,Production,Handler,Material Handler
William,White,Production,Operator,Production Line Operator
Patricia,Harris,Production,Lead,Production Line Lead
Richard,Martin,Production,Tech,Maintenance Technician
Barbara,Thompson,Production,Handler,Material Handler
Joseph,Garcia,Maintenance,Supervisor,Maintenance Supervisor
Mary,Rodriguez,Maintenance,Tech,Electrical Technician
Charles,Lee,Maintenance,Tech,Mechanical Technician
Carol,Perez,Maintenance,Tech,Preventive Maintenance Tech
Christopher,Edwards,Engineering,Lead,Lead Engineer
Nancy,Collins,Engineering,Lead,Lead Engineer
Daniel,Reyes,Engineering,Engineer,Process Engineer
Lisa,Stewart,Engineering,Engineer,Process Engineer
Matthew,Morris,Engineering,Engineer,Controls Engineer
Betty,Rogers,Engineering,Engineer,Controls Engineer
Mark,Morgan,Engineering,Tech,Automation Technician
Margaret,Peterson,Engineering,Tech,Automation Technician
Donald,Cooper,Engineering,Admin,Systems Administrator
Sandra,Reed,Engineering,Engineer,Manufacturing Engineer
Steven,Cook,Engineering,Engineer,Process Engineer
Ashley,Morgan,Engineering,Tech,Automation Technician
Paul,Bell,Quality Assurance,Manager,QA Manager
Donna,Gomez,Quality Assurance,Specialist,QA Specialist
Andrew,Murray,Quality Assurance,Specialist,QA Specialist
Carol,Freeman,Quality Assurance,Specialist,QA Specialist
Joshua,Wells,Quality Assurance,Officer,Compliance Officer
Amanda,Webb,Quality Assurance,Tech,Lab Technician
Kenneth,Simpson,Quality Assurance,Tech,Lab Technician
Melissa,Stevens,Quality Assurance,Specialist,QA Specialist
Kevin,Tucker,Logistics,Manager,Logistics Manager
Deborah,Porter,Logistics,Worker,Warehouse Worker
Brian,Hunter,Logistics,Operator,Forklift Operator
Stephanie,Hicks,Logistics,Clerk,Shipping Clerk
George,Crawford,Management,Director,Plant Director
Cynthia,Henry,Management,Manager,Operations Manager
Edward,Boyd,Management,Manager,Operations Manager
Kathleen,Mason,Management,Manager,Finance Manager
Ronald,Moreno,Management,Manager,HR Manager
Christine,Kennedy,Management,Director,IT Director
Anthony,Warren,Management,Officer,Safety Officer
Alice,Dixon,Management,Manager,Quality Manager
Frank,Ramos,Quality Assurance,Specialist,QA Specialist
Rebecca,Kemp,Engineering,Engineer,Manufacturing Engineer
```

### Step 2.2: Create Users from CSV

```powershell
# Import CSV
$employees = Import-Csv "C:\Scripts\employees.csv"

# Function to create user
function Create-FactoryEmployee {
    param(
        [string]$FirstName,
        [string]$LastName,
        [string]$Department,
        [string]$Role,
        [string]$Title
    )

    $username = "$($FirstName.ToLower()).$($LastName.ToLower())"
    $displayName = "$FirstName $LastName"
    $password = ConvertTo-SecureString "FactoryP@ss2024!" -AsPlainText -Force
    $ou = "OU=$Department,DC=factory,DC=local"
    
    try {
        # Create user
        New-ADUser -Name $displayName `
            -GivenName $FirstName `
            -Surname $LastName `
            -SamAccountName $username `
            -UserPrincipalName "$username@factory.local" `
            -EmailAddress "$username@factory.local" `
            -Path $ou `
            -AccountPassword $password `
            -Title $Title `
            -Department $Department `
            -Office "Building A" `
            -OfficePhone "+1-555-0001" `
            -Enabled $true `
            -ChangePasswordAtLogon $true
        
        # Add to department group
        $group = Get-ADGroup -Identity $Department
        Add-ADGroupMember -Identity $group -Members $username
        
        Write-Host "✓ Created: $username ($Title)" -ForegroundColor Green
        
        return $true
    }
    catch {
        Write-Host "✗ Failed: $username - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Create all 50 employees
$successCount = 0
$failureCount = 0

foreach ($emp in $employees) {
    $result = Create-FactoryEmployee `
        -FirstName $emp.FirstName `
        -LastName $emp.LastName `
        -Department $emp.Department `
        -Role $emp.Role `
        -Title $emp.Title
    
    if ($result) { $successCount++ }
    else { $failureCount++ }
}

Write-Host "`nSummary: Created $successCount users, $failureCount failures"
```

---

## PHASE 3: Deploy File Server (FACTORY-FS)

### Step 3.1: Install File Server Role

On FACTORY-FS (Windows Server 2022):

```powershell
# Install File Server role
Install-WindowsFeature -Name File-Services, FS-FileServer, FS-DFS-Namespace, FS-DFS-Replication `
    -IncludeManagementTools

# Set static IP
$adapter = Get-NetAdapter | Select-Object -First 1
New-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex `
    -IPAddress "10.0.1.101" `
    -PrefixLength 24 `
    -DefaultGateway "10.0.1.1"

# Join to domain
$credential = Get-Credential  # Use FACTORY\Administrator
Add-Computer -DomainName "factory.local" `
    -Credential $credential `
    -OUPath "OU=Computers,DC=factory,DC=local" `
    -Force -Restart
```

### Step 3.2: Create Shares

```powershell
# Create share directories
$shares = @(
    "Production",
    "Engineering",
    "QualityAssurance",
    "Logistics",
    "Maintenance",
    "Corporate",
    "Backups",
    "Public"
)

foreach ($share in $shares) {
    $path = "D:\Shares\$share"
    New-Item -ItemType Directory -Path $path -Force | Out-Null
}

# Create SMB shares with permissions
$shareMappings = @(
    @{Name="Production"; Path="D:\Shares\Production"; Groups="Production"}
    @{Name="Engineering"; Path="D:\Shares\Engineering"; Groups="Engineering"}
    @{Name="Quality"; Path="D:\Shares\QualityAssurance"; Groups="Quality Assurance"}
    @{Name="Logistics"; Path="D:\Shares\Logistics"; Groups="Logistics"}
    @{Name="Maintenance"; Path="D:\Shares\Maintenance"; Groups="Maintenance"}
    @{Name="Corporate"; Path="D:\Shares\Corporate"; Groups="Management"}
    @{Name="Backups"; Path="D:\Shares\Backups"; Groups="File-Server-Admins"}
    @{Name="Public"; Path="D:\Shares\Public"; Groups="FACTORY\Domain Users"}
)

foreach ($share in $shareMappings) {
    # Create SMB share
    New-SmbShare -Name $share.Name `
        -Path $share.Path `
        -FullAccess "$($share.Groups)", "FACTORY\Administrators" `
        -ChangeAccess "$($share.Groups)"
    
    # Set NTFS permissions
    $acl = Get-Acl $share.Path
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "FACTORY\$($share.Groups)",
        "Modify",
        "ContainerInherit,ObjectInherit",
        "None",
        "Allow"
    )
    $acl.SetAccessRule($rule)
    Set-Acl -Path $share.Path -AclObject $acl
    
    Write-Host "Created share: $($share.Name)"
}
```

---

## PHASE 4: Deploy SQL Server and Manufacturing Database

### Step 4.1: SQL Server Installation

Install SQL Server 2022 on FACTORY-SQL:
- Choose "Enterprise" edition
- Set instance name to "MSSQLSERVER"
- Use "NT AUTHORITY\SYSTEM" for SQL Server service
- Enable "SQL Server Agent"
- Join to factory.local domain

### Step 4.2: Create Manufacturing Database

```sql
-- Run on SQL Server
USE [master]
GO

-- Create database
CREATE DATABASE [Manufacturing]
ON PRIMARY 
( 
    NAME = N'Manufacturing', 
    FILENAME = N'D:\MSSQL\Data\Manufacturing.mdf',
    SIZE = 500MB,
    FILEGROWTH = 100MB
)
LOG ON 
( 
    NAME = N'Manufacturing_log', 
    FILENAME = N'D:\MSSQL\Log\Manufacturing_log.ldf',
    SIZE = 100MB,
    FILEGROWTH = 50MB
)
GO

-- Set recovery model to FULL for compliance
ALTER DATABASE [Manufacturing] SET RECOVERY FULL
GO

-- Create tables (see WINDOWS_CORE_ARCHITECTURE.md for full schema)
USE [Manufacturing]
GO

-- Production Lines
CREATE TABLE [dbo].[ProductionLines] (
    [LineID] INT PRIMARY KEY IDENTITY(1,1),
    [LineName] VARCHAR(50) NOT NULL UNIQUE,
    [Location] VARCHAR(100),
    [LineType] VARCHAR(50),
    [CapacityPerHour] INT,
    [Status] VARCHAR(20) DEFAULT 'Active',
    [CreatedDate] DATETIME DEFAULT GETDATE()
)

-- Equipment
CREATE TABLE [dbo].[Equipment] (
    [EquipmentID] INT PRIMARY KEY IDENTITY(1,1),
    [LineID] INT REFERENCES [ProductionLines]([LineID]),
    [EquipmentName] VARCHAR(100) NOT NULL,
    [SerialNumber] VARCHAR(50) UNIQUE,
    [EquipmentType] VARCHAR(50),
    [Manufacturer] VARCHAR(100),
    [Status] VARCHAR(20) DEFAULT 'Operational',
    [LastMaintenance] DATETIME,
    [MaintenanceIntervalDays] INT,
    [CreatedDate] DATETIME DEFAULT GETDATE()
)

-- Production Orders
CREATE TABLE [dbo].[ProductionOrders] (
    [OrderID] INT PRIMARY KEY IDENTITY(1,1),
    [OrderNumber] VARCHAR(50) UNIQUE NOT NULL,
    [CustomerName] VARCHAR(150),
    [ProductCode] VARCHAR(50),
    [Quantity] INT,
    [StartDate] DATETIME,
    [ExpectedCompletion] DATETIME,
    [ActualCompletion] DATETIME,
    [Status] VARCHAR(20) DEFAULT 'Planned',
    [Priority] VARCHAR(20),
    [CreatedBy] VARCHAR(100),
    [CreatedDate] DATETIME DEFAULT GETDATE()
)

-- Safety Events (IMMUTABLE)
CREATE TABLE [dbo].[SafetyEvents] (
    [EventID] BIGINT PRIMARY KEY IDENTITY(1,1),
    [EventType] VARCHAR(50),
    [Severity] VARCHAR(20),
    [EquipmentID] INT REFERENCES [Equipment]([EquipmentID]),
    [Description] NVARCHAR(MAX),
    [UserID] VARCHAR(100),
    [IPAddress] VARCHAR(50),
    [Status] VARCHAR(20),
    [CreatedDate] DATETIME DEFAULT GETDATE()
)
GO

-- Prevent deletion of safety events (compliance)
CREATE TRIGGER trg_PreventDeleteSafetyEvents 
ON [dbo].[SafetyEvents] 
INSTEAD OF DELETE 
AS 
BEGIN
    RAISERROR('Safety events cannot be deleted. Compliance requirement.', 16, 1);
END;
GO

-- Create indexes
CREATE INDEX IX_ProductionLines_Status ON [ProductionLines]([Status])
CREATE INDEX IX_Equipment_LineID ON [Equipment]([LineID])
CREATE INDEX IX_Orders_Status ON [ProductionOrders]([Status])
CREATE INDEX IX_SafetyEvents_Date ON [SafetyEvents]([CreatedDate])
GO

-- Sample data
INSERT INTO [ProductionLines] (LineName, Location, LineType, CapacityPerHour)
VALUES 
    ('Assembly Line A', 'Building A Floor 1', 'Assembly', 150),
    ('Assembly Line B', 'Building A Floor 1', 'Assembly', 150),
    ('Packaging Line 1', 'Building A Floor 2', 'Packaging', 200),
    ('Welding Station', 'Building B', 'Welding', 80),
    ('Testing Lab', 'Building B', 'Testing', 50)
GO
```

---

## PHASE 5: Deploy Windows 11 Workstations (50x)

### Step 5.1: Create Workstation Template

Create master Windows 11 VM, then:

```powershell
# Join to domain
$credential = Get-Credential  # domain\administrator
Add-Computer -DomainName "factory.local" `
    -Credential $credential `
    -OUPath "OU=Computers,DC=factory,DC=local" `
    -Force -Restart

# After restart, install factory applications
choco install googlechrome -y
choco install vscode -y
choco install 7zip -y

# Map network drives
New-PSDrive -Name "F" -PSProvider FileSystem -Root "\\factory-fs\Production" -Persist
```

### Step 5.2: Clone and Deploy 50 Workstations

```powershell
# Clone from template VM 50 times
for ($i = 1; $i -le 50; $i++) {
    $vmName = "WS-$($i.ToString('D3'))"
    $clonePath = "D:\VMs\$vmName.vhdx"
    
    # Copy VM
    Copy-Item -Path "D:\VMs\Template-WS.vhdx" -Destination $clonePath
    
    # Create VM
    New-VM -Name $vmName `
        -MemoryStartupBytes 4GB `
        -VHDPath $clonePath `
        -SwitchName "FactorySwitch"
    
    # Start VM
    Start-VM -Name $vmName
    
    Write-Host "Created workstation: $vmName"
}

# Auto-configure each workstation via script
# (Run on each after boot)
```

---

## PHASE 6: Testing & Validation

### Test Active Directory
```powershell
# Verify domain functionality
Get-ADUser -Filter * | Measure-Object

# Test user authentication
$cred = Get-Credential  # factory\john.smith
Invoke-Command -ComputerName "WS-001" -Credential $cred -ScriptBlock { whoami }

# Verify group memberships
Get-ADMember -Identity "Production"
```

### Test File Sharing
```powershell
# Test SMB shares from workstation
Test-Path \\factory-fs\Production
Test-Path \\factory-fs\Engineering

# Verify permissions
Get-Acl \\factory-fs\Production
```

### Test SQL Server
```powershell
# Connect to SQL Server
$sqlInstance = "FACTORY-SQL\MSSQLSERVER"

# Query manufacturing database
Invoke-Sqlcmd -ServerInstance $sqlInstance `
    -Database "Manufacturing" `
    -Query "SELECT * FROM ProductionLines"
```

---

## Deployment Completed! 

**Total Time: 6-8 hours**

See **WINDOWS_CORE_ARCHITECTURE.md** for:
- MES application deployment (IIS/.NET)
- SCADA & OPC-UA server setup
- Safety Controller Windows Service
- Monitoring and logging configuration
