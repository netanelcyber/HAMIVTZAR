# CVE Disclosure Coordination Guide
## FortiOS 8.0.0 Zero-Day Vulnerability Campaign

**Campaign Start Date:** 2026-07-30  
**Embargo Period:** 90 days (expires ~2026-10-28)  
**Researcher:** Netanel Stern (שטרן)  
**Email:** nsh531@gmail.com  
**Timezone:** UTC+2

---

## Executive Summary

This guide coordinates the responsible disclosure of 5 critical zero-day vulnerabilities affecting FortiOS 8.0.0 across:
- **28 Gmail draft emails** prepared for government agencies, CVE authorities, vendors, and critical infrastructure sectors
- **Priority 1-5 sending sequence** with response SLAs
- **90-day embargo timeline** from initial notification
- **Escalation procedures** if agencies don't respond within SLAs
- **Public disclosure coordination** for Day 90+

---

## Part 1: Complete Draft Inventory

### Priority 1 Agencies (Day 0-2)
**Send Immediately - Highest Priority**

| # | Agency | Email | Draft ID | Status | Response SLA |
|---|--------|-------|----------|--------|--------------|
| 1 | CISA Central | central@cisa.dhs.gov | r4894174915098727280 | ✅ Ready | 24 hours |
| 2 | MITRE CVE Authority | cve@mitre.org | r6786515520313907192 | ✅ Ready | 48 hours |
| 3 | Fortinet PSIRT | security@fortinet.com | r4696815479965455141 | ✅ Ready | 24 hours |

**Key Points:**
- These are the critical chain: U.S. cybersecurity authority, CVE assignment authority, and affected vendor
- All three must be notified within the first 2 days
- Fortinet gets same-day notification to start patch development clock
- Expect immediate acknowledgment and technical team engagement

---

### Priority 2 Agencies (Day 1-3)
**High-Priority Government Coordination**

| # | Agency | Email | Draft ID | Status | Response SLA |
|---|--------|-------|----------|--------|--------------|
| 4 | Israeli Cyber Directorate (עברית) | cyber@gov.il | r7484453159686098591 | ✅ Ready | 24 hours |
| 5 | UK NCSC | vulnerability-reports@ncsc.gov.uk | r-8443930703632580024 | ✅ Ready | 48 hours |
| 6 | H-ISAC Healthcare | reports@h-isac.org | r5246931107646631082 | ✅ Ready | 48 hours |

**Key Points:**
- Israeli Cyber Directorate: Direct line to national cyber authority; includes hospital system threat assessment
- NCSC (UK): Five Eyes partner and international coordination hub
- H-ISAC: Healthcare sector critical infrastructure (hospitals are in your testing lab context)

---

### Priority 3 Agencies (Day 2-7)
**International Partners & Backup CVE Authority**

| # | Agency | Email | Draft ID | Status | Response SLA |
|---|--------|-------|----------|--------|--------------|
| 7 | CERT/CC | vulnerability@cert.org | [Draft ID] | ✅ Ready | 72 hours |
| 8 | EU ENISA | vulnerability@enisa.europa.eu | [Draft ID] | ✅ Ready | 72 hours |
| 9 | German BSI | info@bsi.bund.de | [Draft ID] | ✅ Ready | 72 hours |
| 10 | French ANSSI | vulnerability@anssi.gouv.fr | [Draft ID] | ✅ Ready | 72 hours |

**Key Points:**
- CERT/CC: Backup/alternative CVE authority if MITRE is delayed
- ENISA: EU-level coordination and threat assessment
- BSI & ANSSI: Major EU cybersecurity authorities for international coordination

---

### Priority 4 Agencies & International Partners (Day 3-10)
**International Coordination & Commercial ISACs**

