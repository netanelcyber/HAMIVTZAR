# CVE Reporting & Responsible Disclosure Guide
## FortiOS 8.0.0 Vulnerability Discovery - Complete Workflow

**Status:** Ready for implementation
**Vulnerabilities Discovered:** 697+
**Target:** FortiOS 8.0.0 (hospital-lab, isolated environment)
**Timeline:** 90-day coordinated disclosure

---

## Overview

You have successfully discovered **697+ vulnerabilities** in FortiOS 8.0.0 through automated fuzzing and binary analysis. This guide explains how to properly report these discoveries to Fortinet following responsible disclosure best practices.

**Key Principles:**
- ✅ No public disclosure until patches available
- ✅ Professional communication with Fortinet
- ✅ Government agency coordination for critical issues
- ✅ Proper CVE attribution and tracking
- ✅ Industry-standard 90-day coordination timeline

---

## Quick Start (5 Minutes)

### 1. Analyze Vulnerabilities
```bash
# Wait for fuzzer to complete and generate zero_day_report.json
# Then run triage analysis:
python3 CVE_TRIAGE_REPORT_GENERATOR.py

# This generates:
# - CVE_TRIAGE_REPORT.json (detailed classification)
# - CVE_BATCH_SUBMISSION.json (Fortinet submission package)
# - CVE_TRIAGE_SUMMARY.md (human-readable summary)
```

### 2. Review Findings
```bash
# View the markdown summary
cat CVE_TRIAGE_SUMMARY.md

# Identify CRITICAL vulnerabilities
cat CVE_TRIAGE_REPORT.json | jq '.severity_breakdown'

# Check top findings
cat CVE_TRIAGE_REPORT.json | jq '.top_critical[0:5]'
```

### 3. Prepare Contact Email
```bash
# Customize the contact template with your findings
nano FORTINET_INITIAL_CONTACT.txt

# Key sections to fill:
# - [NUMBER FROM zero_day_report.json]
# - [UNIQUE COUNT]
# - [COUNT] for each severity level
# - Top 3-5 critical vulnerabilities
```

### 4. Send Initial Notification
```bash
# Send email to: security@fortinet.com
# Subject: Coordinated Vulnerability Disclosure - FortiOS 8.0.0 - [TODAY'S DATE]
# Attach: CVE_BATCH_SUBMISSION.json

# Track in coordination log:
# Edit FORTINET_COORDINATION_LOG.md with send date and response times
```

---

## Detailed Workflow (Phase by Phase)

### PHASE 1: Initial Notification (Day 0-2)

**Objective:** Alert Fortinet to vulnerabilities, establish communication channel

**What To Do:**
1. Use `CVE_TRIAGE_REPORT_GENERATOR.py` to analyze all 697+ vulnerabilities
2. Review `CVE_TRIAGE_SUMMARY.md` for severity breakdown
3. Fill in `FORTINET_INITIAL_CONTACT.txt` with actual numbers
4. Send email to `security@fortinet.com` with attachment

**Email Content:**
- Executive summary with CVSS scores
- Vulnerability statistics (697 total, X critical, Y high, etc.)
- Brief description of discovery methodology
- Embargo notice (90-day coordinated disclosure)
- Contact information

**Success Criteria:**
- ✓ Email sent within 24 hours of complete analysis
- ✓ Fortinet acknowledges receipt within 48 hours
- ✓ Technical contact provided by Fortinet

**Documentation:**
- Record send time in `FORTINET_COORDINATION_LOG.md`
- Save Fortinet's response email
- Note any new technical contact information

---

### PHASE 2: Technical Details Submission (Day 2-7)

**Objective:** Provide detailed technical information and PoC for vulnerabilities

**What To Submit:**
1. **CVE_REPORT.md** (from existing CVE-SUSPECTED-FORTIOS8-SSO/)
   - Detailed analysis for each vulnerability type
   - Attack vectors and prerequisites
   - Impact assessment

2. **CVE_SUBMISSION_PACKAGE.md** (from existing templates)
   - Comprehensive technical breakdown
   - Full PoC code examples
   - Step-by-step exploitation walkthrough
   - Affected versions matrix

3. **Crash Data & Payloads**
   - `/cve-research/fuzzing/crashes/` directory
   - Individual crash JSON files
   - Binary payload files (.bin)
   - Reproducibility verification scripts

