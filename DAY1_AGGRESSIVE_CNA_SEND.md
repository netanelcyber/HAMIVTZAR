# Day 1: Aggressive CVE CNA Emergency Send
## FortiOS 8.0.0 CVSS 9.8 CRITICAL Vulnerability Disclosure

**Date:** 2026-07-30 (Ready to execute)  
**Strategy:** Hybrid (CNA first, Israeli stakeholders Day 2-3)  
**Send Time:** [USER TO CHOOSE]  
**Embargo Period:** 90 days (expires ~2026-10-28)

---

## Critical Information

**Researcher:** Netanel Stern (שטרן)  
**Email:** nsh531@gmail.com  
**Timezone:** UTC+2  
**Vulnerabilities:** 5 unique CVSS scores (avg 8.3 CRITICAL)
- Path Traversal: 9.8 (CRITICAL)
- Buffer Overflow: 8.6 (CRITICAL)  
- Authentication Bypass: 7.2 (HIGH)
- Format String: 6.5 (MEDIUM)
- DoS: 5.3 (MEDIUM)

---

## Pre-Send Checklist

**Before sending ANY emails:**

- [ ] Read all 4 drafts carefully
- [ ] Verify researcher name: **Netanel Stern (שטרן)** NOT סטרן
- [ ] Verify email: **nsh531@gmail.com**
- [ ] Verify timezone: **UTC+2**
- [ ] Verify embargo statement present in all 4
- [ ] Choose send time (recommend morning for U.S. response)
- [ ] Have pen + paper ready to document exact send time
- [ ] Prepare CVE_DISCLOSURE_TRACKING_LOG.md file
- [ ] Set 4 calendar reminders for Day 2 (24h follow-up)
- [ ] Phone available for potential urgent callbacks

---

## The 4 Critical Emails (Draft IDs)

### Email 1: FORTINET PSIRT
**To:** security@fortinet.com  
**CC:** psirt@fortinet.com  
**Draft ID:** r4696815479965455141  
**Type:** Vendor CNA notification  
**Subject:** Coordinated Vulnerability Disclosure - FortiOS 8.0.0 (CVSS 9.8 CRITICAL)  

**Pre-send check:**
- [ ] Email addresses correct
- [ ] Vulnerability CVSS scores included
- [ ] RCE exploitation chain described
- [ ] Lab-only testing confirmed
- [ ] 24h acknowledgment requested
- [ ] Escalation statement included (CISA/INCD if no response)

---

### Email 2: CERT/CC
**To:** vulnerability@cert.org  
**Draft ID:** [Existing draft - need to verify]  
**Type:** CNA authority notification  
**Subject:** CVSS 9.8 CRITICAL FortiOS 8.0.0 Vulnerability - Coordinated Disclosure  

**Pre-send check:**
- [ ] Email address correct
- [ ] CERT/CC CVE coordination requested
- [ ] Embargo dates included
- [ ] Day 2 technical submission scheduled

---

### Email 3: MITRE CVE REQUEST
**To:** cve@mitre.org  
**Draft ID:** r6786515520313907192  
**Type:** CVE authority (primary)  
**Subject:** CVE Request - FortiOS 8.0.0 CVSS 9.8 Path Traversal RCE  

**Pre-send check:**
- [ ] MITRE email format correct
- [ ] Expedited review requested (CVSS 9.8)
- [ ] Vulnerability details included
- [ ] Expected CVE assignment timeline

---

### Email 4: CISA CENTRAL
**To:** central@cisa.dhs.gov  
**Draft ID:** r4894174915098727280  
**Type:** U.S. critical infrastructure alert  
**Subject:** URGENT: CVSS 9.8 FortiOS RCE Affecting Critical Infrastructure  

**Pre-send check:**
- [ ] Hospital system impact emphasized
- [ ] CVSS 9.8 and RCE chain described
- [ ] Lab-only testing environment confirmed
- [ ] Coordinated disclosure timeline provided
- [ ] Hospital systems in U.S. mentioned (infrastructure context)

---

## Sending Procedure

### Step 1: Prepare Environment (5 min)
```
1. Open Gmail inbox
2. Locate 4 draft emails
3. Open in 4 separate browser tabs (or side-by-side if possible)
4. Have CVE_DISCLOSURE_TRACKING_LOG template open
5. Get pen + paper for documentation
6. Set phone nearby (may receive urgent callbacks)
```