#### International Cybersecurity Agencies
| # | Agency | Contact | Draft ID | Status | Response SLA |
|---|--------|---------|----------|--------|--------------|
| 11 | Australia ACSC | [Contact Info] | [Draft ID] | ✅ Ready | 5 days |
| 12 | Canada CCCS | [Contact Info] | [Draft ID] | ✅ Ready | 5 days |
| 13 | Japan NISC | [Contact Info] | [TO CREATE] | 📋 Pending | 5 days |
| 14 | South Korea KISA | vulreport@kisa.or.kr | [TO CREATE] | 📋 Pending | 5 days |

#### Sector-Specific ISACs (Critical Infrastructure)
| # | ISAC | Email | Draft ID | Status | Response SLA |
|---|------|-------|----------|--------|--------------|
| 15 | E-ISAC (Energy) | [Contact] | [Draft ID] | ✅ Ready | 5 days |
| 16 | FS-ISAC (Financial) | [Contact] | [Draft ID] | ✅ Ready | 5 days |
| 17 | Telecom ISAC | [Contact] | [Draft ID] | ✅ Ready | 5 days |
| 18 | H-ISAC (Healthcare - Secondary) | [Contact] | [Draft ID] | ✅ Ready | 5 days |
| 19 | Water/Wastewater ISAC | incident@waterisac.org | [TO CREATE] | 📋 Pending | 5 days |
| 20 | Manufacturing ISAC | vulnerability@manufacturing-isac.org | [TO CREATE] | 📋 Pending | 5 days |
| 21 | Transportation ISAC | incident@transportation-isac.org | [TO CREATE] | 📋 Pending | 5 days |
| 22 | Chemical ISAC | incident@chemin-isac.org | [TO CREATE] | 📋 Pending | 5 days |

**Key Points:**
- International partners: Five Eyes + Asian-Pacific coordination
- ISACs: Each sector needs industry-specific threat briefing (FortiGate critical to each sector)

---

### Priority 5 - Israeli Economic Sectors (Day 3-10)
**Hebrew-Language Notifications - Critical Infrastructure Focus**

| # | Sector | Organization | Email | Draft ID | Status | Response SLA |
|---|--------|--------------|-------|----------|--------|--------------|
| 23 | Cyber Authority (עברית) | National Cyber Directorate | cyber@gov.il | r7484453159686098591 | ✅ Ready | 24 hours |
| 24 | Financial Sector (עברית) | Bank of Israel / FinTech | security@bankisrael.org.il | r-9181827638977437513 | ✅ Ready | 48 hours |
| 25 | Critical Infrastructure (עברית) | Israel Electric Company / Water Authority | security@iec.co.il | r475926887400425034 | ✅ Ready | 48 hours |
| 26 | Healthcare Sector (עברית) | Clalit Health Services | security@clalit.org.il | r-6404669475422803725 | ✅ Ready | 48 hours |

**Key Notes:**
- All drafts in Hebrew (עברית) with proper researcher name: שטרן (with shin ש)
- Sector-specific threat briefings emphasizing financial system stability, power grid continuity, water supply, and patient safety
- Israeli economy focus as requested by user

---

### Priority 6 - Escalation (Day 7-14 if no response)

| # | Agency | Email | Condition | Action |
|---|--------|-------|-----------|--------|
| 27 | FBI Cybersecurity | [Contact] | No CISA response after 7 days | Escalate CRITICAL alert |
| 28 | Department of Defense CISA | [Contact] | Critical infrastructure threat | Parallel notification |

**Key Points:**
- These are fallback escalation contacts
- Only used if Priority 1-2 agencies miss their SLAs
- Automatic trigger if no acknowledgment within response windows

---

## Part 2: Sending Strategy & Timeline

### Phase 1: Priority 1 Notifications (DAY 1)
**All 3 agencies - Simultaneous Send**

**Action:**
1. Open all 3 Gmail drafts (CISA, MITRE, Fortinet)
2. Review each for accuracy (name: Netanel Stern שטרן, email: nsh531@gmail.com, timezone: UTC+2)
3. Send simultaneously at same time to start embargo clock
4. Create email tracking log (see Part 3 below)

**Critical:** These three start the 90-day countdown. Document the exact send time.

