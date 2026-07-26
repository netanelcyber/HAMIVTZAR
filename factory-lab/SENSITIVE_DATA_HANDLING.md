# Factory Lab - Sensitive Data Handling Guide

## Data Classification Framework

### Classification Levels

```
LEVEL 4 - CRITICAL
├─ Proprietary manufacturing formulas
├─ OPC-UA control commands to PLCs
├─ Safety interlocks and emergency stops
├─ Encryption keys and credentials
└─ Audit logs (immutable, compliance-required)
   Protection: AES-256, TLS 1.3, MFA, Audit trail

LEVEL 3 - CONFIDENTIAL
├─ Production batch records
├─ Equipment calibration data
├─ Financial/cost data
├─ Maintenance schedules
├─ Employee PII (names, contact info)
└─ Customer orders
   Protection: AES-128, TLS 1.2, Role-based access, Logging

LEVEL 2 - INTERNAL
├─ General work instructions
├─ Equipment manuals
├─ Shift schedules
├─ Public announcements
└─ Training materials
   Protection: Standard NTFS/Unix permissions, Basic logging

LEVEL 1 - PUBLIC
├─ Published specs
├─ Marketing materials
└─ General information
   Protection: Standard network access
```

---

## Data Flow Architecture

### Secure Transfer Paths

```
┌─────────────────────────────────────────────────────────────┐
│ SENSITIVE DATA TRANSFER FLOWS                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. WINDOWS 11 WORKSTATION ──[NTLM + TLS]──> FILE SERVER   │
│    (User: john.smith)                  (Prod share)        │
│    - Access log with timestamp                             │
│    - File hash recorded                                    │
│    - Modification logged                                   │
│                                                             │
│ 2. MES APP ──[JDBC + TLS]──> POSTGRES DATABASE             │
│    (LDAP auth from AD)         (RLS policies enforce)      │
│    - All queries logged                                    │
│    - Data access tracked per user                          │
│    - Encryption at rest with pgcrypto                      │
│                                                             │
│ 3. WINDOWS 11 ──[OPC-UA + TLS]──> OPC-UA SERVER           │
│    (HMI client)                 (Linux container)           │
│    - Client certificate validation                         │
│    - User identity from AD                                 │
│    - All commands logged                                   │
│    - Audit trail in Elasticsearch                          │
│                                                             │
│ 4. ENGINEERING WORKSTATION ──[SFTP]──> PLC FILES           │
│    (Configure ladder logic)     (Version control + backup)  │
│    - Signing with engineer ID                              │
│    - Change audit trail                                    │
│    - Pre-deployment approval workflow                      │
│                                                             │
│ 5. FILE SERVER ──[BACKUP ENCRYPTION]──> BACKUP STORAGE     │
│    (Hourly incremental)             (AES-256 encrypted)    │
│    - Encryption keys in HSM (Hardware Security Module)     │
│    - Backup integrity checks                               │
│    - Retention policy enforced (7 years)                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation: Data Handling at Each Layer

### 1. File Server (SMB) - Sensitive Data Protection

```smb.conf
# /factory-lab/configs/smbshares.conf additions

[Production]
    # Contains batch records (LEVEL 3)
    path = /srv/shares/Production
    comment = Production - CONFIDENTIAL
    
    # Access control
    valid users = @Production @Manager @Quality
    force group = +Production
    
    # Encryption requirements
    smb encrypt = required
    server signing = required
    
    # Audit all access
    audit mode = Yes
    full_audit: create yes delete yes rename yes unlink yes
    
    # Prevent deletion of sensitive files
    delete veto files = Yes
    veto files = *.bak *.old

[SCADA_Configs]
    # Contains PLC programs (LEVEL 4)
    path = /srv/shares/SCADA
    
    # Only engineers can access
    valid users = @Engineering @Manager
    force group = +Engineering
    read only = Yes  # Write-only via version control
    
    # Strict audit
    full_audit: all = connect disconnect openX writeX deleteX unlink
    
    # Immutable backups
    vfs objects = shadow_copy2
```

### 2. Database - Encryption & Row-Level Security

```sql
-- /factory-lab/scripts/init-mes-db.sql additions

-- Enable encryption at rest
CREATE EXTENSION pgcrypto;

