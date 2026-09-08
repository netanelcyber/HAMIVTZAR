#!/usr/bin/env python3
"""
Automated Email Sender for Fortinet CVE Submission
Sends complete vulnerability disclosure email to Fortinet PSIRT
"""

import smtplib
import os
import sys
import getpass
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path

# Configuration
SENDER_EMAIL = "nsh531@gmail.com"
GMAIL_SMTP_SERVER = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587

RECIPIENT_EMAILS = [
    "security@fortinet.com",
]
CC_EMAILS = [
    "psirt@fortinet.com",
]

# Email Details
EMAIL_SUBJECT = "Coordinated Vulnerability Disclosure - FortiOS 8.0.0 (9,360+ Vulnerabilities Discovered - CRITICAL Infrastructure Risk)"

# Files to attach
FILES_TO_ATTACH = [
    "FORTINET_CVE_SUBMISSION/FINAL_TESTING_REPORT.pdf",
    "FORTINET_CVE_SUBMISSION/README_SUBMISSION_PACKAGE.md",
    "FORTINET_CVE_SUBMISSION/CVE_SUBMISSION_REPORT.pdf",
    "FORTINET_CVE_SUBMISSION/analysis/VULNERABILITY_ANALYSIS_FORMAT_STRING.md",
    "FORTINET_CVE_SUBMISSION/analysis/EXPLOITATION_ESCALATION_CHAINS.md",
    "FORTINET_CVE_SUBMISSION/analysis/PERSISTENCE_AND_BACKDOOR_INSTALLATION.md",
    "FORTINET_CVE_SUBMISSION/analysis/COMPLETE_EXPLOITATION_CHAIN_VERIFICATION.md",
    "FORTINET_CVE_SUBMISSION/poc/POC_EXPLOIT_PACK.py",
    "FORTINET_CVE_SUBMISSION/testing/POC_TESTING_GUIDE.md",
    "FORTINET_CVE_SUBMISSION/CVE_REPORTING_GUIDE.md",
]

def read_email_body():
    """Read email body from EMAIL_TO_FORTINET_PSIRT.txt"""
    email_file = "FORTINET_CVE_SUBMISSION/EMAIL_TO_FORTINET_PSIRT.txt"

    if not os.path.exists(email_file):
        print(f"❌ Error: {email_file} not found!")
        sys.exit(1)

    with open(email_file, 'r') as f:
        content = f.read()

    # Extract body (skip TO, CC, SUBJECT lines)
    lines = content.split('\n')
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith('---') and i > 0:
            body_start = i + 1
            break

    body = '\n'.join(lines[body_start:])
    return body.strip()

def get_gmail_password():
    """Securely get Gmail password from user"""
    print("\n" + "="*60)
    print("SECURE PASSWORD ENTRY")
    print("="*60)
    print(f"\nYou will be prompted to enter your Gmail password.")
    print("⚠️  Password will NOT be displayed on screen for security.")
    print("⚠️  Password will NOT be saved anywhere.")
    print(f"\nEmail: {SENDER_EMAIL}")
    print("\n" + "-"*60)

    password = getpass.getpass("\nEnter your Gmail password (or App Password): ")

    if not password:
        print("\n❌ Error: Password cannot be empty!")
        sys.exit(1)

    return password

def create_email_message():
    """Create email message with attachments"""

    print("\n[*] Reading email body...")
    body = read_email_body()

    # Create message
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = ', '.join(RECIPIENT_EMAILS)
    msg['Cc'] = ', '.join(CC_EMAILS)
    msg['Subject'] = EMAIL_SUBJECT
    msg['Date'] = formatdate(localtime=True)

    # Add body
    print("[*] Adding email body...")
    msg.attach(MIMEText(body, 'plain'))

    # Add attachments
    print("\n[*] Attaching files...")
    attachment_count = 0

    for file_path in FILES_TO_ATTACH:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())

                from email import encoders
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(file_path)}')
                msg.attach(part)
                print(f"    ✓ {file_path}")
                attachment_count += 1
            except Exception as e:
                print(f"    ⚠️  Warning: Could not attach {file_path}: {e}")
        else:
            print(f"    ⚠️  Warning: File not found: {file_path}")

    print(f"\n✓ Successfully added {attachment_count} attachments")

    return msg