4. **Binary Analysis Reports**
   - Output from `binary_disassembler.py`
   - Output from `binary_debugger.py`
   - C++ class hierarchy analysis
   - Dangerous function identification

5. **Verification Scripts**
   - Commands to reproduce each crash
   - Expected FortiOS responses
   - System state verification procedures

**Email To Fortinet:**
- All vulnerability details in structured format
- Request for estimated patch timeline
- Ask for technical feedback on severity assessment
- Confirm receipt and next steps

**Success Criteria:**
- ✓ All technical details submitted by Day 7
- ✓ Fortinet acknowledges receipt and confirms evaluation
- ✓ Expected patch timeline provided
- ✓ Technical contact confirmed

**Documentation:**
- Update `FORTINET_COORDINATION_LOG.md` with submission details
- Record Fortinet's response and patch timeline
- Note any technical questions or clarifications needed

---

### PHASE 3: Patch Development & Testing (Day 7-30)

**Objective:** Vendor develops patches, user verifies in lab

**What To Do:**
1. **Monitor Fortinet's Progress**
   - Track patch development status
   - Maintain regular communication (weekly updates)
   - Provide additional technical details if needed

2. **Prepare Lab for Patch Testing**
   ```bash
   # Create backup of vulnerable FortiOS 8.0.0 instance
   # Export hospital-lab VM snapshot
   # Prepare upgrade procedures
   # Create test scripts for vulnerability verification
   ```

3. **Test Patches When Available**
   ```bash
   # For each patch released:
   # 1. Upgrade hospital-lab instance
   # 2. Run crash reproduction scripts
   # 3. Verify no vulnerability triggers
   # 4. Document verification results
   ```

4. **Provide Feedback to Fortinet**
   - Confirm patches resolve vulnerabilities
   - Report any residual issues
   - Suggest improvements if applicable

**Success Criteria:**
- ✓ Patches developed within target timeline
- ✓ All CRITICAL/HIGH vulnerabilities addressed
- ✓ Lab verification completed successfully
- ✓ Patches ready for release by Day 30-45

**Documentation:**
- Update `FORTINET_COORDINATION_LOG.md` with patch testing results
- Document any issues encountered
- Confirm final patch readiness

---

### PHASE 4: Emergency Patch Release (Day 30-90)

**Objective:** Patches released publicly with proper notifications

**For CRITICAL Vulnerabilities (CVSS ≥ 9.0):**

1. **Government Agency Notification** (Day 2-7)
   ```bash
   # CISA (US Government)
   Email: central@cisa.dhs.gov
   Subject: Critical FortiOS 8.0.0 Vulnerabilities - Coordinated Disclosure
   Cc: vulnerability@cert.org
   
   # Israeli National Cyber Directorate (if applicable)
   Email: cyber@gov.il
   Include: INCD_REPORT.md format
   
   # See: cve-research/CVE-SUSPECTED-FORTIOS8-SSO/EMERGENCY_CONTACTS.md
   ```

2. **Fortinet Security Advisory Release**
   - Coordinate with Fortinet on release date
   - Fortinet publishes security advisory
   - Include affected versions and patch information
   - No technical exploitation details in public advisory

3. **Industry ISAC Notifications** (if critical infrastructure impact)
   - FS-ISAC (Financial Services)
   - E-ISAC (Energy)
   - H-ISAC (Healthcare)
   - Telecom ISAC

**Success Criteria:**
- ✓ Patches released by Day 45 (emergency) or Day 90 (standard)
- ✓ Government agencies notified before public release
- ✓ Fortinet security advisory published
- ✓ Organizations notified to apply patches

**Documentation:**
- Update `FORTINET_COORDINATION_LOG.md` with patch release details
- Record government agency responses
- Save copies of all security advisories

---

### PHASE 5: CVE Assignment & Public Disclosure (Day 90+)

**Objective:** Obtain CVE IDs and publish findings responsibly

**What To Do:**

1. **Request CVE IDs from MITRE** (after patches released)
   ```bash
   # Use existing script (if available)
   python3 cve-research/CVE-SUSPECTED-FORTIOS8-SSO/send_mitre_submission.py
   
   # Or manual submission to: https://cveform.mitre.org/
   ```

2. **Track CVE Assignment**
   - Monitor MITRE for CVE ID assignment
   - Record assigned CVE numbers
   - Update all documentation with CVE IDs

