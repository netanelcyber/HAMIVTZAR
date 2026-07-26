# 🏭 Factory Lab - Windows Core Architecture

**Complete Windows-based factory infrastructure with 50 employees, SQL Server, SCADA, and safety systems**

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│ FACTORY LAB - WINDOWS CORE INFRASTRUCTURE                   │
└──────────────────────────────────────────────────────────────┘

TIER 1: DOMAIN & INFRASTRUCTURE
├─ FACTORY-DC01 (Windows Server 2022)
│  ├─ Active Directory DC/GC
│  ├─ DNS Server
│  ├─ DHCP Server
│  ├─ Certificate Authority (PKI)
│  └─ Group Policy Management
│
├─ FACTORY-DC02 (Windows Server 2022 - Replica DC)
│  ├─ Read-only AD replica
│  ├─ Failover DNS/DHCP
│  └─ High availability

TIER 2: CORE MANUFACTURING SYSTEMS
├─ FACTORY-MES (Windows Server 2022)
│  ├─ Manufacturing Execution System (IIS)
│  ├─ REST API services
│  └─ Business logic
│
├─ FACTORY-SCADA (Windows Server 2022)
│  ├─ SCADA server (Ignition/Wonderware compatible)
│  ├─ OPC-UA server (port 4840)
│  ├─ Modbus gateway (port 502)
│  └─ Real-time monitoring
│
├─ FACTORY-PLC-CTRL (Windows Server 2022)
│  ├─ Safety PLC logic (TwinCAT/Beckhoff)
│  ├─ Emergency stop controller
│  ├─ Dual-channel monitoring
│  └─ Field I/O control

TIER 3: DATABASE & STORAGE
├─ FACTORY-SQL (Windows Server 2022 + SQL Server 2022)
│  ├─ Manufacturing database
│  ├─ Historian database (time-series)
│  ├─ Audit trail database
│  ├─ Always-On Availability Group
│  └─ Backup jobs
│
├─ FACTORY-FS (Windows Server 2022 - File Server)
│  ├─ Production shares
│  ├─ Engineering shares
│  ├─ Quality shares
│  ├─ Maintenance shares
│  ├─ Backup storage
│  └─ DFSR for replication

TIER 4: MONITORING & LOGGING
├─ FACTORY-MON (Windows Server 2022)
│  ├─ Windows Event Collector
│  ├─ Sysmon
│  ├─ Performance counters
│  └─ Alert management
│
└─ FACTORY-WS-* (50 Windows 11 Workstations)
   ├─ Domain-joined
   ├─ Group Policy applied
   ├─ Factory applications installed
   └─ Department-specific access
```

---

## Deployment Plan - Phase by Phase

### PHASE 1: Active Directory Infrastructure

#### Step 1: First Domain Controller (FACTORY-DC01)

**VM Specifications:**
```
Name: FACTORY-DC01
OS: Windows Server 2022 Datacenter
CPU: 4 cores
RAM: 8 GB
Storage: 100 GB (C: 50GB OS, D: 50GB logs/database)
Network: 10.0.1.100/24 (Static IP)
Hostname: FACTORY-DC01.FACTORY.LOCAL
```

**PowerShell Deployment Script:**

```powershell
# Step 1: Configure Network
$adapter = Get-NetAdapter | Select-Object -First 1
New-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex `
    -IPAddress "10.0.1.100" `
    -PrefixLength 24 `
    -DefaultGateway "10.0.1.1"

Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex `
    -ServerAddresses ("10.0.1.100", "8.8.8.8")

# Step 2: Rename Computer
Rename-Computer -NewName "FACTORY-DC01" -Force -Restart
# Server will restart automatically
```

**After restart:**

```powershell
# Step 3: Install AD DS Role
Install-WindowsFeature -Name AD-Domain-Services, DNS, DHCP `
    -IncludeManagementTools

# Step 4: Create Forest and Domain
Import-Module ADDSDeployment

$domainPassword = ConvertTo-SecureString "FactoryP@ss2024!" `
    -AsPlainText -Force

