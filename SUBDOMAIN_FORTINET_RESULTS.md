# Subdomain Enumeration + Fortinet Detection

**Scan Date:** 2026-07-24

## Summary

| Metric | Count |
|--------|-------|
| Top Israeli domains scanned | 20 |
| Live subdomains found | 65 |
| **Fortinet detected** | **0** |

## Live Subdomains by Category

### Infrastructure & Security
- `vpn.globes.co.il`, `vpn.haaretz.co.il`, `vpn.mako.co.il`, `vpn.nrg.co.il`
- `firewall.*`, `waf.*` (none found)

### Development & CI/CD
- `gitlab.ynet.co.il` ⚠️ (code repository exposed)
- `jenkins.ynet.co.il` ⚠️ (CI/CD pipeline exposed)
- `dev.bankhapoalim.co.il`, `dev.calcalist.co.il`, `dev.mako.co.il`
- `staging.nrg.co.il`
- `test.mako.co.il`, `test.news1.co.il`, `test.wikipedia.co.il`, `test.ynet.co.il`

### Authentication & Services
- `passport.ynet.co.il` (auth service)
- `auth.calcalist.co.il`, `auth.israelpost.co.il`
- `service.bankleumi.co.il`, `service.haaretz.co.il`

### Internal Services
- `api.israelhayom.co.il`, `api.one.co.il`, `api.tase.co.il`
- `cache.bankleumi.co.il`, `cache.walla.co.il`
- `cdn.glz.co.il`
- `chat.walla.co.il`, `chat.ynet.co.il`
- `dashboard.ynet.co.il`
- `mail.*` (10 instances across different domains)
- `app.israelpost.co.il`, `app.nrg.co.il`
- `prod.walla.co.il`
- `smtp.walla.co.il`, `smtp.ynet.co.il`

### Web Properties
- All major Israeli news/business sites have `www.` subdomains

## Key Findings

1. **No Fortinet Detected** - None of the 65 subdomains showed Fortinet v7.6 or v8 indicators
2. **Development Infrastructure Exposed** - gitlab.ynet.co.il and jenkins.ynet.co.il are publicly resolvable
3. **Multi-tier Architecture** - Israeli major websites have distinct subdomains for dev/staging/prod
4. **Email Infrastructure** - Mail servers on separate subdomains across multiple orgs
5. **VPN Gateways** - Multiple VPN endpoints found for news/media organizations

## Conclusion

- **Answer to "Check Fortinet on all subdomains":** Zero (0/65) subdomains use Fortinet
- Israeli major websites use alternative security solutions or don't expose Fortinet headers publicly