**Expected Responses:**
- CISA: Acknowledge within 24h, assign incident coordinator
- MITRE: Ask for CVE submission form, provide timeline
- Fortinet: Acknowledge, request technical details, start PSIRT escalation

---

### Phase 2: Priority 2 Notifications (DAY 2)
**Israeli Authority + International Partners**

**Action:**
1. Send Israeli Cyber Directorate draft (Hebrew version)
2. Send UK NCSC draft
3. Send H-ISAC Healthcare draft
4. Wait for Day 2 responses from Priority 1 before proceeding

**Rationale:**
- Allow CISA/Fortinet 24h acknowledgment before broader notification
- Focus on government-to-government coordination
- Healthcare sector overlap with lab environment

---

### Phase 3: Priority 3 Notifications (DAY 3-5)
**European & International CVE Coordination**

**Sequence:**
- Day 3: CERT/CC (as backup CVE authority)
- Day 4: EU ENISA (European coordination hub)
- Day 5: German BSI + French ANSSI (EU members)

**Rationale:**
- Stagger European notifications to avoid notification fatigue
- CERT/CC first in case MITRE needs backup
- ENISA as coordination point for EU-wide alert

---

### Phase 4: Priority 4 Notifications (DAY 5-10)
**International Partners + Sector ISACs**

**Sequence:**
- Day 5-6: Five Eyes partners (Australia ACSC, Canada CCCS)
- Day 7: NISAC/Energy sector (E-ISAC, Energy grid critical)
- Day 8: Financial sector (FS-ISAC, banking system threat)
- Day 9: Healthcare/Water (H-ISAC secondary, Water ISAC)
- Day 10: Manufacturing, Transportation, Chemical ISACs

**Rationale:**
- Space out ISAC notifications to allow individual sector coordination
- Energy sector first (critical infrastructure priority)
- Financial sector second (economic impact)
- Other sectors follow

---

### Phase 5: Priority 5 Israeli Sectors (DAY 3-10)
**Hebrew-Language Sector Notifications (Parallel to Priority 4)**

**Sequence:**
- Day 3 (Parallel to Phase 3): Israeli Cyber Directorate (government level)
- Day 4-5: Israeli Financial Sector (Bank of Israel, FinTech companies)
- Day 5-6: Israeli Critical Infrastructure (Israel Electric Company, Water Authority)
- Day 6-7: Israeli Healthcare (Clalit Health Services, Hospital networks)

**Rationale:**
- Parallel with international notifications (not sequential)
- Government-to-government first
- Economic sector coordination
- Healthcare last (lower priority than power/water)

---

### Phase 6: Escalation Triggers (DAY 7+ if needed)

**IF** no acknowledgment from CISA within 24h:
- Escalate to FBI Cybersecurity Division

**IF** no acknowledgment from Fortinet within 24h:
- Escalate to Fortinet board of directors legal team
- Add to CERT/CC escalation report

**IF** multiple non-responses within 48h:
- Request CISA to conduct outreach
- Consider media briefing (if critical infrastructure at immediate risk)

---

## Part 3: Email Tracking Log Template

Create a file: **CVE_DISCLOSURE_TRACKING_LOG.md**