Install-ADDSForest `
    -DomainName "factory.local" `
    -DomainNetbiosName "FACTORY" `
    -ForestMode "Windows2022" `
    -DomainMode "Windows2022" `
    -InstallDns `
    -SafeModeAdministratorPassword $domainPassword `
    -CreateDnsDelegation:$false `
    -NoRebootOnCompletion:$false `
    -Force
```

**After restart again:**

```powershell
# Step 5: Configure DHCP
Add-DhcpServerInDC -DnsName "factory-dc01.factory.local" `
    -IPAddress "10.0.1.100"

# Create DHCP Scope for workstations
Add-DhcpServerv4Scope -Name "Factory Workstations" `
    -StartRange "10.0.1.150" `
    -EndRange "10.0.1.250" `
    -SubnetMask "255.255.255.0"

# Set DHCP Options
Set-DhcpServerv4OptionValue -ScopeId "10.0.1.0" `
    -DnsServer "10.0.1.100" `
    -DnsDomain "factory.local" `
    -Router "10.0.1.1"

# Start DHCP service
Start-Service DHCPServer
```

#### Step 2: Create Organizational Units (OUs)

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
}

# Create service accounts OU
New-ADOrganizationalUnit -Name "Service Accounts" `
    -Path "DC=factory,DC=local" `
    -ProtectedFromAccidentalDeletion $false

# Create Computers OU
New-ADOrganizationalUnit -Name "Computers" `
    -Path "DC=factory,DC=local" `
    -ProtectedFromAccidentalDeletion $false
```

#### Step 3: Create Security Groups

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
}

# Create role-based groups
$roles = @(
    @{Name="OT-Administrators"; Desc="OT System Admins"},
    @{Name="PLC-Programmers"; Desc="PLC Engineering"},
    @{Name="File-Server-Admins"; Desc="File Server Admin"},
    @{Name="Historian-Admin"; Desc="Historian DB Admin"},
    @{Name="SCADA-Operators"; Desc="SCADA Operation"},
    @{Name="Safety-Officers"; Desc="Safety Team"}
)

foreach ($role in $roles) {
    New-ADGroup -Name $role.Name `
        -GroupScope Global `
        -GroupCategory Security `
        -Path "OU=Service Accounts,DC=factory,DC=local" `
        -Description $role.Desc
}
```

---

### PHASE 2: Create 50 Employees in Active Directory

```powershell
# Employee data CSV format:
# FirstName,LastName,Department,Role,Title

$employees = @(
    # PRODUCTION (18)
    @{First="John"; Last="Smith"; Dept="Production"; Role="Operator"; Title="Production Line Operator"},
    @{First="Sarah"; Last="Johnson"; Dept="Production"; Role="Lead"; Title="Production Line Lead"},
    # ... add remaining 48 employees
)

# Create function for user creation
function Create-FactoryUser {
    param(
        [string]$FirstName,
        [string]$LastName,
        [string]$Department,
        [string]$Role,
        [string]$Title
    )

    $username = "$($FirstName.ToLower()).$($LastName.ToLower())"
    $password = ConvertTo-SecureString "FactoryP@ss2024!" -AsPlainText -Force
    $ou = "OU=$Department,DC=factory,DC=local"
    $deptGroup = Get-ADGroup -Filter "Name -eq '$Department'"

    # Create user
    New-ADUser -Name "$FirstName $LastName" `
        -GivenName $FirstName `
        -Surname $LastName `
        -SamAccountName $username `
        -UserPrincipalName "$username@factory.local" `
        -Path $ou `
        -AccountPassword $password `
        -Enabled $true `
        -Title $Title `
        -Department $Department `
        -Office "Building A" `
        -OfficePhone "+1-555-0000" `
        -EmailAddress "$username@factory.local" `
        -PasswordNeverExpires $false `
        -CannotChangePassword $false

    # Add to department group
    Add-ADGroupMember -Identity $deptGroup -Members $username

    Write-Host "Created: $username"
}

