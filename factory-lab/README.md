# 🏭 Factory Lab - Comprehensive Training Environment

**Complete factory simulation with 50 employees, Active Directory, security-critical systems, and sensitive data handling.**

## Overview

Factory Lab is a production-grade training environment that simulates a complete manufacturing facility with:

- **👥 50 Factory Employees** with realistic departments and roles
- **🔐 Active Directory (Samba)** with LDAP authentication
- **📂 SMB File Sharing** with department-based access controls
- **🤖 Manufacturing Systems**: MES, SCADA, OPC-UA, PLC simulators
- **💾 Critical Databases**: PostgreSQL with encryption and RLS policies
- **⚠️ Safety Systems**: Emergency stops, interlocks (SIL 3 rated)
- **🔒 Sensitive Data**: Full encryption at rest/transit + audit trails
- **📊 Monitoring**: Elasticsearch, Kibana, Prometheus

## Quick Start (5 minutes)

### Prerequisites

- Docker & docker-compose
- Linux (Ubuntu 20.04+ recommended)
- 16GB+ RAM
- 50GB+ disk space

### Deployment

```bash
# Clone repository
cd /home/user/HAMIVTZAR

# Run initialization
cd factory-lab
chmod +x init-lab.sh
./init-lab.sh

# Wait for services to start (~2 minutes)
docker-compose ps

# Verify services
curl http://localhost:8000/health  # MES
curl http://localhost:8001/scada/health  # SCADA
```

**Services available after deployment:**

| Service | URL | Port | Purpose |
|---------|-----|------|---------|
| MES API | http://localhost:8000 | 8000 | Manufacturing Execution System |
| SCADA Dashboard | http://localhost:8001 | 8001 | SCADA monitoring |
| OPC-UA Server | opc.tcp://localhost:4840 | 4840 | Industrial protocol |
| Kibana Logs | http://localhost:5601 | 5601 | Log aggregation |
| Prometheus | http://localhost:9090 | 9090 | Metrics collection |

---

## Architecture

### Network Zones

```
┌─────────────────────────────────────────────────────┐
│ FACTORY LAB ENVIRONMENT                             │
├──────────────────────────────────────────────────────┤
│                                                     │
│ ┌──────────────────────────────────────────────┐   │
│ │ EXTERNAL (10.0.1.0/24)                      │   │
│ │ - Active Directory (Samba)                   │   │
│ │ - File Server (SMB)                          │   │
│ │ - DNS/DHCP                                   │   │
│ └──────────────────────────────────────────────┘   │
│            ↓ (Restricted)                           │
│ ┌──────────────────────────────────────────────┐   │
│ │ SUPERVISORY (10.0.2.0/24)                   │   │
│ │ - Manufacturing Execution System (MES)      │   │
│ │ - Historian Database                        │   │
│ │ - OPC-UA Server                             │   │
│ └──────────────────────────────────────────────┘   │
│            ↓ (Unidirectional)                       │
│ ┌──────────────────────────────────────────────┐   │
│ │ OPERATIONAL (10.0.3.0/24)                   │   │
│ │ - PLC Controllers                           │   │
│ │ - Modbus Gateway                            │   │
│ │ - Safety Systems                            │   │
│ └──────────────────────────────────────────────┘   │
│            ↓ (Isolated)                             │
│ ┌──────────────────────────────────────────────┐   │
│ │ FIELD (10.0.4.0/24)                         │   │
│ │ - Modbus Devices (simulated)                │   │
│ │ - Sensors                                   │   │
│ │ - Field Controllers                         │   │
│ └──────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| AD/Auth | Samba 4 + LDAP | 50 users, role-based access |
| File Server | Samba CIFS | Department SMB shares |
| MES | Python FastAPI | Production monitoring |
| Database | PostgreSQL | Manufacturing data + RLS |
| SCADA | Python Modbus | Industrial control simulation |
| OPC-UA | asyncua | Industrial protocol server |
| Safety | Custom PLC logic | Emergency stops, interlocks |
| Logging | Elasticsearch | Immutable audit trail |
| Monitoring | Prometheus + Kibana | Metrics & visualization |

---

## 50 Employees Distribution

```
PRODUCTION (18 employees)
├─ Shift Supervisors (3)
├─ Line Operators (10)
├─ Material Handlers (3)
└─ Maintenance (2)

