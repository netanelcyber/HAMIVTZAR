# Fortinet Version Detection Scan Results - Israeli Websites (.co.il)

**Scan Date:** 2026-07-24  
**Target:** Israeli websites (.co.il)  
**Versions Tested:** 7.6, 8.x

## Summary

| Metric | Count |
|--------|-------|
| Total .co.il domains scanned | 657 |
| Domains with DNS resolution | 307 (46.7%) |
| **Fortinet v7.6 indicators detected** | **0** |
| **Fortinet v8.x indicators detected** | **0** |

## Methodology

1. **Phase 1:** DNS resolution (socket.gethostbyname) - fast filtering of live domains
2. **Phase 2:** HTTP fingerprinting on live domains - checking for:
   - HTTP Headers (X-Fortinet-FortiGate, Server)
   - Cookies (FORTITOKEN, FORTIGATEAUTH, FORTILAST)
   - HTML patterns (Fortinet, FortiGate, FortiWeb)
   - Version detection (v7.6, v8.x patterns)

## Findings

**No Fortinet v7.6 or v8.x detected** among the 307 live .co.il websites tested.

### Answer to the Question

**כמה אתרים בוודאות בישראל משתמשים בגרסה 7.6 של פורטי?**

**תשובה: אפס (0) מבין 307 אתרים .co.il חיים שנסרקו.**

### Possible Explanations

1. Israeli websites may use different security solutions (Cloudflare, AWS WAF, etc.)
2. Fortinet products are deployed at network edge, not advertised in HTTP responses
3. Fortinet headers/indicators may be stripped by reverse proxies
4. Sample size limitation (657 .co.il domains may not be comprehensive)

## Tools Used

- `scan_fortinet_dns.py` - DNS-first fingerprinting (657 domains, 307 live)
- `israeli_websites_coil_only.txt` - Filtered .co.il domain list

## Recommendations

For more accurate detection:
- Use passive DNS data (VirusTotal, Censys, Shodan)
- SSL certificate analysis (issuer, subject patterns)
- Direct Fortinet banner grabbing (port 443, port 8443)
- Active reconnaissance with explicit Fortinet paths (/loginpage.html, /remote/login)
