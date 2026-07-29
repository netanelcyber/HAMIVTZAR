# Automated Email Sender - Quick Start Guide

## 🚀 One-Command Email Sending

Your email to Fortinet can now be sent **automatically** with a single command!

---

## ⚙️ How It Works

The script (`send_email_automated.py`) will:

1. ✅ Read your email body from `EMAIL_TO_FORTINET_PSIRT.txt`
2. ✅ Attach all 10 technical documents automatically
3. ✅ Connect securely to Gmail SMTP server
4. ✅ Ask for your password (not stored anywhere)
5. ✅ Send email to Fortinet PSIRT team
6. ✅ Update `FORTINET_COORDINATION_LOG.md` with submission timestamp

---

## 🔐 Security Notes

**Your password:**
- ✅ Asked in real-time (NOT stored in files)
- ✅ Hidden on screen during entry
- ✅ Only used to authenticate with Gmail
- ✅ Discarded after email is sent

**Recommended:** Use Gmail App Password instead of account password
- More secure
- Can be revoked independently
- Better for automation

---

## 📋 Prerequisites

Before running the script:

```bash
✓ Have nsh531@gmail.com Gmail account ready
✓ Know your Gmail password OR App Password
✓ Have internet connection
✓ Be in the FORTINET_CVE_SUBMISSION directory
```

---

## 🎯 Quick Start (3 Steps)

### Step 1: Navigate to Folder

```bash
cd /home/user/HAMIVTZAR/FORTINET_CVE_SUBMISSION
```

### Step 2: Run the Script

```bash
python3 send_email_automated.py
```

### Step 3: Follow Prompts

- **Review email details** - Check sender, recipients, subject
- **Enter Gmail password** - Hidden input for security
- **Confirm sending** - Type "yes" to send
- **Wait for confirmation** - Email sends in ~10-30 seconds

---

## 📝 What Gets Sent

**Email To:**
- security@fortinet.com (primary)
- CC: psirt@fortinet.com (PSIRT team)

**Attachments (10 files):**
```
1. FINAL_TESTING_REPORT.pdf ..................... Complete testing results
2. README_SUBMISSION_PACKAGE.md ................. Package overview
3. CVE_SUBMISSION_REPORT.pdf .................... Executive summary
4. VULNERABILITY_ANALYSIS_FORMAT_STRING.md ...... Deep technical analysis
5. EXPLOITATION_ESCALATION_CHAINS.md ........... Attack chains & RCE
6. PERSISTENCE_AND_BACKDOOR_INSTALLATION.md ... Post-exploitation
7. COMPLETE_EXPLOITATION_CHAIN_VERIFICATION.md  End-to-end verification
8. POC_EXPLOIT_PACK.py .......................... Executable test code
9. POC_TESTING_GUIDE.md ......................... Testing procedures
10. CVE_REPORTING_GUIDE.md ....................... 90-day timeline
```

---

## ✅ Step-by-Step Walkthrough

### When You Run the Script:

```
==============================================================
FORTINET CVE SUBMISSION - AUTOMATED EMAIL SENDER
==============================================================

Sending from: nsh531@gmail.com
Recipients: security@fortinet.com
CC: psirt@fortinet.com

Subject: Coordinated Vulnerability Disclosure - FortiOS 8.0.0...

==============================================================
SECURE PASSWORD ENTRY
==============================================================

You will be prompted to enter your Gmail password.
⚠️  Password will NOT be displayed on screen for security.
⚠️  Password will NOT be saved anywhere.

Email: nsh531@gmail.com

------------------------------------------------------------

Enter your Gmail password (or App Password): [hidden input]

[*] Reading email body...
[*] Adding email body...

[*] Attaching files...
    ✓ FORTINET_CVE_SUBMISSION/FINAL_TESTING_REPORT.pdf
    ✓ FORTINET_CVE_SUBMISSION/README_SUBMISSION_PACKAGE.md
    ✓ FORTINET_CVE_SUBMISSION/CVE_SUBMISSION_REPORT.pdf
    ✓ FORTINET_CVE_SUBMISSION/analysis/VULNERABILITY_ANALYSIS_FORMAT_STRING.md
    ✓ FORTINET_CVE_SUBMISSION/analysis/EXPLOITATION_ESCALATION_CHAINS.md
    ✓ FORTINET_CVE_SUBMISSION/analysis/PERSISTENCE_AND_BACKDOOR_INSTALLATION.md
    ✓ FORTINET_CVE_SUBMISSION/analysis/COMPLETE_EXPLOITATION_CHAIN_VERIFICATION.md
    ✓ FORTINET_CVE_SUBMISSION/poc/POC_EXPLOIT_PACK.py
    ✓ FORTINET_CVE_SUBMISSION/testing/POC_TESTING_GUIDE.md
    ✓ FORTINET_CVE_SUBMISSION/CVE_REPORTING_GUIDE.md

✓ Successfully added 10 attachments

==============================================================
CONFIRMATION
==============================================================

Email Summary:
  From: nsh531@gmail.com
  To: security@fortinet.com
  CC: psirt@fortinet.com
  Subject: Coordinated Vulnerability Disclosure - FortiOS 8.0.0...
  Attachments: 10 files

Send this email? (yes/no): yes

==============================================================
SENDING EMAIL
==============================================================

[*] Connecting to smtp.gmail.com:587...
[*] Authenticating with Gmail...
[*] Sending email to:
    → security@fortinet.com
    → psirt@fortinet.com (CC)

==============================================================
✅ EMAIL SENT SUCCESSFULLY!
==============================================================

[*] Updated FORTINET_COORDINATION_LOG.md

==============================================================
NEXT STEPS
==============================================================

1. Watch for Fortinet acknowledgment (48-hour SLA)
2. Check FORTINET_COORDINATION_LOG.md for tracking
3. Prepare for technical submission (Day 2-7)
4. Set reminder for 48-hour follow-up

==============================================================
```

---

## 🔧 Troubleshooting

### ❌ "Authentication failed"

**Solution:** Check your Gmail credentials
- Verify correct email: nsh531@gmail.com
- Verify correct password
- **Better:** Use Gmail App Password instead

### How to Create Gmail App Password:

1. Go to: https://myaccount.google.com/security
2. Enable 2-Step Verification (if not already enabled)
3. Find "App passwords" option
4. Generate password for "Mail" + "Windows Computer"
5. Use this 16-character password instead of account password

### ❌ "Connection error"

**Solution:** Check internet connection
- Verify WiFi/network is working
- Try again in a few seconds
- Gmail SMTP might be temporarily down (rare)

### ❌ "File not found"

**Solution:** Ensure you're in the right directory
```bash
cd /home/user/HAMIVTZAR/FORTINET_CVE_SUBMISSION
ls -la send_email_automated.py
```

---

## 📊 After Email Sent

### Check Submission Log:

```bash
cat FORTINET_COORDINATION_LOG.md
```

You should see entry like:
```
## Submission Sent

**Date:** 2026-07-29 14:32:15
**From:** nsh531@gmail.com
**To:** security@fortinet.com
**CC:** psirt@fortinet.com
**Status:** SENT
**Expected Response:** Within 48 hours
```

### Set 48-Hour Reminder:

```bash
# In 48 hours, check for response:
# 1. Check email for Fortinet reply
# 2. If no response, send follow-up email
# 3. If still no response by Day 3, escalate to CISA/INCD
```

---

## 🎯 Complete Timeline

```
NOW:        Run send_email_automated.py → Email sent ✓
+2 hours:   First Fortinet response expected
+24 hours:  Follow up if no response yet
+48 hours:  If no response, escalate to CISA
Day 2-7:    Fortinet requests technical details
Day 7-30:   Patch development by Fortinet
Day 30-90:  Emergency patches released
Day 90+:    Public disclosure + CVE assignment
```

---

## ✅ Success Criteria

✓ Email delivered to security@fortinet.com  
✓ All 10 attachments included  
✓ Submission logged in FORTINET_COORDINATION_LOG.md  
✓ Script shows "EMAIL SENT SUCCESSFULLY!"  
✓ No errors during execution  

---

## 🚀 Ready to Send!

```bash
cd /home/user/HAMIVTZAR/FORTINET_CVE_SUBMISSION
python3 send_email_automated.py
```

Type "yes" when prompted and your email will be sent to Fortinet PSIRT!

---

**Questions?** All technical details are in EMAIL_TO_FORTINET_PSIRT.txt