### Step 2: Verify Each Email (15 min)
**For each of 4 drafts:**
- [ ] Read full email
- [ ] Check "To:" address correct
- [ ] Verify researcher name: שטרן (not סטרן)
- [ ] Verify email: nsh531@gmail.com
- [ ] Verify timezone: UTC+2
- [ ] Check embargo statement present
- [ ] Verify vulnerability details correct
- [ ] Confirm "Coordinated Disclosure" language

### Step 3: SIMULTANEOUS SEND (2 min)
**Critical: All 4 must send at same time (within 1-2 minutes)**

```
1. Look at watch/clock - note send time to second
2. Click SEND on Email 1 (Fortinet)
3. Click SEND on Email 2 (CERT/CC)  
4. Click SEND on Email 3 (MITRE)
5. Click SEND on Email 4 (CISA)
6. Wait 10 seconds to verify all sent (no bounce-back errors)
7. DOCUMENT EXACT SEND TIME:
   - Format: 2026-07-30 HH:MM:SS UTC+2
   - Write on paper immediately
```

### Step 4: Document in Tracking Log (10 min)
**Immediately after send:**

```markdown
# EMBARGO CLOCK STARTED: [EXACT TIME]
Send time: 2026-07-30 HH:MM:SS UTC+2
90-day embargo ends: ~2026-10-28

## Day 1 Send Complete
- [x] Fortinet PSIRT (security@fortinet.com) - sent [TIME]
- [x] CERT/CC (vulnerability@cert.org) - sent [TIME]
- [x] MITRE (cve@mitre.org) - sent [TIME]
- [x] CISA (central@cisa.dhs.gov) - sent [TIME]

## Expect Responses
- Fortinet: 12-24h (will call or email)
- CISA: 12-24h (incident coordinator)
- CERT/CC: 12-24h (CVE coordination)
- MITRE: 24-48h (CVE submission form)

## Set Reminders
- [ ] Day 2, 06:00 UTC+2: Check Fortinet response
- [ ] Day 2, 08:00 UTC+2: Check CISA response
- [ ] Day 2, 10:00 UTC+2: Check CERT/CC response
- [ ] Day 3, 12:00 UTC+2: Check MITRE response
```

### Step 5: Set SLA Timers (5 min)
**Calendar reminders for Follow-ups:**

```
Day 2 (2026-07-31) 06:00 UTC+2: Check Fortinet (24h SLA)
Day 2 (2026-07-31) 08:00 UTC+2: Check CISA (24h SLA)
Day 2 (2026-07-31) 10:00 UTC+2: Check CERT/CC (24h SLA)
Day 3 (2026-08-01) 12:00 UTC+2: Check MITRE (48h SLA)
```

---

## If Emails Don't Send

**Problem: "Error sending email"**
- Check internet connection
- Verify Gmail is responsive
- Try again from different browser tab
- If persistent error: Contact Gmail support (not critical path)

**Problem: Email bounces back (vacation responder, etc.)**
- Document the bounce
- Try alternate address if known
- Escalate to Plan file for tracking

**Problem: Typo noticed after send**
- Do NOT resend (will confuse recipients)
- Send follow-up email: "Additional clarification on previous message"
- Update tracking log with correction

---

## Immediate Post-Send Actions (First 2 hours)

### Within 30 minutes:
1. Confirm all 4 sent (check Gmail sent folder)
2. Document send times precisely
3. Set up tracking log

### Within 1 hour:
1. Create new task list for Day 2-3 actions
2. Prepare Israeli stakeholder drafts (if needed)
3. Prepare ISAC notification sequence