ENGINEERING (12 employees)
├─ Lead Engineers (2)
├─ Process Engineers (4)
├─ Controls Engineers (3)
├─ Automation Techs (2)
└─ Systems Admin (1)

QUALITY/COMPLIANCE (8 employees)
├─ QA Manager (1)
├─ QA Specialists (3)
├─ Lab Technicians (2)
├─ Compliance Officer (1)
└─ Documentation (1)

MAINTENANCE (4 employees)
├─ Supervisor (1)
├─ Electrical Tech (1)
├─ Mechanical Tech (1)
└─ Preventive Maint (1)

MANAGEMENT (8 employees)
├─ Plant Director (1)
├─ Operations Managers (2)
├─ Finance Manager (1)
├─ HR Manager (1)
├─ IT Director (1)
├─ Safety Officer (1)
└─ Quality Manager (1)
```

---

## Configuration

### Environment Variables

Edit `factory-lab/.env`:

```bash
# Domain Configuration
DOMAIN=factory.local
NETBIOS_NAME=FACTORY
REALM=FACTORY.LOCAL

# Database
DB_PASSWORD=MESp@ssw0rd123!

# Timezone
TZ=UTC
```

### Sensitive Data Encryption

All sensitive data is encrypted:

- **At rest**: AES-256 (pgcrypto)
- **In transit**: TLS 1.3
- **Audit trail**: Immutable (7-year retention)

See [SENSITIVE_DATA_HANDLING.md](SENSITIVE_DATA_HANDLING.md) for full details.

### Safety Systems

Emergency stop, interlocks, and pressure relief are SIL 3 rated.

See [SAFETY_CRITICAL_SYSTEMS.md](SAFETY_CRITICAL_SYSTEMS.md) for testing and certification.

---

## Usage Examples

### Access MES API

```bash
# Get dashboard
curl http://localhost:8000/api/v1/dashboard

# Get production lines
curl http://localhost:8000/api/v1/production-lines

# Get equipment status
curl http://localhost:8000/api/v1/equipment
```

### SCADA Monitoring

```bash
# Get production line status
curl http://localhost:8001/scada/status

# Get specific production line
curl http://localhost:8001/scada/lines/line_1

# Get alarms
curl http://localhost:8001/scada/alarms

# Trigger E-stop
curl -X POST http://localhost:8001/scada/lines/line_1/control \
  -H "Content-Type: application/json" \
  -d '{"action":"stop"}'
```

### File Sharing (SMB)

```bash
# Mount from Linux
sudo mount -t cifs //localhost/Production \
  /mnt/factory-production \
  -o username=john.smith,password=FactoryP@ss123

# List shares
smbclient -L localhost -U john.smith
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mes-app
docker-compose logs -f scada-simulator

# Security audit logs
docker-compose logs -f elasticsearch | grep security
```

---

## Windows Server 2022 Integration

For production use with actual Windows infrastructure:

1. **Deploy Windows Server 2022 as primary AD DC**
2. **Create 50 users via PowerShell**
3. **Deploy Windows 11 workstations**
4. **Connect Linux containers to Windows AD**

See [WINDOWS_DEPLOYMENT.md](WINDOWS_DEPLOYMENT.md) for step-by-step PowerShell scripts.

---

## Data Handling

### Classification Levels

```
LEVEL 4 - CRITICAL
├─ Manufacturing formulas
├─ PLC control commands
├─ Emergency stops
└─ Encryption keys
   → AES-256 + TLS 1.3 + MFA

LEVEL 3 - CONFIDENTIAL
├─ Production batch records
├─ Equipment calibration
├─ Financial data
└─ Employee PII
   → AES-128 + TLS 1.2 + RBAC

LEVEL 2 - INTERNAL
├─ Work instructions
├─ Equipment manuals
└─ Shift schedules
   → Standard NTFS permissions

LEVEL 1 - PUBLIC
├─ Published specs
└─ Marketing materials
   → Standard network access
```

### Compliance

- **Data Retention**: 7 years (regulatory)
- **Audit Trail**: Immutable (cannot delete)
- **Backup**: Encrypted with GPG
- **Access Logging**: All actions tracked

See [SENSITIVE_DATA_HANDLING.md](SENSITIVE_DATA_HANDLING.md) for compliance details.

---

## Safety Critical Systems

### Emergency Stop

```bash
# Trigger emergency stop
curl -X POST http://localhost:5000/safety/e-stop \
  -d '{"source":"api","reason":"Manual test"}'

