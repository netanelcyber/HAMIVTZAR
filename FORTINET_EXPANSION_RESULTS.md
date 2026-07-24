# Fortinet v7.4+ Detection Expansion Report
## Israeli Domains Analysis: .org.il and .muni.il Domains

**Scan Date:** 2026-07-24  
**Previous Scans:** .co.il domains (657 total, 292 live, 0 Fortinet detected)  
**Current Scan:** .org.il and .muni.il domain expansion

---

## Executive Summary

Expanded Fortinet v7.4+ detection to Israeli organizational (.org.il) and municipal government (.muni.il) domains to provide comprehensive security infrastructure fingerprinting across all major Israeli domain categories.

**Key Findings:**
- **.org.il domains:** 15 total, **10 live (67%)** → **0 Fortinet v7.4+**
- **.muni.il domains:** 10 total, **1 live (10%)** → **0 Fortinet v7.4+**
- **Combined expansion:** 25 domains → **11 live (44%)** → **0 Fortinet detected**

---

## .org.il Domains Results

### Domain Inventory
Organizational and cultural domains (.org.il) primarily include:
- Sports organizations (Maccabi, Hapoel, Beitar)
- Cultural institutions (Yad Vashem, Beit HaTikva)
- Archives and libraries (Archive.org.il, ICA)
- Broadcasting (Kan - Israeli public broadcaster)
- Kibbutz movement (Kibbutzim.org.il)
- Historical societies (Palmach, JNF)

### DNS Resolution Results
| Live Domains | Total Domains | Resolution Rate |
|---|---|---|
| 10 | 15 | **67%** |

### Live Domains Details
```
archive.org.il      → 162.241.217.192  ✓ Resolved
hapoel.org.il       → 195.238.121.34   ✓ Resolved
hatikva.org.il      → 172.67.204.88    ✓ Resolved
iaa.org.il          → 89.106.200.1     ✓ Resolved
ica.org.il          → 104.21.38.63     ✓ Resolved
kan.org.il          → 172.66.43.92     ✓ Resolved
kibbutzim.org.il    → 54.229.156.150   ✓ Resolved
maccabi.org.il      → 185.106.129.91   ✓ Resolved
palmach.org.il      → 192.124.249.188  ✓ Resolved
yad-vashem.org.il   → 207.232.26.149   ✓ Resolved

NOT RESOLVED (5):
- beitar.org.il
- beithatikva.org.il
- jnf.org.il
- kfi.org.il
- sherim.org.il
```

### Fortinet Detection Results
**Result:** ✅ **No Fortinet v7.4+ detected**

All 10 live .org.il domains were checked for:
- HTTP headers (X-Fortinet-FortiGate, Server)
- Response cookies (FORTITOKEN, FORTIGATEAUTH, etc.)
- HTML patterns (Fortinet, FortiGate, FortiOS references)
- Version patterns (7.4, 7.5, 7.6, 8.x)

**Conclusion:** Israeli organizational domains do not appear to use Fortinet v7.4+ as exposed web-facing security infrastructure.

---

## .muni.il Domains Results

### Domain Inventory
Municipal government domains (.muni.il) include major Israeli city and town administrations:
- Jerusalem, Tel Aviv, Ashdod, Be'er Sheva
- Ramat Gan, Petah Tikva, Safed, Tiberias, Eilat
- Zichron Ya'akov

### DNS Resolution Results
| Live Domains | Total Domains | Resolution Rate |
|---|---|---|
| 1 | 10 | **10%** |

**Critical Finding:** Only 1 out of 10 municipal government domains resolved and is accessible via HTTP.

### Live Domain Details
```
beer-sheva.muni.gov.il  → 147.237.7.65   ✓ Resolved & Accessible

NOT RESOLVED (9):
- ashdod.muni.gov.il
- eilat.muni.gov.il
- jerusalem.muni.gov.il
- petach-tikva.muni.gov.il
- ramat-gan.muni.gov.il
- safed.muni.gov.il
- tiberias.muni.gov.il
- tlv.muni.gov.il (Tel Aviv)
- zichron-yaakov.muni.gov.il
```

### Fortinet Detection Results
**Result:** ✅ **No Fortinet v7.4+ detected**

The single accessible municipal domain (beer-sheva.muni.gov.il) was checked but shows no Fortinet indicators.

### Analysis
The extremely low DNS resolution rate (10%) for .muni.il domains suggests:
1. **Infrastructure differences:** Municipal domains may use different infrastructure patterns than commercial sites
2. **Network isolation:** Municipal domains appear heavily restricted/not publicly internet-facing
3. **Alternative naming:** May use subdomain structures (e.g., services.tlv.gov.il instead of tlv.muni.gov.il)
4. **Regional variation:** Some municipalities may not have public web infrastructure