def send_email(msg, password):
    """Send email via Gmail SMTP"""

    print("\n" + "="*60)
    print("SENDING EMAIL")
    print("="*60)

    all_recipients = RECIPIENT_EMAILS + CC_EMAILS

    try:
        print(f"\n[*] Connecting to {GMAIL_SMTP_SERVER}:{GMAIL_SMTP_PORT}...")

        # Create SMTP session
        server = smtplib.SMTP(GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT)
        server.starttls()  # Secure connection

        print("[*] Authenticating with Gmail...")
        server.login(SENDER_EMAIL, password)

        print(f"[*] Sending email to:")
        for email in RECIPIENT_EMAILS:
            print(f"    → {email}")
        for email in CC_EMAILS:
            print(f"    → {email} (CC)")

        # Send email
        server.send_message(msg)

        server.quit()

        print("\n" + "="*60)
        print("✅ EMAIL SENT SUCCESSFULLY!")
        print("="*60)

        return True

    except smtplib.SMTPAuthenticationError:
        print("\n❌ Error: Authentication failed!")
        print("   Check your Gmail password or enable 'Less secure app access'")
        print("   Or use a Gmail App Password instead")
        return False
    except smtplib.SMTPException as e:
        print(f"\n❌ SMTP Error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def log_submission():
    """Log submission in FORTINET_COORDINATION_LOG.md"""
    from datetime import datetime

    log_file = "FORTINET_CVE_SUBMISSION/FORTINET_COORDINATION_LOG.md"

    if os.path.exists(log_file):
        with open(log_file, 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n## Submission Sent\n\n")
            f.write(f"**Date:** {timestamp}\n")
            f.write(f"**From:** {SENDER_EMAIL}\n")
            f.write(f"**To:** {', '.join(RECIPIENT_EMAILS)}\n")
            f.write(f"**CC:** {', '.join(CC_EMAILS)}\n")
            f.write(f"**Subject:** {EMAIL_SUBJECT}\n")
            f.write(f"**Status:** SENT\n")
            f.write(f"**Expected Response:** Within 48 hours\n\n")

        print(f"[*] Updated {log_file}")

def main():
    """Main function"""

    print("\n" + "="*60)
    print("FORTINET CVE SUBMISSION - AUTOMATED EMAIL SENDER")
    print("="*60)

    print(f"\nSending from: {SENDER_EMAIL}")
    print(f"Recipients: {', '.join(RECIPIENT_EMAILS)}")
    print(f"CC: {', '.join(CC_EMAILS)}")

    print(f"\nSubject: {EMAIL_SUBJECT}")

    # Verify email body file exists
    if not os.path.exists("FORTINET_CVE_SUBMISSION/EMAIL_TO_FORTINET_PSIRT.txt"):
        print("\n❌ Error: EMAIL_TO_FORTINET_PSIRT.txt not found!")
        sys.exit(1)

    # Get password
    password = get_gmail_password()

    # Create email
    print("\n[*] Creating email message...")
    msg = create_email_message()

    # Confirm before sending
    print("\n" + "="*60)
    print("CONFIRMATION")
    print("="*60)
    print(f"\nEmail Summary:")
    print(f"  From: {SENDER_EMAIL}")
    print(f"  To: {', '.join(RECIPIENT_EMAILS)}")
    print(f"  CC: {', '.join(CC_EMAILS)}")
    print(f"  Subject: {EMAIL_SUBJECT[:50]}...")
    print(f"  Attachments: {len(FILES_TO_ATTACH)} files")

    confirm = input("\nSend this email? (yes/no): ").lower().strip()

    if confirm != 'yes':
        print("\n❌ Email sending cancelled.")
        sys.exit(0)

    # Send email
    success = send_email(msg, password)

    if success:
        # Log submission
        log_submission()

        print("\n" + "="*60)
        print("NEXT STEPS")
        print("="*60)
        print("\n1. Watch for Fortinet acknowledgment (48-hour SLA)")
        print("2. Check FORTINET_COORDINATION_LOG.md for tracking")
        print("3. Prepare for technical submission (Day 2-7)")
        print("4. Set reminder for 48-hour follow-up")
        print("\n" + "="*60)
    else:
        print("\n⚠️  Email send failed. Please check your credentials.")
        print("   Consider using a Gmail App Password instead of your account password.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Email sending cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
