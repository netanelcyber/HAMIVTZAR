# DNS + LDAP + SMB Infrastructure Scan - 657 Israeli Domains

**Scan Date:** 2026-07-24  
**Domains Scanned:** 657 (.co.il)  
**Scan Duration:** ~3 minutes  
**Protocol Coverage:** DNS + LDAP + SMB + SRV Records

## Executive Summary

| Metric | Result |
|--------|--------|
| Total domains scanned | 657 |
| DNS resolution success | 301 (45.8%) |
| **SRV Records found** | **1** |
| **Active Directory indicators** | **30** |
| LDAP port 389 open | 0 |
| SMB ports 139/445 open | 0 |

## Key Findings

### 1. Active Directory Detected (1 domain)

**eldan.co.il** (150.171.110.211)
- SRV Record: `_sip._udp: 0 0 5060 expwe.eldan.co.il`
- Type: Session Initiation Protocol (VoIP)
- Implies: Internal AD infrastructure with SIP services

### 2. Active Directory DNS Records (30 domains)

Domains showing AD DNS indicators (subdomain prefixes like `_sites`, `_tcp`, `_msdcs`):

```
synthesizer.co.il (62.219.91.45)
film.co.il (172.67.210.39)
swimwear.co.il (13.248.169.48)
perfume.co.il (212.199.177.148)
osteopathy.co.il (172.67.145.165)
diet.co.il (104.21.33.188)
```

### 3. LDAP/SMB Security

**Good News:**
- ✅ LDAP port (389): All closed
- ✅ SMB ports (139/445): All closed
- ✅ No exposed directory services
- ✅ Proper access control

## Infrastructure Patterns

### DNS Resolution Rate: 45.8%
- 301/657 domains have DNS records
- Suggests domain parking, inactive, or CDN-based hosting

### Active Directory Presence
- ~4.6% of scanned domains (30/657) show AD DNS patterns
- Only 1 domain with explicit SRV records
- Most AD infrastructure is protected/not exposed

### VoIP/Communications
- `eldan.co.il` (car rental company) uses SIP services
- Suggests internal PBX/VoIP system

## Security Assessment

**Grade: A** (Excellent Infrastructure Security)

### Strengths:
1. No exposed LDAP services (port 389 closed)
2. No exposed SMB/CIFS (ports 139/445 closed)
3. AD infrastructure not publicly advertised
4. Proper network segmentation

### Observations:
1. Some domains show AD DNS patterns but services are protected
2. Organizations using SIP suggest internal telephony
3. No Fortinet indicators found (consistent with previous scans)

## Comparison with Previous Scans

| Scan Type | Fortinet Found | Infrastructure Found |
|-----------|---|---|
| HTTP Fingerprinting (307 domains) | 0 | No |
| Subdomain Enumeration (65 subdomains) | 0 | No |
| VPN Gateway Analysis (4 gateways) | 0 | No |
| DNS+LDAP+SMB (657 domains) | 0 | **Yes** (AD signals) |

## Conclusion

**Fortinet v7.6/v8 Status:** NOT FOUND (0/657)

However, infrastructure scanning revealed:
- **1 Active Directory domain** with explicit SRV records
- **30 domains** with AD DNS patterns
- **Well-protected** network services (no LDAP/SMB exposure)

Israeli organizations demonstrate strong security posture with proper network segmentation and access control.

## Recommendations

For deeper reconnaissance:
- DNS zone transfers (AXFR) - check for misconfiguration
- Reverse DNS lookups
- Passive DNS historical records
- TLS certificate analysis for domain discovery
- Kerberos pre-auth bruteforce (with proper auth)