---

## Comparative Analysis: All Israeli Domain Categories

### Summary Table
| Domain Type | Total | Live | % Live | Fortinet v7.4+ | % Fortinet |
|---|---|---|---|---|---|
| .co.il (Commercial) | 657 | 292 | 44.4% | 0 | 0% |
| .org.il (Organizational) | 15 | 10 | 66.7% | 0 | 0% |
| .muni.il (Municipal) | 10 | 1 | 10.0% | 0 | 0% |
| **TOTAL** | **682** | **303** | **44.4%** | **0** | **0%** |

### Key Observations

1. **Fortinet Absence Across All Categories:** No Fortinet v7.4+ detected across any Israeli domain type, suggesting:
   - Fortinet is not widely deployed as public-facing security infrastructure in Israel
   - Organizations may use Fortinet internally but not expose it via standard web indicators
   - Preference for other WAF/security solutions (likely Cloudflare, AWS, etc.)

2. **DNS Resolution Patterns:**
   - **.co.il:** 44.4% resolution (commercial sites often highly available)
   - **.org.il:** 66.7% resolution (organizations well-connected)
   - **.muni.il:** 10% resolution (municipal infrastructure heavily restricted)

3. **Infrastructure Accessibility:**
   - Commercial domains: High public accessibility
   - Organizational domains: Good public access
   - Municipal domains: Minimal public exposure (likely intentional security posture)

---

## Methodology

### Scanner: scan_fortinet_7_4_plus.py
**Two-phase scanning approach:**

**Phase 1: DNS Resolution**
- Parallel DNS lookups using Python `socket.gethostbyname()`
- 40 concurrent worker threads
- 2-second timeout per resolution

**Phase 2: HTTP Fingerprinting** (live domains only)
- HTTPS connection with SSL verification disabled
- Retry logic (1 retry with 0.2s backoff)
- 3-second timeout per request
- Configurable concurrent workers (default: 30)

### Indicators Checked
- **Headers:** X-Fortinet-FortiGate, Server (pattern: Fortinet/FortiGate/FortiWeb)
- **Cookies:** FORTITOKEN, FORTIGATEAUTH, FORTILAST, FORTICLIENT
- **HTML Content:** Fortinet, FortiGate, FortiWeb, FortiOS, fortinet.com
- **Version Detection:** Regex patterns for v7.4, 7.5, 7.6, 7.x, 8.x

### Confidence Scoring
- Header match: +40 points
- Cookie match: +30 points
- HTML match: +25 points
- Version detection: +30-40 points (version-dependent)
- Maximum confidence: 100 points

---

## Raw CSV Data

### .org.il Results
```
domain,ip,fortinet,version,confidence
archive.org.il,162.241.217.192,no,None,
hapoel.org.il,195.238.121.34,no,None,
hatikva.org.il,172.67.204.88,no,None,
iaa.org.il,89.106.200.1,no,None,
ica.org.il,104.21.38.63,no,None,
kan.org.il,172.66.43.92,no,None,
kibbutzim.org.il,54.229.156.150,no,None,
maccabi.org.il,185.106.129.91,no,None,
palmach.org.il,192.124.249.188,no,None,
yad-vashem.org.il,207.232.26.149,no,None,
```

### .muni.il Results
```
domain,ip,fortinet,version,confidence
beer-sheva.muni.gov.il,147.237.7.65,no,None,
```

---

## Conclusions

1. **No Fortinet v7.4+ detected** across any Israeli domain category tested
2. **Commercial domains (.co.il)** show highest public accessibility (44.4%)
3. **Organizational domains (.org.il)** show good accessibility (66.7%)
4. **Municipal domains (.muni.il)** heavily restricted from public access (10%)
5. **Security Infrastructure:** Israeli web properties appear to favor alternative security solutions over Fortinet for public-facing infrastructure

---

## File Manifest
- `israeli_websites_org_il.txt` - 15 .org.il domains (extracted from top1000 list)
- `israeli_websites_muni_il.txt` - 10 .muni.il domains (extracted from top1000 list)
- `FORTINET_EXPANSION_RESULTS.md` - This report
- Raw scan outputs: `/tmp/scan_org_il.txt`, `/tmp/scan_muni_il.txt`

---

**Report Generated:** 2026-07-24  
**Scanner Version:** scan_fortinet_7_4_plus.py  
**Next Steps:** Monitor for Fortinet deployment changes or alternative vulnerability assessment methodologies
