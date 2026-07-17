"""Control catalog: ISO 27799-aligned checks for PACS / DICOM environments.

ISO 27799 ("Health informatics -- Information security management in health
using ISO/IEC 27002") gives sector-specific guidance for applying the 14
ISO/IEC 27002:2013 control clauses to health information. The domain numbers
and names below follow that base clause structure; the control text itself is
written for this project, in plain language, for a PACS/DICOM imaging
context -- it is not a reproduction of the standard's copyrighted text.
Treat this catalog as a starting checklist, not a certification: a real
ISO 27799 assessment should reference the licensed standard directly and be
carried out (or reviewed) by a qualified auditor.

Each control is either:
  - "automated": scored from a key in the deployment's JSON config file.
  - "manual": a documentation/process/physical-security item that can't be
    verified from a config file -- it is always reported as "needs manual
    review" together with the question an assessor should ask.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

DOMAINS = {
    5: "Information security policies",
    6: "Organization of information security",
    7: "Human resource security",
    8: "Asset management",
    9: "Access control",
    10: "Cryptography",
    11: "Physical and environmental security",
    12: "Operations security",
    13: "Communications security",
    14: "System acquisition, development and maintenance",
    15: "Supplier relationships",
    16: "Information security incident management",
    17: "Information security aspects of business continuity management",
    18: "Compliance",
}


@dataclass(frozen=True)
class Control:
    id: str
    domain: int
    title: str
    description: str
    check_type: str  # "automated" | "manual"
    severity: str  # "high" | "medium" | "low"
    remediation: str
    config_path: Optional[str] = None  # dotted path into the config JSON
    operator: Optional[str] = None  # "eq" | "le" | "ge" | "truthy"
    expected: Any = None

    @property
    def domain_name(self) -> str:
        return DOMAINS[self.domain]


CONTROLS: List[Control] = [
    Control(
        id="POL-1", domain=5,
        title="Documented health-information security policy",
        description="A written information security policy exists that explicitly covers "
                    "patient imaging data handled by the PACS/DICOM environment.",
        check_type="manual", severity="high",
        remediation="Adopt and publish a security policy that names PACS/imaging data "
                    "in scope, approved by senior management and the privacy/security officer.",
    ),
    Control(
        id="POL-2", domain=5,
        title="Policy reviewed on a defined schedule",
        description="The security policy is reviewed at least annually and after any "
                    "significant incident or system change.",
        check_type="manual", severity="medium",
        remediation="Set a recurring policy-review date and re-review after major "
                    "incidents, audits, or PACS upgrades.",
    ),
    Control(
        id="ORG-1", domain=6,
        title="Named information security / privacy responsibility",
        description="A specific role (CISO, privacy officer, or equivalent) is "
                    "accountable for the security of the imaging environment.",
        check_type="manual", severity="high",
        remediation="Assign and document ownership of PACS security to a named role.",
    ),
    Control(
        id="ORG-2", domain=6,
        title="Segregation of administrative and clinical duties",
        description="PACS system-administration accounts are separate from clinical "
                    "viewing/reporting accounts, so no single account holds both roles.",
        check_type="automated", severity="medium",
        config_path="access_control.admin_accounts_segregated", operator="truthy",
        expected=True,
        remediation="Split administrative and clinical roles into distinct accounts "
                    "with distinct privilege sets.",
    ),
    Control(
        id="HR-1", domain=7,
        title="Confidentiality commitments for PACS users",
        description="Staff with PACS access sign confidentiality/acceptable-use "
                    "agreements before access is granted.",
        check_type="manual", severity="medium",
        remediation="Require a signed confidentiality agreement as a precondition of "
                    "account provisioning.",
    ),
    Control(
        id="HR-2", domain=7,
        title="Security awareness training coverage",
        description="Staff with PACS access complete recurring security/privacy "
                    "awareness training.",
        check_type="automated", severity="medium",
        config_path="human_resources.training_completion_rate_pct", operator="ge",
        expected=90,
        remediation="Track training completion and follow up on staff below the "
                    "organization's target completion rate.",
    ),
    Control(
        id="AM-1", domain=8,
        title="Asset inventory of PACS components",
        description="An up-to-date inventory exists of PACS servers, workstations, and "
                    "modality DICOM AE titles connected to the network.",
        check_type="manual", severity="medium",
        remediation="Maintain an asset register covering every PACS server, viewing "
                    "workstation, and modality endpoint.",
    ),
    Control(
        id="AM-2", domain=8,
        title="Imaging media handling and disposal procedure",
        description="A documented procedure governs handling and secure disposal of "
                    "imaging media (CDs/USB exports, retired disks).",
        check_type="manual", severity="low",
        remediation="Document secure-disposal and media-handling procedures for exported "
                    "studies and decommissioned storage.",
    ),
    Control(
        id="AC-1", domain=9,
        title="Unique user identification",
        description="Every clinical and administrative user authenticates with a unique "
                    "account; no shared or generic logins are permitted.",
        check_type="automated", severity="high",
        config_path="access_control.shared_accounts_allowed", operator="eq",
        expected=False,
        remediation="Disable shared/generic accounts; provision one account per person.",
    ),
    Control(
        id="AC-2", domain=9,
        title="Role-based access control",
        description="Access to studies and administrative functions is restricted by "
                    "role, following least privilege.",
        check_type="automated", severity="high",
        config_path="access_control.rbac_enabled", operator="truthy", expected=True,
        remediation="Enable and configure role-based access profiles for clinical, "
                    "radiology, and admin roles.",
    ),
    Control(
        id="AC-3", domain=9,
        title="Strong authentication for remote access",
        description="Remote/VPN access to the PACS environment requires multi-factor "
                    "authentication.",
        check_type="automated", severity="high",
        config_path="access_control.mfa_required_for_remote", operator="truthy",
        expected=True,
        remediation="Require MFA for any remote-access path into the PACS network.",
    ),
    Control(
        id="AC-4", domain=9,
        title="Session inactivity timeout",
        description="Clinical viewing workstations automatically lock or log off after "
                    "a bounded idle period.",
        check_type="automated", severity="medium",
        config_path="access_control.session_idle_timeout_minutes", operator="le",
        expected=15,
        remediation="Configure auto-lock/logoff at or below the organization's approved "
                    "idle-timeout threshold.",
    ),
    Control(
        id="AC-5", domain=9,
        title="Password strength policy",
        description="Account passwords meet a documented minimum length/complexity "
                    "standard.",
        check_type="automated", severity="medium",
        config_path="access_control.password_min_length", operator="ge", expected=12,
        remediation="Enforce a minimum password length/complexity in the identity "
                    "provider or PACS auth module.",
    ),
    Control(
        id="AC-6", domain=9,
        title="Rate limiting / lockout on patient self-service login",
        description="A patient-facing self-service login path (e.g. an 'instant "
                    "access' flow authenticating with something like date of birth "
                    "plus a short access code, rather than a full account password) "
                    "enforces rate limiting and temporary lockout after repeated "
                    "failed attempts, so it cannot be enumerated or brute-forced.",
        check_type="automated", severity="high",
        config_path="access_control.instant_access_rate_limited", operator="truthy",
        expected=True,
        remediation="Add rate limiting and progressive/temporary lockout (plus a "
                    "CAPTCHA or equivalent bot-mitigation) to any patient "
                    "self-service login path that uses low-entropy or partially "
                    "guessable identifiers.",
    ),
    Control(
        id="AC-7", domain=9,
        title="Lockout threshold for patient self-service login",
        description="The failed-attempt threshold before a patient self-service "
                    "login is temporarily locked is low enough to make brute-force "
                    "impractical.",
        check_type="automated", severity="medium",
        config_path="access_control.instant_access_lockout_threshold", operator="le",
        expected=5,
        remediation="Lower the failed-attempt threshold and add an increasing "
                    "backoff/lockout window rather than a fixed short delay.",
    ),
    Control(
        id="AC-8", domain=9,
        title="Access-code entropy and expiry for patient self-service login",
        description="Any secondary code used in a patient self-service login "
                    "(access code, one-time link, etc.) is high-entropy, single-use "
                    "or short-lived, and not derivable from information that is "
                    "otherwise public or easily guessable about the patient.",
        check_type="manual", severity="high",
        remediation="Review how the access code is generated and delivered; replace "
                    "short numeric codes with longer random tokens or one-time links "
                    "with a short expiry, delivered out-of-band (e.g. SMS/email the "
                    "patient already controls).",
    ),
    Control(
        id="CR-1", domain=10,
        title="Encryption of DICOM traffic in transit",
        description="DICOM associations and web/API traffic to and from the PACS are "
                    "encrypted (TLS).",
        check_type="automated", severity="high",
        config_path="cryptography.dicom_tls_enabled", operator="truthy", expected=True,
        remediation="Enable TLS on DICOM associations and any HTTP(S)/API interfaces.",
    ),
    Control(
        id="CR-2", domain=10,
        title="Encryption of imaging data at rest",
        description="Stored studies on the archive/storage tier are encrypted at rest.",
        check_type="automated", severity="high",
        config_path="cryptography.storage_encryption_at_rest", operator="truthy",
        expected=True,
        remediation="Enable storage-level or filesystem-level encryption for the image "
                    "archive.",
    ),
    Control(
        id="PHY-1", domain=11,
        title="Restricted, logged physical access to PACS server room",
        description="Physical access to rooms housing PACS servers/archive is "
                    "restricted to authorized personnel and logged.",
        check_type="manual", severity="medium",
        remediation="Use badge/key-controlled access with a physical access log for "
                    "server rooms.",
    ),
    Control(
        id="PHY-2", domain=11,
        title="Environmental protection for the imaging archive",
        description="The imaging archive environment has UPS, fire suppression, and "
                    "climate control appropriate to a clinical data center.",
        check_type="manual", severity="low",
        remediation="Verify UPS runtime, fire suppression, and climate control are in "
                    "place and tested.",
    ),
    Control(
        id="OPS-1", domain=12,
        title="Access logging for image view/export events",
        description="Every access, view, and export of a patient study is logged with "
                    "user identity and timestamp, retained per the organization's "
                    "record-retention policy.",
        check_type="automated", severity="high",
        config_path="operations.access_logging_enabled", operator="truthy",
        expected=True,
        remediation="Enable comprehensive audit logging and confirm retention matches "
                    "the organization's legal/record-retention requirement.",
    ),
    Control(
        id="OPS-2", domain=12,
        title="Endpoint protection on PACS hosts",
        description="Anti-malware/endpoint protection is deployed on PACS servers and "
                    "viewing workstations.",
        check_type="automated", severity="medium",
        config_path="operations.endpoint_protection_enabled", operator="truthy",
        expected=True,
        remediation="Deploy and centrally monitor endpoint protection compatible with "
                    "the PACS vendor's support requirements.",
    ),
    Control(
        id="OPS-3", domain=12,
        title="Patch currency",
        description="The PACS OS and application stack are patched within a bounded "
                    "window of vendor release.",
        check_type="automated", severity="high",
        config_path="operations.os_patch_days_behind", operator="le", expected=30,
        remediation="Establish a patch cadence and reduce the gap between vendor "
                    "release and deployment.",
    ),
    Control(
        id="OPS-5", domain=12,
        title="Logging of patient self-service login attempts",
        description="Both successful and failed attempts on the patient "
                    "self-service login path are logged with enough detail "
                    "(timestamp, source, target identifier) to detect an "
                    "enumeration or brute-force attempt in progress.",
        check_type="automated", severity="high",
        config_path="operations.instant_access_attempts_logged", operator="truthy",
        expected=True,
        remediation="Log every self-service login attempt (not just successes) and "
                    "alert on abnormal failure volume against a single identifier or "
                    "from a single source.",
    ),
    Control(
        id="OPS-4", domain=12,
        title="Change management for PACS configuration",
        description="Configuration changes to the PACS follow a documented "
                    "change-management/approval process.",
        check_type="manual", severity="medium",
        remediation="Route PACS configuration changes through a change-advisory "
                    "process with rollback planning.",
    ),
    Control(
        id="COM-1", domain=13,
        title="Network segmentation",
        description="The PACS/DICOM network segment is isolated (VLAN/firewall) from "
                    "the general hospital network and guest/IoT segments.",
        check_type="automated", severity="high",
        config_path="communications.network_segmented", operator="truthy",
        expected=True,
        remediation="Place PACS and modalities on a dedicated, firewalled VLAN.",
    ),
    Control(
        id="COM-2", domain=13,
        title="Restricted DICOM port exposure",
        description="Firewall rules restrict DICOM ports (e.g. 104/11112) and any "
                    "management interfaces to explicitly authorized hosts.",
        check_type="manual", severity="high",
        remediation="Review firewall rulesets and remove any broad/any-source allow "
                    "rules for DICOM or management ports.",
    ),
    Control(
        id="DEV-1", domain=14,
        title="Vendor security-patch SLA",
        description="Security patches released by the PACS vendor are applied within a "
                    "defined SLA.",
        check_type="automated", severity="medium",
        config_path="acquisition.vendor_patch_sla_days", operator="le", expected=90,
        remediation="Negotiate and track a patch-application SLA with the PACS vendor.",
    ),
    Control(
        id="DEV-2", domain=14,
        title="Pre-production security testing of upgrades",
        description="PACS upgrades and configuration changes are security-tested in a "
                    "non-production environment before deployment.",
        check_type="manual", severity="medium",
        remediation="Stand up a staging environment and require sign-off before "
                    "production PACS upgrades.",
    ),
    Control(
        id="SUP-1", domain=15,
        title="Data-processing agreement with the PACS vendor",
        description="A contractual agreement with the vendor covers confidentiality, "
                    "breach notification, and data-handling obligations for patient "
                    "imaging data.",
        check_type="manual", severity="high",
        remediation="Put a data-processing/BAA-equivalent agreement in place with the "
                    "vendor before go-live.",
    ),
    Control(
        id="SUP-2", domain=15,
        title="Time-limited, logged vendor remote support",
        description="Remote-support access used by the vendor is time-boxed, requires "
                    "explicit activation, and is logged.",
        check_type="automated", severity="medium",
        config_path="acquisition.vendor_remote_access_time_limited", operator="truthy",
        expected=True,
        remediation="Require vendor remote sessions to be requested, time-limited, and "
                    "logged rather than left permanently open.",
    ),
    Control(
        id="INC-1", domain=16,
        title="Incident response plan covering imaging data",
        description="A documented incident-response plan explicitly addresses a "
                    "breach or outage involving the PACS/imaging data.",
        check_type="manual", severity="high",
        remediation="Extend or write an incident-response plan naming PACS/imaging "
                    "data scenarios and escalation paths.",
    ),
    Control(
        id="INC-2", domain=16,
        title="Regulatory breach-notification timeline",
        description="The incident process meets the applicable jurisdiction's "
                    "breach-notification deadlines for health data.",
        check_type="manual", severity="high",
        remediation="Confirm the incident process's notification timeline against "
                    "applicable national health-data-protection law.",
    ),
    Control(
        id="BC-1", domain=17,
        title="Backups with tested restore",
        description="The imaging archive is backed up on a defined schedule and "
                    "restore has been tested recently.",
        check_type="automated", severity="high",
        config_path="business_continuity.backup_restore_tested_days_ago", operator="le",
        expected=90,
        remediation="Schedule regular backups and periodically test full restore, not "
                    "just backup completion.",
    ),
    Control(
        id="BC-2", domain=17,
        title="Documented PACS downtime procedure",
        description="A patient-safety-focused downtime procedure exists for when PACS "
                    "is unavailable (e.g. fallback viewing/reporting path).",
        check_type="manual", severity="high",
        remediation="Document and drill a clinical downtime procedure so imaging "
                    "remains accessible during an outage.",
    ),
    Control(
        id="CMP-1", domain=18,
        title="Compliance with applicable health-data-protection law",
        description="The PACS deployment has been reviewed against applicable national "
                    "health-data and privacy law.",
        check_type="manual", severity="high",
        remediation="Have legal/compliance review the deployment against applicable "
                    "national health-data-protection and privacy legislation.",
    ),
    Control(
        id="CMP-2", domain=18,
        title="Independent security risk assessment cadence",
        description="An independent security risk assessment of the PACS environment "
                    "has been performed within the last year.",
        check_type="automated", severity="medium",
        config_path="compliance.last_risk_assessment_days_ago", operator="le",
        expected=365,
        remediation="Commission an independent risk assessment at least annually.",
    ),
]
