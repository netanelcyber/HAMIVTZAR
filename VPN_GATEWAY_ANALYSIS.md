# VPN Gateway Analysis - Israeli News Organizations

**Analysis Date:** 2026-07-24

## Summary

| Gateway | IP | Status | Ports | Fortinet |
|---------|----|----|-------|----------|
| vpn.globes.co.il | 80.70.130.5 | LIVE | 80, 443 | ❌ No |
| vpn.haaretz.co.il | 192.118.72.125 | LIVE | 80, 443 | ❌ No |
| vpn.mako.co.il | 91.240.234.20 | LIVE | 80, 443 | ❌ No |
| vpn.nrg.co.il | 192.118.0.2 | LIVE | 80, 443 | ❌ No |

## Detailed Findings

### All VPN Gateways Return Consistent Pattern:

```
HTTP/1.1 403 Forbidden
x-deny-reason: host_not_allowed
content-type: text/plain
```

### Port Analysis
- **HTTP (80):** OPEN - 403 Forbidden with `x-deny-reason` header
- **HTTPS (443):** OPEN - SSL/TLS active
- **SSH (22):** CLOSED
- **OpenVPN (1194):** CLOSED
- **WireGuard (51820):** CLOSED
- **IPSec (500):** CLOSED

### Security Observations

1. **WAF/Proxy Protection** - The `x-deny-reason: host_not_allowed` header suggests a Web Application Firewall (WAF) or reverse proxy
2. **Access Control** - All requests are blocked unless proper credentials/headers provided
3. **No Fortinet Headers** - Unlike exposed infrastructure, these gateways don't advertise Fortinet
4. **Uniform Response** - All 4 gateways follow identical security posture

### Fortinet Path Testing

Tested common Fortinet paths:
- `/loginpage.html` → HTTP 403
- `/remote/login` → HTTP 403  
- `/admin` → HTTP 403
- `/api` → HTTP 403
- `/admin/login` → HTTP 403

**Result:** No Fortinet-specific paths accessible

## Possible Infrastructure

Given the pattern, these VPN gateways likely use:
- **FortiClient VPN** (Fortinet's own VPN client)
- **Custom WAF** (AWS WAF, Cloudflare, etc.)
- **Reverse Proxy** (nginx, HAProxy)
- **Hardware Load Balancer**

## Conclusion

**Fortinet v7.6/v8 Status: NOT CONFIRMED**

While the infrastructure could be Fortinet-based, the gateways:
- Don't expose identifying headers
- Have consistent WAF-like behavior
- Block all reconnaissance attempts
- Implement proper access control

**Security Grade: A+** - Israeli news organizations protect their VPN infrastructure properly.

## Infrastructure Architecture

```
Internet
   ↓
[WAF/Proxy Layer] ← x-deny-reason: host_not_allowed
   ↓
[VPN Gateway] ← vpn.*.co.il
   ↓
[Internal Network]
```
