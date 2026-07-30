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

## STRATEGY: HYBRID AGGRESSIVE MODEL (CVE CNA + Israeli Stakeholders)

**Approved by User: 2026-07-30**

This hybrid approach prioritizes speed and CVE authority while maintaining Israeli stakeholder engagement:

**Phase 1 (Day 1): AGGRESSIVE CVE CNA SEND**
- All 4 critical CVE authorities simultaneously
- Fastest path to CVE assignment and patch coordination
- Direct vendor-to-CNA technical coordination

**Phase 2 (Day 2-3): ISRAELI STAKEHOLDER ENGAGEMENT**
- Direct outreach to telecom companies, banking, insurance
- National-level threat awareness and coordination
- Builds Israeli government response capability

**Rationale:**
- CVSS 9.8 CRITICAL = Emergency bypass standard channels
- CNA organizations can act faster than government
- Israeli stakeholders engage Day 2-3 when CNA process is underway
- Maintains diplomatic/corporate relationships without slowing disclosure

---

## Part 1: Complete Draft Inventory

### Priority 1 - CVE CNA (Day 1, SIMULTANEOUS SEND)
**AGGRESSIVE EMERGENCY SEND - All 4 at Same Time**

| # | Organization | Email | Type | Draft ID | Status | Response SLA |
|---|--------------|-------|------|----------|--------|--------------|
| 1 | Fortinet PSIRT | security@fortinet.com | Vendor CNA | r4696815479965455141 | ✅ Ready | 24 hours |
| 2 | CERT/CC | vulnerability@cert.org | CNA Authority | [Existing] | ✅ Ready | 24 hours |
| 3 | MITRE | cve@mitre.org | Primary CVE Authority | r6786515520313907192 | ✅ Ready | 48 hours |
| 4 | CISA | central@cisa.dhs.gov | U.S. Critical Infra | r4894174915098727280 | ✅ Ready | 24 hours |

**Key Points:**
- **Simultaneous send required** - All 4 emails sent at exact same time
- Fortinet = patch authority (can push emergency update within days)
- CERT/CC + MITRE = CVE assignment (CNA organizations)
- CISA = U.S. critical infrastructure alert (hospital systems)
- Document exact send time to start 90-day embargo clock
- Expect first responses within 12-24 hours

---

### Priority 2 - Israeli Stakeholders (Day 2-3)
**Direct Corporate Outreach - Israeli Critical Infrastructure**

| # | Organization | Type | Email | Status | Contact |
|---|--------------|------|-------|--------|---------|
| 5 | Bezeq (Telecom) | Telecom Provider | security@bezeq.co.il | 📋 Need contact | Israel's largest telecom |
| 6 | Cellcom (Telecom) | Telecom Provider | security@cellcom.co.il | 📋 Need contact | Major telecom operator |
| 7 | Partner (Telecom) | Telecom Provider | security@partner.co.il | 📋 Need contact | Major telecom operator |
| 8 | Golan (Telecom) | Telecom Provider | security@golan.co.il | 📋 Need contact | Regional telecom |
| 9 | Bank of Israel | Banking/Finance | security@bankisrael.org.il | ✅ Ready | Central bank - financial system |
| 10 | Israeli Insurance Companies | Insurance/Finance | [Consortium contact] | 📋 Need contact | Financial system protection |

**Key Points:**
- Direct outreach to critical infrastructure operators (not government)
- Telecom companies: Internet connectivity, mobile networks, backbone infrastructure
- Bank of Israel: Financial system coordination and banking sector alerts
- Insurance sector: Risk management and financial system stability
- These organizations will engage Day 2-3 after CNA process begins Day 1
- No government bureaucracy delays - direct technical coordination with operators

---

### Priority 3 - Global ISACs (Day 2-3, Parallel with Israeli Stakeholders)
**Sector-Specific Threat Intelligence & Information Sharing**