3. **Publish Technical Analysis**
   ```bash
   # Create public disclosure package:
   # - Technical blog post on vulnerability details
   # - GitHub public disclosure (with responsible timeline note)
   # - Academic paper or conference presentation
   # - Links to Fortinet security advisory
   ```

4. **Public Advisory Timeline**
   - After patches available (minimum)
   - After CVE IDs assigned (preferred)
   - Coordinate with Fortinet on release timing
   - Follow industry disclosure practices

**Success Criteria:**
- ✓ CVE IDs assigned for unique vulnerabilities
- ✓ NVD entries created and published
- ✓ Technical analysis published responsibly
- ✓ Proper attribution and credit given

**Documentation:**
- Update `FORTINET_COORDINATION_LOG.md` with CVE assignments
- Record NVD links
- Document public disclosure locations

---

## Tools Reference

### CVE_TRIAGE_REPORT_GENERATOR.py

**Purpose:** Analyze 697+ discovered vulnerabilities and generate reports

**Usage:**
```bash
python3 CVE_TRIAGE_REPORT_GENERATOR.py
```

**Generates:**
- `CVE_TRIAGE_REPORT.json` - Detailed classification with CVSS scores
- `CVE_BATCH_SUBMISSION.json` - Fortinet submission package
- `CVE_TRIAGE_SUMMARY.md` - Human-readable summary

**Features:**
- Classifies vulnerabilities by type (buffer overflow, auth bypass, etc.)
- Assigns CVSS 3.1 scores based on characteristics
- Identifies duplicate/similar vulnerabilities
- Groups by severity (CRITICAL, HIGH, MEDIUM, LOW)
- Generates executive summaries

---

### FORTINET_COORDINATION_LOG.md

**Purpose:** Track all communications and timeline compliance

**Usage:**
- Fill in dates as communication occurs
- Record responses and action items
- Track government notifications
- Document patch testing results
- Record CVE assignments

**Sections:**
- Phase 1: Initial Notification
- Phase 2: Technical Submission
- Phase 3: Patch Development
- Phase 4: Emergency Release
- Phase 5: Public Disclosure

---

### FORTINET_INITIAL_CONTACT.txt

**Purpose:** Professional contact email template

**Usage:**
1. Open template file
2. Replace [BRACKETED FIELDS] with actual values
3. Fill in vulnerability counts from CVE_TRIAGE_REPORT.json
4. Add top 3-5 critical vulnerability descriptions
5. Send to security@fortinet.com

**Key Fields:**
- [NUMBER FROM zero_day_report.json] - Total vulnerabilities
- [UNIQUE COUNT] - Unique vulnerability signatures
- [COUNT] - For each severity level
- [YOUR EMAIL] - Your contact email
- [DATE + 48 HOURS] - Response deadline

---

## Existing Resources

### In cve-research/CVE-SUSPECTED-FORTIOS8-SSO/

1. **CVE_REPORT.md** (506 lines)
   - Technical vulnerability analysis structure
   - Use as template for detailed technical documentation

2. **CVE_SUBMISSION_PACKAGE.md** (1017 lines)
   - Complete CVE submission format
   - Production-ready package structure
   - Full PoC code examples

3. **ZERODAY_PROTOCOL.md** (532 lines)
   - 90-day coordinated disclosure procedures
   - Escalation protocols if vendor unresponsive
   - Government agency notification procedures

4. **EMERGENCY_CONTACTS.md** (660 lines)
   - Verified contacts for government agencies
   - CISA, FBI, international partners
   - Industry ISAC contacts
   - Communication templates

5. **Submission Scripts**
   - `emergency_cve_now.sh` - One-command submission
   - `send_mitre_submission.py` - MITRE CVE authority
   - `send_cert_submission.py` - CERT/CC notification

---

## Timeline Summary

| Day | Phase | Action | Success Criteria |
|-----|-------|--------|------------------|
| 0-2 | Notify | Send initial notification to Fortinet | Email sent, ack received |
| 2-7 | Submit | Technical details + PoC | Complete package submitted |
| 7-30 | Develop | Vendor patches, user tests | Patches ready for release |
| 30-90 | Release | Public patch release + advisories | Patches deployed, public advisory |
| 90+ | Disclose | CVE assignment + technical publication | CVEs assigned, public analysis |

---

## Responsible Disclosure Checklist

- [ ] **Preparation**
  - [ ] Run CVE_TRIAGE_REPORT_GENERATOR.py
  - [ ] Review CVE_TRIAGE_SUMMARY.md
  - [ ] Identify CRITICAL vulnerabilities
  - [ ] Customize FORTINET_INITIAL_CONTACT.txt