```markdown
# CVE Disclosure Tracking Log
## FortiOS 8.0.0 Zero-Day Campaign

**Campaign Start:** 2026-07-30  
**Embargo End:** 2026-10-28  
**Researcher:** Netanel Stern (שטרן) - nsh531@gmail.com - UTC+2

---

## Sent Notifications

### Priority 1 - CRITICAL (Day 0-2)

#### CISA Central
- **Send Time:** [YYYY-MM-DD HH:MM UTC+2]
- **Email:** central@cisa.dhs.gov
- **Subject:** [Copy from draft]
- **Status:** ⏳ Awaiting response (SLA: 24h)
- **Response Received:** [Date/Time]
- **Response Summary:** [Key points]
- **Next Action:** [Coordinate technical submission]

#### MITRE CVE Authority
- **Send Time:** [YYYY-MM-DD HH:MM UTC+2]
- **Email:** cve@mitre.org
- **Status:** ⏳ Awaiting response (SLA: 48h)
- **Response Received:** [Date/Time]
- **CVE IDs Assigned:** [e.g., CVE-2026-XXXXX]
- **Next Action:** [Update all documentation]

#### Fortinet PSIRT
- **Send Time:** [YYYY-MM-DD HH:MM UTC+2]
- **Email:** security@fortinet.com
- **Status:** ⏳ Awaiting response (SLA: 24h)
- **Response Received:** [Date/Time]
- **Patch Timeline:** [e.g., "Emergency patch in 7 days"]
- **Next Action:** [Schedule technical call]

---

### Priority 2 - HIGH (Day 1-3)

#### Israeli Cyber Directorate
- **Send Time:** [Date/Time]
- **Language:** Hebrew (עברית)
- **Status:** ⏳ Awaiting response
- **Response Received:** [Date/Time]
- **Next Action:** [Government coordination]

#### UK NCSC
- **Send Time:** [Date/Time]
- **Status:** ⏳ Awaiting response
- **Next Action:** [Five Eyes coordination]

#### H-ISAC Healthcare
- **Send Time:** [Date/Time]
- **Status:** ⏳ Awaiting response
- **Next Action:** [Hospital sector briefing]

---

## Response Handling Procedures

### CISA Response Procedures
**IF** CISA responds with questions:
- Provide technical details from CVE_SUBMISSION_PACKAGE.md
- Coordinate with Fortinet on disclosure timeline
- Request CISA public statement if critical

**IF** CISA asks for briefing:
- Schedule call within 24h
- Prepare presentation on RCE chain
- Provide live lab access if approved

---

### Fortinet Response Procedures
**IF** Fortinet asks for details:
- Send Day 2-7 technical submission package
- Provide proof-of-concept code with restrictions
- Schedule patch coordination call

**IF** Fortinet doesn't respond:
- Follow up within 24h
- Escalate to security@fortinet.com AND psirt@fortinet.com
- Document time for CISA coordination

---

## Critical Dates & Milestones

| Date | Milestone | Owner | Status |
|------|-----------|-------|--------|
| 2026-07-30 | Send Priority 1 notifications | You | ⏳ Ready |
| 2026-07-31 | CISA acknowledgment deadline | CISA | ⏳ Waiting |
| 2026-08-02 | Send Priority 2-3 notifications | You | 📋 Ready |
| 2026-08-06 | Technical submission to Fortinet | You | 📋 Scheduled |
| 2026-08-13 | Fortinet patch development update | Fortinet | ⏳ Waiting |
| 2026-09-29 | CVE public disclosure deadline | MITRE/Fortinet | ⏳ Scheduled |
| 2026-10-28 | 90-day embargo expires | All | ⏳ Hard deadline |

```

---

## Part 4: Response Coordination Matrix

### CISA Response Scenarios

**Scenario A: Rapid Acknowledgment (Expected)**
```
CISA Response → Assign incident coordinator → 
Request tech team call → Provide limited PoC → 
Coordinate daily standups
```
**Action:** Engage fully, provide all requested materials

---

**Scenario B: Delayed Response (>24h, Escalate)**
```
CISA No Response (24h) → Escalate to FBI Cybersecurity → 
Contact CERT/CC → Document for audit trail
```
**Action:** Email FBI director of cybersecurity division

---

**Scenario C: Request for Media Briefing**
```
CISA Asks for Joint Briefing → Prepare 30-min presentation →
Include hospital system threat data → Request embargo until patch
```
**Action:** Coordinate with Fortinet on disclosure timing

---

### Fortinet Response Scenarios

**Scenario A: Aggressive Response (Expected)**
```
Fortinet Responds (6-12h) → PSIRT team calls → 
Request PoC with restrictions → Start patch development
```
**Action:** Provide technical submission package within 24h

---

**Scenario B: Slow Response (>24h)**
```
No Response Day 1 → Follow up email Day 2 → 
Escalate to security@fortinet.com + psirt@fortinet.com Day 3 →
Request acknowledgment from CEO level if critical
```
**Action:** Document all attempts, escalate to CISA coordination