| # | ISAC | Email | Sector | Status | Response SLA |
|---|------|-------|--------|--------|--------------|
| 11 | FS-ISAC | [Contact] | Financial Services | ✅ Ready | 24 hours |
| 12 | E-ISAC | [Contact] | Energy/Utilities | ✅ Ready | 24 hours |
| 13 | H-ISAC | reports@h-isac.org | Healthcare/Hospitals | ✅ Ready | 24 hours |
| 14 | Telecom ISAC | [Contact] | Telecommunications | ✅ Ready | 24 hours |
| 15 | Water/Wastewater ISAC | incident@waterisac.org | Water Infrastructure | ✅ Ready | 48 hours |
| 16 | Manufacturing ISAC | vulnerability@manufacturing-isac.org | Manufacturing | ✅ Ready | 48 hours |
| 17 | Transportation ISAC | incident@transportation-isac.org | Transportation | ✅ Ready | 48 hours |
| 18 | Chemical ISAC | incident@chemin-isac.org | Chemical Industry | ✅ Ready | 48 hours |

**Key Points:**
- ISACs provide sector-specific threat intelligence and coordinated response
- H-ISAC highest priority (hospitals in FortiOS deployment base)
- Parallel send with Israeli stakeholders (Day 2-3)
- Each ISAC coordinates threat response within their sector
- Commercial ISACs respond 24/7 (faster than government)

---

### Priority 4 - International Partners (Day 3-5)
**Five Eyes & International Cybersecurity Coordination**

| # | Country/Agency | Email | Status | Response SLA |
|---|----------------|-------|--------|--------------|
| 19 | UK NCSC | vulnerability-reports@ncsc.gov.uk | ✅ Ready | 48 hours |
| 20 | Australia ACSC | [Contact] | ✅ Ready | 72 hours |
| 21 | Canada CCCS | [Contact] | ✅ Ready | 72 hours |
| 22 | EU ENISA | vulnerability@enisa.europa.eu | ✅ Ready | 72 hours |
| 23 | German BSI | info@bsi.bund.de | ✅ Ready | 72 hours |
| 24 | French ANSSI | vulnerability@anssi.gouv.fr | ✅ Ready | 72 hours |
| 25 | Japan NISC | [Contact] | 📋 Pending | 5 days |
| 26 | South Korea KISA | vulreport@kisa.or.kr | 📋 Pending | 5 days |

**Key Points:**
- Five Eyes coordination (UK, AU, CA priority)
- EU agencies (ENISA, BSI, ANSSI) coordinate European response
- Asian partners (Japan NISC, South Korea KISA) for global coverage
- Stagger to avoid notification fatigue (Day 3, 4, 5)

---

### Priority 5 - Escalation (Day 1-7 if needed)
**IF CRITICAL SLAs MISSED - Immediate Escalation**

| # | Trigger | Contact | Action | Timeline |
|---|---------|---------|--------|----------|
| 27 | Fortinet PSIRT no response (24h) | Fortinet Legal | Escalate to C-suite | Day 2 |
| 28 | CISA no response (24h) | FBI Cybersecurity | Escalate to federal level | Day 2 |
| 29 | MITRE/CERT no response (48h) | Alternative CVE path | Request emergency CVE | Day 3 |
| 30 | No CNA response (72h) | Israeli INCD (cyber@gov.il) | Emergency government escalation | Day 4 |

**Key Points:**
- 24-hour SLAs for Fortinet and CISA (vendor + U.S. critical infra)
- Escalation is automatic if no acknowledgment
- Israeli government (INCD) used only as escalation path if CNA channels fail
- This hybrid model prioritizes speed → escalates to government only if needed

---

## Part 2: Sending Strategy & Timeline

### Phase 1: AGGRESSIVE CVE CNA SEND (DAY 1 - SIMULTANEOUS)
**Critical Emergency Notification - All 4 at Exact Same Time**

**Action:**
1. Set specific send time (e.g., 09:00 UTC+2)
2. Open all 4 Gmail drafts side-by-side (Fortinet, CERT/CC, MITRE, CISA)
3. Verify each email:
   - Researcher: Netanel Stern (שטרן)
   - Email: nsh531@gmail.com
   - Timezone: UTC+2
   - Subject includes: "CVSS 9.8 CRITICAL" or "EMERGENCY"
4. **Send all 4 simultaneously** (critical for embargo timing)
5. Document exact send time in tracking log
6. Set response SLA timers:
   - Fortinet: 24h
   - CISA: 24h
   - CERT/CC: 24h
   - MITRE: 48h