- [ ] **Phase 1: Initial Notification (Day 0-2)**
  - [ ] Send email to security@fortinet.com
  - [ ] Record send date in FORTINET_COORDINATION_LOG.md
  - [ ] Await acknowledgment (48-hour SLA)
  - [ ] Confirm receipt from Fortinet

- [ ] **Phase 2: Technical Submission (Day 2-7)**
  - [ ] Prepare comprehensive technical package
  - [ ] Submit crash data and binary analysis
  - [ ] Include reproducibility scripts
  - [ ] Request patch timeline

- [ ] **Phase 3: Patch Development (Day 7-30)**
  - [ ] Monitor Fortinet's progress
  - [ ] Provide additional technical clarification if needed
  - [ ] Prepare lab for patch testing
  - [ ] Test patches when released

- [ ] **Phase 4: Release Coordination (Day 30-90)**
  - [ ] Coordinate patch release timing with Fortinet
  - [ ] Notify government agencies if CRITICAL
  - [ ] Confirm patch effectiveness
  - [ ] Track industry adoption

- [ ] **Phase 5: Public Disclosure (Day 90+)**
  - [ ] Request CVE IDs from MITRE
  - [ ] Monitor NVD for CVE entries
  - [ ] Publish technical analysis
  - [ ] Update GitHub repository
  - [ ] Document findings in academic format (optional)

---

## Important Notes

### Embargo Compliance
- ⚠️ Do NOT discuss vulnerabilities publicly during 90-day embargo
- ⚠️ Do NOT post technical details on social media or forums
- ⚠️ Do NOT test vulnerabilities on external systems
- ⚠️ Do NOT share vulnerability details with unauthorized parties

### Government Coordination
- If CRITICAL vulnerabilities (CVSS ≥ 9.0), MUST notify CISA
- If Israeli infrastructure impact, notify National Cyber Directorate
- Use templates in EMERGENCY_CONTACTS.md for proper format
- Document all government communications

### Professional Communication
- Use professional email and technical documentation
- Include clear attribution to your research
- Acknowledge existing security research practices
- Maintain regular communication with Fortinet

### Public Disclosure
- ONLY disclose after patches are available
- Coordinate timing with Fortinet security advisory
- Provide proper CVE attribution
- Link to Fortinet's official advisory
- No exploitation details in public disclosures

---

## Success Metrics

✅ **Completed Successfully When:**
1. Initial notification sent and acknowledged within 48 hours
2. Technical details submitted by Day 7
3. Patches developed and tested by Day 30
4. Patches released publicly by Day 90
5. CVE IDs assigned and published
6. Public disclosure completed responsibly
7. All communications documented in coordination log
8. Fortinet/industry recognition received

---

## Contact & Support

**If you need additional guidance:**
- Review: cve-research/CVE-SUSPECTED-FORTIOS8-SSO/ZERODAY_PROTOCOL.md
- Review: cve-research/CVE-SUSPECTED-FORTIOS8-SSO/EMERGENCY_CONTACTS.md
- Consult: Industry vulnerability disclosure best practices
- Reference: CISA vulnerability coordination guidelines

**Key Contacts:**
- Fortinet Security: security@fortinet.com
- CISA (if critical): central@cisa.dhs.gov
- CVE Authority: https://cveform.mitre.org/

---

## Next Steps

1. **Wait for Fuzzing to Complete**
   - Monitor logs/fuzzing_session.log
   - Fuzzer will generate zero_day_report.json

2. **Run Triage Analysis**
   ```bash
   python3 CVE_TRIAGE_REPORT_GENERATOR.py
   ```

3. **Review Findings**
   ```bash
   cat CVE_TRIAGE_SUMMARY.md
   ```

4. **Prepare Contact**
   ```bash
   nano FORTINET_INITIAL_CONTACT.txt
   ```

5. **Send Notification**
   - Email to security@fortinet.com
   - Start 90-day coordination timeline

6. **Track Progress**
   - Update FORTINET_COORDINATION_LOG.md regularly
   - Maintain communication with Fortinet
   - Document all submissions and responses

---

**Last Updated:** [Date]
**Status:** Ready for Implementation
**Vulnerabilities Discovered:** 697+
**Next Milestone:** Fuzzing Completion → Triage Analysis → Fortinet Notification