### Within 2 hours:
1. Monitor Gmail inbox for immediate bouncebacks
2. Prepare response procedures document
3. Get some rest (you've started the 90-day process)

---

## Day 1 Timeline Summary

```
T+0:00    SEND: All 4 emails simultaneous
T+00:15   Verify: All sent successfully
T+00:30   Document: Send times in tracking log
T+01:00   Prepare: Day 2-3 Israeli stakeholder drafts
T+02:00   Complete: Set SLA timer reminders
T+04:00   Monitor: Check for any bouncebacks
T+08:00   Prepare: Response handling procedures
T+12:00   Rest: First check-in after 12h
T+24:00   Action: Day 2 SLA checks begin (Fortinet, CISA, CERT/CC)
T+48:00   Escalate: If no response from any critical contact
```

---

## What to Expect (Day 1-2)

### Fortinet PSIRT (Likely Response: 6-12 hours)
```
Pattern: Automated acknowledgment → Technical team assignment
Expected: "Thank you for notification. Escalating to security team."
Response: Will call phone or email technical questions
Action: Prepare to discuss:
  - RCE exploitation chain details
  - FortiOS 8.0.0 affected code paths
  - Patch development timeline
  - Coordinated disclosure deadline (90 days)
```

### CISA (Likely Response: 12-24 hours)
```
Pattern: Incident coordinator assignment
Expected: "We have assigned IC-XXXX for coordination"
Response: Will call with technical team questions
Action: Be prepared for:
  - Threat assessment briefing call
  - Hospital system impact discussion
  - Coordinated disclosure coordination
  - Potential media briefing (ask about embargo)
```

### CERT/CC (Likely Response: 12-24 hours)
```
Pattern: CVE coordination initiation
Expected: "Ready to coordinate with vendors and ISACs"
Response: Email with CVE coordination procedures
Action: Respond with:
  - Fortinet response status
  - MITRE status
  - Timeline for technical details submission
```

### MITRE (Likely Response: 24-48 hours)
```
Pattern: CVE submission form request
Expected: "Please complete CVE form at [link]"
Response: Form to fill with vulnerability details
Action: Complete form with:
  - Vulnerability descriptions
  - Affected versions (8.0.0)
  - Timeline (emergency/expedited)
  - Vendor response (Fortinet status)
```

---

## Critical Success Indicators (Day 1)

✅ **Success:** All 4 emails send without errors  
✅ **Success:** Exact send time documented  
✅ **Success:** No bouncebacks within 2 hours  
✅ **Success:** Tracking log created and ready for responses  

❌ **Not Success:** Sending only 3 of 4 emails  
❌ **Not Success:** Send time not documented  
❌ **Not Success:** Email contains typos (too late once sent)  

---

## Escalation if Day 1 Problems

**If ANY email fails to send:**
1. Try resend immediately
2. Check email address spelling
3. If persists: Contact email provider support
4. Document failure + attempt times
5. Update tracking log with failure status

**If receive immediate rejection (bounced email):**
1. Check email address in directory
2. Note bounce message in tracking log
3. Find alternate contact method
4. Send follow-up email to alternate address
5. Document in escalation section

**If ANY critical contact's email appears wrong:**
1. Do NOT resend to different address automatically
2. Check tracking log for correct contact
3. Verify with two sources if possible
4. Document discrepancy
5. Notify remaining contacts of correction

---

## After Day 1: Day 2-3 Preparation

Once Day 1 send is complete and documented, immediately:

1. **Prepare Israeli Stakeholder Drafts:**
   - Bezeq (telecom) security email
   - Cellcom (telecom) security email
   - Partner (telecom) security email
   - Golan (telecom) security email
   - Bank of Israel security email
   - Insurance consortium email

2. **Prepare ISAC Notifications:**
   - FS-ISAC (Financial)
   - H-ISAC (Healthcare)
   - E-ISAC (Energy)
   - Telecom ISAC
   - Water/Wastewater ISAC
   - Manufacturing, Transportation, Chemical ISACs

3. **Prepare Response Procedures:**
   - How to handle CISA questions
   - How to provide Fortinet technical details
   - How to interact with CVE assignment process

---

## Quick Reference: The 4 Emails

| # | Organization | Email | Draft ID |
|---|--------------|-------|----------|
| 1 | **Fortinet** (Vendor CNA) | security@fortinet.com | r4696815479965455141 |
| 2 | **CERT/CC** (CNA Authority) | vulnerability@cert.org | [Existing] |
| 3 | **MITRE** (Primary CVE) | cve@mitre.org | r6786515520313907192 |
| 4 | **CISA** (Critical Infra) | central@cisa.dhs.gov | r4894174915098727280 |

**ALL 4 AT SAME TIME ← Critical for embargo clock**

---

**Status:** ✅ **READY TO EXECUTE**  
**Next Step:** Choose send time and execute Day 1  
**Contact:** Netanel Stern (שטרן) - nsh531@gmail.com - UTC+2