-- Table for sensitive batch records
CREATE TABLE production_batches_sensitive (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES production_orders(id),
    batch_number VARCHAR(50),
    recipe_data BYTEA,  -- Encrypted with pgcrypto
    operator_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    -- Audit columns
    access_log JSONB,
    data_hash VARCHAR(64),
    integrity_check BOOLEAN DEFAULT true
);

-- Encryption function
CREATE OR REPLACE FUNCTION encrypt_sensitive_data(data TEXT, key TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN pgcrypto.encrypt(data::bytea, key::bytea, 'aes');
END;
$$ LANGUAGE plpgsql;

-- Decryption (with audit)
CREATE OR REPLACE FUNCTION decrypt_sensitive_data(encrypted_data BYTEA, user_id TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Log access attempt
    INSERT INTO access_audit (table_name, user_id, action, timestamp)
    VALUES ('production_batches_sensitive', user_id, 'decrypt', NOW());
    
    -- Return decrypted data
    RETURN decrypt(encrypted_data, 'factory_key'::bytea, 'aes')::TEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Row-level security policies
ALTER TABLE production_batches_sensitive ENABLE ROW LEVEL SECURITY;

-- Policy: Users see only their department's batches
CREATE POLICY production_rls ON production_batches_sensitive
    USING (
        operator_id IN (
            SELECT username FROM operators
            WHERE department = (
                SELECT department FROM ad_users
                WHERE username = CURRENT_USER
            )
        )
    );

-- Audit trail table
CREATE TABLE access_audit (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50),
    record_id INTEGER,
    user_id VARCHAR(100),
    action VARCHAR(20),  -- read, write, delete, export
    old_value JSONB,
    new_value JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    result VARCHAR(20)   -- success, denied, failed
);

-- Index for performance
CREATE INDEX idx_access_audit_user_time ON access_audit(user_id, timestamp DESC);
```

### 3. API Layer - Authentication & Data Sanitization

```python
# /factory-lab/docker/mes/app.py additions

from flask import Flask, request, abort
from functools import wraps
import logging
import json
from datetime import datetime
import hmac
import hashlib

app = Flask(__name__)

# Audit logger
audit_log = logging.getLogger('audit')
audit_handler = logging.FileHandler('/var/log/factory-lab/api-audit.log')
audit_log.addHandler(audit_handler)

def audit_access(action):
    """Decorator to log API access to sensitive endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = request.headers.get('X-User-ID', 'unknown')
            ip_address = request.remote_addr
            
            audit_log.info(json.dumps({
                'timestamp': datetime.utcnow().isoformat(),
                'user': user,
                'action': action,
                'endpoint': request.path,
                'method': request.method,
                'ip_address': ip_address,
                'status': 'attempted'
            }))
            
            try:
                result = f(*args, **kwargs)
                audit_log.info(json.dumps({
                    'timestamp': datetime.utcnow().isoformat(),
                    'user': user,
                    'action': action,
                    'result': 'success'
                }))
                return result
            except Exception as e:
                audit_log.error(json.dumps({
                    'timestamp': datetime.utcnow().isoformat(),
                    'user': user,
                    'action': action,
                    'error': str(e),
                    'result': 'failed'
                }))
                abort(500)
        return decorated_function
    return decorator

@app.route('/api/v1/batch-recipe/<int:batch_id>', methods=['GET'])
@audit_access('read_sensitive_recipe')
def get_batch_recipe(batch_id):
    """Return encrypted recipe - only for authorized users."""
    user = get_current_user()  # From LDAP/AD
    
    # Check user department against batch
    if not user_can_access_batch(user, batch_id):
        audit_log.warning(f"Unauthorized access attempt: {user} -> batch {batch_id}")
        abort(403)
    
    # Get encrypted recipe
    batch = db.session.query(ProductionBatch).get(batch_id)
    
    # Decrypt only if authorized (triggers encryption key usage)
    decrypted_recipe = decrypt_with_audit(batch.recipe_encrypted, user)
    
    return jsonify({'recipe': decrypted_recipe})

@app.route('/api/v1/batch-records', methods=['GET', 'POST'])
@audit_access('batch_record_access')
def batch_records():
    """Batch records with data classification enforcement."""
    if request.method == 'POST':
        user = get_current_user()
        
        # Only production supervisors can create
        if user.role != 'supervisor':
            abort(403)
        
        data = request.get_json()
        
        # Hash for integrity check
        data_hash = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
        
        batch = ProductionBatch(
            batch_number=data['batch_number'],
            recipe_data=encrypt_data(data['recipe']),
            operator_id=user.username,
            created_by=user.username,
            data_hash=data_hash
        )
        
        db.session.add(batch)
        db.session.commit()
        
        return jsonify({'status': 'created', 'id': batch.id}), 201
```

### 4. Network Layer - TLS & Encryption

```yaml
# /factory-lab/configs/nginx/nginx.conf additions

# HTTPS configuration for sensitive endpoints
server {
    listen 443 ssl http2;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Certificates
    ssl_certificate /etc/nginx/ssl/factory-api.crt;
    ssl_certificate_key /etc/nginx/ssl/factory-api.key;
    
    # Client certificate validation (mutual TLS)
    ssl_client_certificate /etc/nginx/ssl/ca-cert.pem;
    ssl_verify_client optional;
    ssl_verify_depth 2;
    
    location /api/v1/sensitive/ {
        # Require client certificate
        if ($ssl_client_verify != SUCCESS) {
            return 403 "Client certificate required";
        }
        
        # Add security headers
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;
        
        # Rate limiting for API
        limit_req zone=api burst=10 nodelay;
        
        proxy_pass http://mes-app:8000;
        
        # Log all access
        access_log /var/log/nginx/api-sensitive.log combined buffer=32k flush=5s;
    }
}
```

### 5. Data Transmission - Secure Transfer Methods

```bash
#!/bin/bash
# /factory-lab/scripts/secure-data-transfer.sh

# SFTP - Secure file transfer for engineering files
sftp_transfer() {
    local user=$1
    local source=$2
    local dest=$3
    
    # Create SFTP script
    cat > /tmp/sftp-script.txt <<EOF
put $source $dest
EOF
    
    # Transfer with logging
    sftp -v \
        -i /home/$user/.ssh/id_rsa \
        -o StrictHostKeyChecking=accept-new \
        $user@factory-sftp:$dest < /tmp/sftp-script.txt
    
    # Log transfer
    echo "$(date): $user transferred $source to $dest" >> /var/log/data-transfers.log
    
    # Verify integrity
    remote_hash=$(ssh $user@factory-sftp "sha256sum $dest")
    local_hash=$(sha256sum $source)
    
    if [ "${remote_hash% *}" != "${local_hash% *}" ]; then
        echo "ERROR: Hash mismatch for $dest"
        return 1
    fi
}

# HTTPS Upload - For MES batch records
https_upload_sensitive() {
    local user=$1
    local file=$2
    local batch_id=$3
    
    # Get authentication token
    token=$(curl -s -X POST https://factory-api.local/auth/login \
        -d "username=$user&password=$FACTORY_PASSWORD" | jq -r '.token')
    
    # Upload with encryption
    curl -s -X POST https://factory-api.local/api/v1/batch-records \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        --cacert /etc/ssl/certs/factory-ca.crt \
        --cert /home/$user/.ssl/client-cert.pem \
        --key /home/$user/.ssl/client-key.pem \
        -d @$file
}

# Encrypted backup transfer
backup_transfer() {
    local backup_file=$1
    local recipient=$2
    
    # Encrypt with GPG
    gpg --encrypt --recipient $recipient $backup_file
    
    # Transfer to secure location
    rsync -avz --partial \
        $backup_file.gpg \
        backup-server:/secure/backups/
    
    # Log backup
    echo "Backup transferred: $backup_file (GPG encrypted)" >> /var/log/backups.log
}

# DLP - Data Loss Prevention scanner
scan_for_sensitive_data() {
    local directory=$1
    
    # Find files with sensitive patterns
    grep -r "CONFIDENTIAL\|SECRET\|PASSWORD\|API_KEY" $directory 2>/dev/null | \
    while read -r line; do
        echo "ALERT: Sensitive data found in: $line" >> /var/log/dlp-alerts.log
        # Trigger escalation if needed
    done
}

# Example usages
# sftp_transfer "john.smith" "/tmp/ladder-logic.ld" "plc-configs/"
# https_upload_sensitive "sarah.johnson" "/tmp/batch-recipe.json" "BATCH-2024-001"
# backup_transfer "/backups/factory-db-2024-07-26.dump" "backup-admin@factory.local"
# scan_for_sensitive_data "/srv/shares/Production"
```

### 6. Compliance & Audit Trail

```sql
-- /factory-lab/configs/postgres/audit-trail.sql

-- Master audit table
CREATE TABLE security_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50),  -- 'data_access', 'modification', 'deletion', 'export'
    severity VARCHAR(10),     -- 'info', 'warning', 'critical'
    user_id VARCHAR(100),
    object_type VARCHAR(50),  -- 'batch', 'equipment', 'employee_record'
    object_id INTEGER,
    old_value JSONB,
    new_value JSONB,
    classification_level VARCHAR(20),
    timestamp TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    status VARCHAR(20),       -- 'allowed', 'denied', 'failed'
    encryption_used BOOLEAN,
    mfa_verified BOOLEAN,
    notes TEXT
);

-- Index for fast queries
CREATE INDEX idx_security_events_user_time ON security_events(user_id, timestamp DESC);
CREATE INDEX idx_security_events_type ON security_events(event_type, severity);

-- Compliance view (immutable audit log)
CREATE MATERIALIZED VIEW compliance_audit_log AS
SELECT 
    event_type,
    COUNT(*) as count,
    MIN(timestamp) as first_event,
    MAX(timestamp) as last_event,
    ARRAY_AGG(DISTINCT user_id) as users
FROM security_events
WHERE severity IN ('warning', 'critical')
GROUP BY event_type
ORDER BY last_event DESC;

-- Enforce immutability (no deletes)
CREATE RULE no_delete_security_events AS
ON DELETE TO security_events
DO INSTEAD NOTHING;

-- Generate compliance reports
CREATE OR REPLACE FUNCTION generate_compliance_report(
    start_date DATE,
    end_date DATE
)
RETURNS TABLE (
    report_date DATE,
    total_access_events BIGINT,
    unauthorized_attempts BIGINT,
    data_modified COUNT,
    users_audited BIGINT,
    critical_events BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        CURRENT_DATE,
        COUNT(*),
        COUNT(*) FILTER (WHERE status = 'denied'),
        COUNT(*) FILTER (WHERE event_type = 'modification'),
        COUNT(DISTINCT user_id),
        COUNT(*) FILTER (WHERE severity = 'critical')
    FROM security_events
    WHERE timestamp::DATE BETWEEN start_date AND end_date;
END;
$$ LANGUAGE plpgsql;
```

---

## Sensitive Data Scenarios

### Scenario 1: Engineering downloads PLC program

```
1. Engineer logs in with AD credentials
   → MFA via email or phone
   
2. Request PLC file from SCADA share
   → System checks AD group membership
   → Verifies department (Engineering only)
   
3. File transferred via SFTP (TLS 1.3)
   → File is signed with engineer's certificate
   → Timestamp and hash recorded
   
4. Engineer modifies and uploads back
   → System logs: who, what, when
   → Version control tracks all changes
   → Change requires manager approval
   
5. Audit trail recorded in Elasticsearch
   → Accessible only to compliance officer
   → Retained for 7 years (regulatory)
```

### Scenario 2: Production supervisor creates batch record

```
1. Supervisor accesses MES web portal
   → HTTPS + client certificate
   → LDAP authentication against AD
   
2. Fills batch record form (contains recipe - LEVEL 4)
   → Data encrypted in transit (TLS 1.3)
   → Data encrypted at rest (pgcrypto AES-256)
   
3. Submit button triggers:
   → Data hash calculation
   → User audit log entry
   → Encryption with factory key
   → Database insert with RLS enforcement
   
4. System emails approval to QA manager
   → QA manager reviews via HTTPS
   → Grants approval (MFA validated)
   → Batch record visible to production line
```

### Scenario 3: Backup and recovery of sensitive data

```
1. Hourly backup process triggers
   → Connects to Postgres via SSL
   → Exports batch records and recipes
   → Encrypts backup with GPG key
   
2. Backup stored in:
   → Local: /data/backups/ (encrypted filesystem)
   → Remote: backup-server (SFTP + GPG)
   → Cloud: S3 (server-side encryption)
   
3. Backup log entries:
   → Who initiated backup (system account)
   → What was backed up (size, hash)
   → Where stored (locations)
   → Encryption key used (reference only, never stored)
   
4. Recovery process:
   → Manager requests restore
   → Requires dual approval (manager + IT)
   → Decryption with HSM (Hardware Security Module)
   → Recovery to isolated database first
   → Verification and comparison before production restore
```

---

## Compliance & Regulatory

### Data Retention Policy

```
LEVEL 4 (CRITICAL):
├─ Encryption keys: 10+ years (offline secure storage)
├─ Audit logs: 7+ years (immutable)
├─ Safety interlocks: Forever (regulatory requirement)
└─ Incident reports: 7 years

LEVEL 3 (CONFIDENTIAL):
├─ Batch records: 7 years (FDA compliance)
├─ Equipment calibration: 5 years (ISO 9001)
└─ Access logs: 2 years

LEVEL 2 (INTERNAL):
├─ Work instructions: 3 years (or until superseded)
└─ Training records: Duration of employment

LEVEL 1 (PUBLIC):
└─ Automatic deletion: 1 year
```

### User Access Rights Management

```yaml
Access Control Tiers:

Tier 1 - No Access (Default):
  - Cannot see sensitive compartments
  - Cannot modify any data

Tier 2 - Read-Only:
  - View production metrics
  - View equipment status
  - Cannot export data

Tier 3 - Read/Write:
  - Modify batch records (own department)
  - Export aggregated data
  - Cannot delete records

Tier 4 - Administrative:
  - Full access (all departments)
  - Delete authority (with approval)
  - Encryption key management

Tier 5 - Compliance/Audit:
  - Read-only all data
  - Access audit logs
  - Generate compliance reports
  - Cannot modify any production data
```

---

## Testing Sensitive Data Handling

```bash
#!/bin/bash
# /factory-lab/scripts/test-sensitive-data.sh

# Test 1: Verify encryption in transit
echo "Testing TLS encryption..."
openssl s_client -connect factory-api.local:443 \
  -cert /home/test-user/.ssl/client-cert.pem \
  -key /home/test-user/.ssl/client-key.pem \
  -CAfile /etc/ssl/certs/factory-ca.crt

# Test 2: Verify RLS policies
echo "Testing row-level security..."
psql -h postgres-main -U test_user -d manufacturing \
  -c "SELECT * FROM production_batches_sensitive WHERE id = 1;"
# Should return no rows if user's department doesn't match

# Test 3: Verify audit logging
echo "Testing audit trail..."
curl -s https://factory-api.local/api/v1/sensitive/batch/1 \
  -H "Authorization: Bearer $TOKEN"
# Check /var/log/factory-lab/api-audit.log for entry

# Test 4: Verify file access logging
echo "Testing SMB access logging..."
smbclient \\\\\\factory-dc01\\Production -U john.smith
# Check /var/log/samba/audit.log for access records

# Test 5: Test data export restrictions
echo "Testing export restrictions..."
curl -X POST https://factory-api.local/api/v1/export/batch-records \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-01", "end_date": "2024-12-31"}'
# Should fail if user doesn't have export permission

echo "All tests completed. Check logs for compliance."
```

---

## Summary: Data Security by Layer

| Layer | Protection | Mechanism |
|-------|-----------|-----------|
| **Network** | Encryption in transit | TLS 1.3 + mTLS |
| **Authentication** | Identity verification | LDAP + MFA |
| **Authorization** | Access control | AD groups + RBAC |
| **Data at rest** | Storage encryption | AES-256 (pgcrypto) |
| **Database** | Row-level security | PostgreSQL RLS policies |
| **Audit** | Immutable logging | Append-only security_events |
| **Compliance** | Retention & deletion | Automated policies + retention |
| **Recovery** | Disaster recovery | Encrypted backups + HSM |

This creates a **production-grade** sensitive data handling system suitable for regulated industries (FDA, ISO, etc.).