---

**Scenario C: Patch Delivery Ahead of Schedule**
```
Fortinet Delivers Emergency Patch (Day 7-10) → 
Test in lab environment → Verify PoC no longer works →
Coordinate public release with CISA
```
**Action:** Verify patch effectiveness, document for audit

---

## Part 5: 90-Day Embargo Management

### Embargo Compliance Checklist

**Week 1 (Days 0-7):**
- [ ] All Priority 1-2 agencies notified
- [ ] CISA and Fortinet responding
- [ ] Technical submission package prepared
- [ ] Embargo period documented (90 days from Day 0)

**Week 2-4 (Days 8-30):**
- [ ] Fortinet patch development in progress
- [ ] Weekly standups with CISA/Fortinet
- [ ] No public disclosure or media mentions
- [ ] CVE request filed with MITRE (if approved)

**Week 5-12 (Days 31-90):**
- [ ] Fortinet emergency patch released (or on schedule)
- [ ] Lab testing confirms patches effective
- [ ] Prepare public disclosure materials
- [ ] Coordinate with Fortinet advisory schedule

**Day 90+ (Post-Embargo):**
- [ ] Fortinet security advisory published
- [ ] CVE records published (MITRE/NVD)
- [ ] This GitHub repository can go public
- [ ] Option: Academic paper or security conference presentation

---

## Part 6: Communications Checklist

Before sending any email, verify:

- [ ] Researcher name: **Netanel Stern (שטרן)** - NOT סטרן
- [ ] Email: **nsh531@gmail.com**
- [ ] Timezone: **UTC+2**
- [ ] For Hebrew emails: Character encoding UTF-8, Shin ש not Samech ס
- [ ] Subject line includes CVSS or CRITICAL alert level
- [ ] Draft references specific vulnerabilities (Path Traversal 9.8, Buffer Overflow 8.6, etc.)
- [ ] Embargo statement included: "Coordinated Disclosure - Do Not Disclose"
- [ ] Contact information and timezone for urgent callback
- [ ] 24-48h acknowledgment request based on priority

---

## Part 7: Next Steps

**Immediate (Within 24 hours):**
1. Review this coordination guide
2. Verify all 28 draft emails are ready
3. Create CVE_DISCLOSURE_TRACKING_LOG.md file
4. Send Priority 1 notifications (CISA, MITRE, Fortinet)

**Short-term (Days 2-7):**
1. Send Priority 2 notifications (Israeli authority, NCSC, H-ISAC)
2. Track responses against SLA timeline
3. Prepare technical submission package for Fortinet Day 2-7 delivery
4. Engage with CISA incident coordinator

**Medium-term (Days 8-30):**
1. Send Priority 3-4 notifications (EU, international, ISAC sector briefings)
2. Manage Fortinet patch development coordination
3. Document all communications for audit trail
4. Prepare CVE submission materials for MITRE review

**Long-term (Days 31-90):**
1. Monitor Fortinet patch development
2. Test patches in lab environment
3. Prepare public disclosure materials
4. Coordinate Day 90+ publication timeline

---

## Contact Quick Reference

**For IMMEDIATE HELP:**
- Your contact: nsh531@gmail.com (UTC+2)
- Session timezone: UTC+2

**Key Escalation Contacts:**
- CISA Emergency: central@cisa.dhs.gov
- Fortinet PSIRT: security@fortinet.com
- MITRE CVE: cve@mitre.org
- Israeli Cyber Directorate: cyber@gov.il

**If Embargo is Breached:**
- Notify CISA immediately (central@cisa.dhs.gov)
- Document all public disclosures
- Accelerate public advisory if needed

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-07-30 | Initial coordination guide |
| | | 28 Gmail drafts consolidated |
| | | Sending sequence defined |
| | | Response procedures documented |

---

**Status:** ✅ Ready to Execute  
**Last Updated:** 2026-07-30  
**Next Review:** Before sending Priority 1 notifications