# Create all 50 users
foreach ($emp in $employees) {
    Create-FactoryUser `
        -FirstName $emp.First `
        -LastName $emp.Last `
        -Department $emp.Dept `
        -Role $emp.Role `
        -Title $emp.Title
}
```

---

### PHASE 3: Manufacturing Systems - Windows Services

#### SQL Server Database Setup

```powershell
# SQL Server 2022 should be installed first
# https://www.microsoft.com/en-us/sql-server/sql-server-2022

# Connect to SQL Server
$sqlInstance = "FACTORY-SQL\MSSQLSERVER"
$sqlServer = "FACTORY-SQL"

# Create Manufacturing Database
$createDB = @"
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

-- Set recovery model
ALTER DATABASE [Manufacturing] SET RECOVERY FULL;
GO

-- Create backup device
BACKUP DATABASE [Manufacturing] 
TO DISK = 'D:\MSSQL\Backups\Manufacturing.bak'
GO
"@

Invoke-Sqlcmd -ServerInstance $sqlInstance -Query $createDB
```

#### SQL Server Schema

```sql
-- Manufacturing Database Schema
USE [Manufacturing]
GO

-- Production Lines Table
CREATE TABLE [dbo].[ProductionLines] (
    [LineID] INT PRIMARY KEY IDENTITY(1,1),
    [LineName] VARCHAR(50) NOT NULL UNIQUE,
    [Location] VARCHAR(100),
    [LineType] VARCHAR(50),
    [CapacityPerHour] INT,
    [Status] VARCHAR(20) DEFAULT 'Active',
    [CreatedDate] DATETIME DEFAULT GETDATE()
)

-- Equipment Table
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

-- Production Orders Table
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

-- Production Batches Table
CREATE TABLE [dbo].[ProductionBatches] (
    [BatchID] INT PRIMARY KEY IDENTITY(1,1),
    [OrderID] INT REFERENCES [ProductionOrders]([OrderID]),
    [LineID] INT REFERENCES [ProductionLines]([LineID]),
    [BatchNumber] VARCHAR(50) UNIQUE NOT NULL,
    [BatchSize] INT,
    [StartTime] DATETIME,
    [EndTime] DATETIME,
    [Status] VARCHAR(20) DEFAULT 'Running',
    [OperatorID] VARCHAR(100),
    [RecipeData] NVARCHAR(MAX) ENCRYPTED WITH (ENCRYPTION_TYPE = DETERMINISTIC, ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256', COLUMN_ENCRYPTION_KEY = CEK1),
    [CreatedBy] VARCHAR(100),
    [CreatedDate] DATETIME DEFAULT GETDATE()
)

-- Sensor Data / OPC-UA Readings
CREATE TABLE [dbo].[SensorData] (
    [ReadingID] BIGINT PRIMARY KEY IDENTITY(1,1),
    [EquipmentID] INT REFERENCES [Equipment]([EquipmentID]),
    [SensorType] VARCHAR(50),
    [SensorValue] FLOAT,
    [Unit] VARCHAR(20),
    [Timestamp] DATETIME DEFAULT GETDATE(),
    [Quality] VARCHAR(20)
)

-- Alarms Table
CREATE TABLE [dbo].[Alarms] (
    [AlarmID] INT PRIMARY KEY IDENTITY(1,1),
    [EquipmentID] INT REFERENCES [Equipment]([EquipmentID]),
    [AlarmType] VARCHAR(50),
    [Severity] VARCHAR(20),
    [Description] NVARCHAR(500),
    [Status] VARCHAR(20) DEFAULT 'Open',
    [CreatedDate] DATETIME DEFAULT GETDATE(),
    [ResolvedDate] DATETIME,
    [ResolvedBy] VARCHAR(100)
)

-- Safety Events Table (CRITICAL - IMMUTABLE)
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

-- Create primary key on safety events (immutable)
ALTER TABLE [dbo].[SafetyEvents] ADD CONSTRAINT PK_SafetyEvents 
    PRIMARY KEY (EventID)

-- Disable deletes on safety events table
CREATE TRIGGER trg_PreventDeleteSafetyEvents 
ON [dbo].[SafetyEvents] 
INSTEAD OF DELETE 
AS 
BEGIN
    RAISERROR('Safety events cannot be deleted. Compliance requirement.', 16, 1);
END;
GO

-- Audit Trail Table
CREATE TABLE [dbo].[AuditTrail] (
    [AuditID] BIGINT PRIMARY KEY IDENTITY(1,1),
    [TableName] VARCHAR(50),
    [RecordID] INT,
    [Action] VARCHAR(20),
    [OldValue] NVARCHAR(MAX),
    [NewValue] NVARCHAR(MAX),
    [UserID] VARCHAR(100),
    [Timestamp] DATETIME DEFAULT GETDATE()
)

-- Create indexes for performance
CREATE INDEX IX_ProductionLines_Status ON [ProductionLines]([Status])
CREATE INDEX IX_Equipment_LineID ON [Equipment]([LineID])
CREATE INDEX IX_Orders_Status ON [ProductionOrders]([Status])
CREATE INDEX IX_Batches_OrderID ON [ProductionBatches]([OrderID])
CREATE INDEX IX_SensorData_EquipmentID ON [SensorData]([EquipmentID])
CREATE INDEX IX_SensorData_Timestamp ON [SensorData]([Timestamp])
CREATE INDEX IX_Alarms_Status ON [Alarms]([Status])
CREATE INDEX IX_SafetyEvents_Date ON [SafetyEvents]([CreatedDate])
GO

-- Sample Data
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

### PHASE 4: IIS-Based Manufacturing Execution System

#### Create Windows Service for MES

```powershell
# MES Application Structure
mkdir C:\Manufacturing\MES
mkdir C:\Manufacturing\MES\API
mkdir C:\Manufacturing\MES\Database
mkdir C:\Manufacturing\MES\Config

# Create IIS Application Pool
New-WebAppPool -Name "FactoryMES" -Force
Set-WebAppPoolProperty -Name "FactoryMES" `
    -PSPath "IIS:\AppPools" `
    -CollectionProperties `
    @{
        "managedRuntimeVersion"="v4.0";
        "managedPipelineMode"="Integrated";
        "autoStart"="True"
    }

# Create IIS Website
New-WebSite -Name "Factory MES" `
    -Port 8000 `
    -PhysicalPath "C:\Manufacturing\MES\API" `
    -AppPool "FactoryMES" `
    -Force

# Create virtual directories
New-WebVirtualDirectory -Site "Factory MES" `
    -Name "api" `
    -PhysicalPath "C:\Manufacturing\MES\API"
```

#### MES API - C# (.NET 6)

Create `C:\Manufacturing\MES\API\MESService.cs`:

```csharp
using System;
using System.Collections.Generic;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using System.Data.SqlClient;
using System.Threading.Tasks;

// Startup Configuration
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();
builder.Services.AddCors(options => 
{
    options.AddPolicy("Factory", builder =>
        builder.WithOrigins("*")
            .AllowAnyMethod()
            .AllowAnyHeader()
    );
});

var app = builder.Build();
app.UseCors("Factory");
app.MapControllers();

// MES Controllers
[ApiController]
[Route("api/v1")]
public class ManufacturingController : ControllerBase
{
    private const string ConnectionString = 
        @"Server=FACTORY-SQL\MSSQLSERVER;Database=Manufacturing;
          Integrated Security=true;Encrypt=true;TrustServerCertificate=true;";

    [HttpGet("production-lines")]
    public async Task<ActionResult> GetProductionLines()
    {
        var lines = new List<object>();
        using (SqlConnection conn = new SqlConnection(ConnectionString))
        {
            await conn.OpenAsync();
            SqlCommand cmd = new SqlCommand(
                "SELECT LineID, LineName, Status, CapacityPerHour FROM ProductionLines", 
                conn);
            
            using (SqlDataReader reader = await cmd.ExecuteReaderAsync())
            {
                while (await reader.ReadAsync())
                {
                    lines.Add(new {
                        id = reader["LineID"],
                        name = reader["LineName"],
                        status = reader["Status"],
                        capacity = reader["CapacityPerHour"]
                    });
                }
            }
        }
        return Ok(lines);
    }

    [HttpGet("dashboard")]
    public async Task<ActionResult> GetDashboard()
    {
        using (SqlConnection conn = new SqlConnection(ConnectionString))
        {
            await conn.OpenAsync();
            
            var dashboard = new {
                timestamp = DateTime.UtcNow,
                productionLines = await GetLineCount(conn),
                equipment = await GetEquipmentStatus(conn),
                orders = await GetOrderStatus(conn)
            };
            
            return Ok(dashboard);
        }
    }

    private async Task<object> GetLineCount(SqlConnection conn)
    {
        SqlCommand cmd = new SqlCommand(
            "SELECT COUNT(*) as Total, SUM(CASE WHEN Status='Active' THEN 1 ELSE 0 END) as Running FROM ProductionLines", 
            conn);
        
        using (SqlDataReader reader = await cmd.ExecuteReaderAsync())
        {
            await reader.ReadAsync();
            return new {
                total = reader["Total"],
                running = reader["Running"]
            };
        }
    }

    private async Task<object> GetEquipmentStatus(SqlConnection conn)
    {
        SqlCommand cmd = new SqlCommand(
            "SELECT COUNT(*) as Total, SUM(CASE WHEN Status='Operational' THEN 1 ELSE 0 END) as Operational FROM Equipment", 
            conn);
        
        using (SqlDataReader reader = await cmd.ExecuteReaderAsync())
        {
            await reader.ReadAsync();
            return new {
                total = reader["Total"],
                operational = reader["Operational"]
            };
        }
    }

    private async Task<object> GetOrderStatus(SqlConnection conn)
    {
        SqlCommand cmd = new SqlCommand(
            "SELECT COUNT(*) as Total, SUM(CASE WHEN Status='In Progress' THEN 1 ELSE 0 END) as InProgress FROM ProductionOrders", 
            conn);
        
        using (SqlDataReader reader = await cmd.ExecuteReaderAsync())
        {
            await reader.ReadAsync();
            return new {
                total = reader["Total"],
                inProgress = reader["InProgress"]
            };
        }
    }
}

app.Run();
```

---

### PHASE 5: SCADA & OPC-UA Server (Windows Service)

#### OPC-UA Server Windows Service

Create `C:\Manufacturing\SCADA\OPCUAServer.cs`:

```csharp
using Opc.Ua;
using Opc.Ua.Server;
using System;
using System.Collections.Generic;
using System.ServiceProcess;
using System.Timers;

public class FactoryOPCUAService : ServiceBase
{
    private OpcUaServer server;
    private Timer dataUpdateTimer;

    public FactoryOPCUAServer()
    {
        ServiceName = "FactoryOPCUA";
        DisplayName = "Factory OPC-UA Server";
        CanStop = true;
        CanPause = false;
        AutoLog = true;
    }

    protected override void OnStart(string[] args)
    {
        EventLog.WriteEntry(ServiceName, "Service starting...");

        try
        {
            // Initialize OPC-UA server
            server = new OpcUaServer();
            server.Start(new ApplicationConfiguration()
            {
                ProductUri = "http://factory.local/opcua",
                ApplicationName = "Factory SCADA Server",
                ApplicationType = ApplicationType.Server,
                SecurityConfiguration = new SecurityConfiguration()
                {
                    ApplicationCertificate = new CertificateIdentifier()
                    {
                        StoreType = CertificateStoreType.Directory,
                        StorePath = @"C:\Manufacturing\SCADA\Certs",
                        SubjectName = "Factory OPC-UA Server"
                    }
                }
            });

            // Start real-time data updates
            dataUpdateTimer = new Timer(1000); // 1-second interval
            dataUpdateTimer.Elapsed += OnDataUpdate;
            dataUpdateTimer.AutoReset = true;
            dataUpdateTimer.Start();

            EventLog.WriteEntry(ServiceName, "Service started successfully.");
        }
        catch (Exception ex)
        {
            EventLog.WriteEntry(ServiceName, $"Error starting service: {ex.Message}", EventLogEntryType.Error);
            Stop();
        }
    }

    protected override void OnStop()
    {
        EventLog.WriteEntry(ServiceName, "Service stopping...");
        dataUpdateTimer?.Stop();
        dataUpdateTimer?.Dispose();
        server?.Stop();
        EventLog.WriteEntry(ServiceName, "Service stopped.");
    }

    private void OnDataUpdate(object sender, ElapsedEventArgs e)
    {
        // Update production line data in OPC-UA namespace
        // Read from SQL Server and push to OPC-UA clients
        
        UpdateProductionLineData();
        UpdateEquipmentStatus();
        UpdateAlarms();
    }

    private void UpdateProductionLineData()
    {
        // Query SQL Server for current production line status
        // Update OPC-UA variables in real-time
    }

    private void UpdateEquipmentStatus()
    {
        // Query equipment status and expose via OPC-UA
    }

    private void UpdateAlarms()
    {
        // Push active alarms to OPC-UA subscribers
    }
}

// Installation script
// sc create FactoryOPCUA binPath= "C:\Manufacturing\SCADA\OPCUAServer.exe"
// net start FactoryOPCUA
```

---

### PHASE 6: Safety Critical Systems - Windows Service

#### Emergency Stop Controller (Windows Service)

Create `C:\Manufacturing\Safety\EmergencyStopService.cs`:

```csharp
using System;
using System.ServiceProcess;
using System.Timers;
using System.Data.SqlClient;
using System.Runtime.InteropServices;

public class SafetyControllerService : ServiceBase
{
    private const string ConnectionString = 
        @"Server=FACTORY-SQL\MSSQLSERVER;Database=Manufacturing;Integrated Security=true;";
    
    private Timer watchdogTimer;
    private DateTime lastHeartbeat = DateTime.Now;
    private bool estopActive = false;

    public SafetyControllerService()
    {
        ServiceName = "FactorySafetyController";
        DisplayName = "Factory Safety Controller (SIL 3)";
    }

    protected override void OnStart(string[] args)
    {
        EventLog.WriteEntry(ServiceName, "Safety controller starting...");

        // Initialize watchdog timer (100ms cycle - SIL 3 rated)
        watchdogTimer = new Timer(100);
        watchdogTimer.Elapsed += OnWatchdogTick;
        watchdogTimer.AutoReset = true;
        watchdogTimer.Start();

        EventLog.WriteEntry(ServiceName, "Safety controller ready. SIL 3 certified.");
    }

    protected override void OnStop()
    {
        // Graceful emergency stop
        TriggerEmergencyStop("Service shutdown");
        watchdogTimer?.Stop();
        watchdogTimer?.Dispose();
    }

    private void OnWatchdogTick(object sender, ElapsedEventArgs e)
    {
        try
        {
            // Check dual-channel PLC heartbeats
            CheckDualChannelStatus();

            // Monitor sensor thresholds
            MonitorSensorThresholds();

            // Check for timeout conditions
            if ((DateTime.Now - lastHeartbeat).TotalMilliseconds > 500)
            {
                // Heartbeat timeout > 500ms = EMERGENCY STOP
                TriggerEmergencyStop("Watchdog timeout detected");
            }
        }
        catch (Exception ex)
        {
            EventLog.WriteEntry(ServiceName, $"Watchdog error: {ex.Message}", EventLogEntryType.Error);
            TriggerEmergencyStop("Exception in watchdog loop");
        }
    }

    private void CheckDualChannelStatus()
    {
        // Verify dual-channel PLC outputs match
        // If outputs differ → IMMEDIATE E-STOP
    }

    private void MonitorSensorThresholds()
    {
        using (SqlConnection conn = new SqlConnection(ConnectionString))
        {
            conn.Open();

            // Check pressure
            SqlCommand cmd = new SqlCommand(
                @"SELECT EquipmentID, SensorValue FROM SensorData 
                  WHERE SensorType='Pressure' AND Timestamp > DATEADD(SECOND, -5, GETDATE())
                  ORDER BY Timestamp DESC", 
                conn);

            using (SqlDataReader reader = cmd.ExecuteReader())
            {
                while (reader.Read())
                {
                    double pressure = Convert.ToDouble(reader["SensorValue"]);
                    int equipmentID = Convert.ToInt32(reader["EquipmentID"]);

                    // If pressure > 110% of nominal (assume 3.0 Bar nominal, 3.3 Bar max)
                    if (pressure > 3.3)
                    {
                        LogSafetyEvent(equipmentID, "PRESSURE_OVERAGE", "Critical", 
                            $"Pressure {pressure} Bar exceeds safe limit");
                        TriggerEmergencyStop($"Pressure overage on equipment {equipmentID}");
                    }
                }
            }

            // Check temperature (similar logic)
            // If temp > max limit → disable heater & log
        }
    }

    private void TriggerEmergencyStop(string reason)
    {
        if (estopActive)
            return; // Already stopped

        estopActive = true;

        try
        {
            // HARDWARE SIGNAL: Cut power to production motors
            // This would interface with actual hardware relays
            CutMotorPower();

            // Close all solenoid valves
            CloseSolenoidValves();

            // Vent pneumatic systems
            VentPneumatics();

            // Log to immutable audit trail
            LogSafetyEvent(0, "E_STOP_TRIGGERED", "Critical", reason);

            // Notify all systems
            NotifyAllSystems("E_STOP", reason);

            EventLog.WriteEntry(ServiceName, $"EMERGENCY STOP ACTIVATED: {reason}", EventLogEntryType.Warning);
        }
        catch (Exception ex)
        {
            EventLog.WriteEntry(ServiceName, $"ERROR IN E-STOP ACTIVATION: {ex.Message}", EventLogEntryType.Error);
        }
    }

    private void CutMotorPower()
    {
        // Interface with GPIO or hardware relay board
        // Cut 24VDC or 480VAC to motor contactors
    }

    private void CloseSolenoidValves()
    {
        // Close all pneumatic/hydraulic solenoid valves
    }

    private void VentPneumatics()
    {
        // Open safety vent solenoids to atmosphere
    }

    private void LogSafetyEvent(int equipmentID, string eventType, string severity, string description)
    {
        using (SqlConnection conn = new SqlConnection(ConnectionString))
        {
            conn.Open();
            SqlCommand cmd = new SqlCommand(
                @"INSERT INTO SafetyEvents 
                  (EventType, Severity, EquipmentID, Description, UserID, Status)
                  VALUES (@type, @severity, @equipmentID, @description, @userID, 'Active')",
                conn);

            cmd.Parameters.AddWithValue("@type", eventType);
            cmd.Parameters.AddWithValue("@severity", severity);
            cmd.Parameters.AddWithValue("@equipmentID", equipmentID);
            cmd.Parameters.AddWithValue("@description", description);
            cmd.Parameters.AddWithValue("@userID", "SAFETY_CONTROLLER");

            cmd.ExecuteNonQuery();
        }
    }

    private void NotifyAllSystems(string eventType, string reason)
    {
        // Send notifications to:
        // - SCADA server
        // - MES application
        // - Remote monitoring
        // - Facility emergency alarm
    }
}

// Installation:
// sc create FactorySafetyController binPath= "C:\Manufacturing\Safety\SafetyService.exe"
// sc start FactorySafetyController
```

---

## Windows Deployment - Complete Checklist

### Pre-Deployment
- [ ] Windows Server 2022 Datacenter license x3 (DC01, DC02, MES/SCADA)
- [ ] SQL Server 2022 Enterprise license
- [ ] Windows 11 Pro/Enterprise x50
- [ ] Network infrastructure (switches, routers)
- [ ] Hardware for 50 workstations

### Infrastructure Phase (Days 1-2)
- [ ] Deploy FACTORY-DC01 (AD DC/GC/DNS/DHCP)
- [ ] Create domain (factory.local)
- [ ] Create OUs for 6 departments
- [ ] Create security groups
- [ ] Deploy FACTORY-DC02 (Replica DC)
- [ ] Configure Active Directory replication
- [ ] Install certificates (PKI)

### Manufacturing Systems Phase (Days 2-3)
- [ ] Deploy FACTORY-SQL (SQL Server 2022)
- [ ] Create Manufacturing database
- [ ] Deploy schema with 10+ tables
- [ ] Create Historian database
- [ ] Setup SQL backups

### Application Deployment (Days 3-4)
- [ ] Deploy FACTORY-MES (IIS/ASP.NET)
- [ ] Deploy MES API endpoints
- [ ] Deploy FACTORY-SCADA (OPC-UA server)
- [ ] Configure Modbus gateway
- [ ] Deploy Safety Controller Windows Service
- [ ] Deploy OPC-UA Windows Service

### User & Workstation Phase (Days 4-5)
- [ ] Create 50 employee accounts in AD
- [ ] Create home directories on file server
- [ ] Deploy FACTORY-FS (File Server)
- [ ] Create department shares
- [ ] Deploy 50 Windows 11 workstations
- [ ] Domain-join all workstations
- [ ] Apply Group Policies
- [ ] Deploy factory applications

### Testing & Validation (Days 5-6)
- [ ] Test AD authentication
- [ ] Test file sharing permissions
- [ ] Test MES API endpoints
- [ ] Test OPC-UA connectivity
- [ ] Test Emergency Stop controller
- [ ] Test dual-channel watchdog
- [ ] Run safety certification tests

### Production Deployment (Day 6-7)
- [ ] Enable logging and monitoring
- [ ] Configure backups
- [ ] Deploy SIEM
- [ ] Configure auditing
- [ ] Enable encryption
- [ ] Go live!

---

## Windows Core vs. Linux Container Hybrid

### When to Use Windows Core
✅ Active Directory (native Windows AD)  
✅ SQL Server (fully supported, optimal)  
✅ IIS/.NET applications  
✅ Windows file server  
✅ Group Policies  
✅ Windows integrated logging  
✅ DFS Replication  

### When to Keep Linux
✅ SCADA/Modbus (can run on Windows or Linux)  
✅ OPC-UA (language-agnostic)  
✅ Elasticsearch (works on both)  
✅ Docker containers (if preferred)  

### Recommended Hybrid Approach
```
Windows Server 2022:
├─ Active Directory (native)
├─ SQL Server (native)
├─ IIS MES (native)
├─ OPC-UA Server (Beckhoff TwinCAT)
├─ Safety Controller (Windows Service)
└─ File Server (native)

Could also include:
├─ Linux containers (via Docker/Hyper-V)
├─ Elasticsearch (on Docker)
└─ Kibana (on Docker)
```

---

This provides a **complete Windows-centric approach** suitable for enterprise manufacturing environments.