# Get safety status
curl http://localhost:5000/safety/status

# Reset (requires MFA)
curl -X POST http://localhost:5000/safety/reset \
  -d '{"authorized_by":"supervisor1","password":"MFA_CODE"}'
```

### SIL 3 Rated

- **Response time**: <200ms
- **Dual-channel monitoring**: Automatic E-stop if mismatch
- **Watchdog timeout**: E-stop if heartbeat missing >500ms
- **Pressure relief**: Automatic at 110% nominal

See [SAFETY_CRITICAL_SYSTEMS.md](SAFETY_CRITICAL_SYSTEMS.md) for full test procedures.

---

## Deployment Workflow

### Phase 1: Linux Containers (Start Here)
```bash
cd factory-lab
./init-lab.sh
# ~5 minutes, fully automated
```

### Phase 2: Windows Server 2022 AD (Optional)
```powershell
# On Windows Server 2022
# See WINDOWS_DEPLOYMENT.md section "Windows Server 2022 VM Setup"
# ~30 minutes
```

### Phase 3: Windows 11 Workstations (Optional)
```powershell
# Create 50 Windows 11 VMs
# Domain-join via script
# ~4 hours (can parallelize)
```

### Phase 4: Integration (Optional)
```bash
# Point Linux services to Windows AD
# Update docker-compose to use 10.0.1.100
# ~30 minutes
```

---

## Troubleshooting

### Services not starting

```bash
# Check logs
docker-compose logs -f

# Verify Docker is running
docker ps

# Check disk space
df -h

# Restart all services
docker-compose restart
```

### Cannot connect to MES API

```bash
# Check if container is running
docker ps | grep mes-app

# Check container logs
docker logs factory-mes-app

# Test connectivity
curl -v http://localhost:8000/health
```

### SMB shares not accessible

```bash
# Check Samba service
docker-compose logs samba-fs

# Test SMB port
nc -z localhost 445

# List shares
smbclient -L localhost
```

### Safety system tests failing

```bash
# Check emergency stop controller
docker-compose logs -f safety-controller

# Test E-stop endpoint
curl http://localhost:5000/safety/status
```

---

## Maintenance

### Backup

```bash
# Backup all data
docker-compose exec postgres-main pg_dump \
  -U mes_admin manufacturing > backup-$(date +%Y%m%d).sql

# Backup file shares
tar -czf factory-shares-backup.tar.gz factory-lab/data/smb/
```

### Reset to Baseline

```bash
# Stop all services
docker-compose down

# Remove volumes
docker volume rm factory-lab_*

# Restart
./init-lab.sh
```

### Update Configuration

```bash
# Edit .env
nano factory-lab/.env

# Reload
docker-compose up -d
```

---

## Production Deployment

For production use:

1. **Use Windows Server 2022 AD** instead of Samba
2. **Deploy Kubernetes** instead of docker-compose
3. **Enable TLS certificates** (self-signed → proper CAs)
4. **Use managed databases** (RDS, Azure SQL)
5. **Implement backup retention** (3-7 years)
6. **Enable compliance logging** (immutable audit trails)
7. **Deploy monitoring** (real Prometheus/Grafana)
8. **Use HSM** for encryption keys

---

## Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design details
- **[WINDOWS_DEPLOYMENT.md](WINDOWS_DEPLOYMENT.md)** - Windows Server 2022 & 11 setup
- **[SENSITIVE_DATA_HANDLING.md](SENSITIVE_DATA_HANDLING.md)** - Encryption & compliance
- **[SAFETY_CRITICAL_SYSTEMS.md](SAFETY_CRITICAL_SYSTEMS.md)** - Emergency stops & SIL 3
- **[API_REFERENCE.md](docs/API_REFERENCE.md)** - Service endpoints
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues

---

## Support

- 📖 See documentation in `/docs`
- 🐛 Check logs: `docker-compose logs -f`
- 💬 Review sample data: `factory-lab/data/employees.json`

---

## License

Educational use only. Do not use in production without proper security review and compliance verification.

---

## Quick Reference

```bash
# Start
./init-lab.sh

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Status
docker-compose ps

# Reset
docker-compose down -v && ./init-lab.sh
```

**Happy factory simulation! 🏭**