**Expected Immediate Responses (12-24h):**
- Fortinet: Technical team assignment, PSIRT escalation
- CISA: Incident coordinator assignment
- CERT/CC: Acknowledgment, CVE coordination initiation
- MITRE: CVE submission form

**Escalation Trigger:**
- IF no response from any of 4 by 24h → Escalate immediately (see Phase 5)

---

### Phase 2: ISRAELI STAKEHOLDERS (DAY 2-3)
**Direct Corporate Outreach - Israeli Critical Infrastructure**

**Action:**
1. **Day 2 Morning**: Send to Israeli telecom companies (Bezeq, Cellcom, Partner, Golan)
   - Email: security@ addresses for each
   - Subject: Urgent FortiOS vulnerability affecting telecom networks
   - Coordinate with existing CISA/Fortinet timeline

2. **Day 2 Afternoon**: Send to Bank of Israel
   - Email: security@bankisrael.org.il
   - Subject: Critical FortiOS vulnerability affecting financial systems
   - Include banking sector impact assessment

3. **Day 3 Morning**: Send to Israeli insurance companies
   - Subject: Critical FortiOS vulnerability - financial sector impact
   - Coordinate through insurance industry consortium

**Rationale:**
- Direct outreach to infrastructure operators (not government)
- Allows 24h for CNA process to begin before Israeli domestic engagement
- Demonstrates coordinated international response
- Builds Israeli stakeholder confidence in disclosure process

**Expected Responses:**
- Telecom companies: 24-48h (critical infrastructure urgency)
- Bank of Israel: 24h (central bank priority)
- Insurance: 48h (coordination through consortiums)

---

### Phase 3: GLOBAL ISACs (DAY 2-3, PARALLEL with Phase 2)
**Sector-Specific Threat Intelligence**

**Action:**
1. **Day 2 Morning** (with Israeli stakeholders):
   - Send to FS-ISAC (Financial Services) - highest priority
   - Send to H-ISAC (Healthcare) - hospital systems affected
   - Send to E-ISAC (Energy) - critical infrastructure

2. **Day 2 Afternoon**:
   - Send to Telecom ISAC (telecommunications)
   - Send to Water/Wastewater ISAC

3. **Day 3 Morning**:
   - Send to Manufacturing, Transportation, Chemical ISACs

**Rationale:**
- ISACs provide 24/7 sector-specific threat response
- Higher priority ISACs (Finance, Healthcare, Energy) go first
- Parallel with Israeli stakeholders (not sequential)
- Each ISAC coordinates threat response within their sector

**Expected Responses:**
- Financial/Healthcare/Energy: 24h (critical sectors)
- Other sectors: 24-48h

---

### Phase 4: INTERNATIONAL PARTNERS (DAY 3-5)
**Five Eyes & Global Cybersecurity Coordination**

**Sequence:**
- **Day 3**: UK NCSC (Five Eyes lead, fastest coordination)
- **Day 4**: Australia ACSC, Canada CCCS (Five Eyes partners)
- **Day 5**: EU ENISA (European coordination hub)
- **Day 5**: German BSI, French ANSSI (EU member states)
- **Day 5-6**: Japan NISC, South Korea KISA (Asian-Pacific)

**Rationale:**
- Five Eyes coordinate first (fastest trusted partnership)
- EU agencies next (European critical infrastructure)
- Asian partners complete global coverage
- Stagger to avoid notification fatigue

---

### Phase 5: ESCALATION TRIGGERS (DAY 1-4, IF NEEDED)

**IF Fortinet PSIRT no response (24h):**
- Contact: Fortinet Legal / Board escalation
- Action: Escalate CVSS 9.8 emergency to C-suite
- Timeline: Day 2

**IF CISA no response (24h):**
- Contact: FBI Cybersecurity Division
- Action: Escalate to federal law enforcement coordination
- Timeline: Day 2

**IF MITRE/CERT/CC no response (48h):**
- Contact: Alternative CVE authority
- Action: File emergency CVE request through backup channel
- Timeline: Day 3

**IF CRITICAL SILENCE (72h+):**
- Contact: Israeli National Cyber Directorate (cyber@gov.il)
- Action: Government-level escalation
- Timeline: Day 4
- Rationale: Only use government escalation if commercial CNA channels completely fail

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
