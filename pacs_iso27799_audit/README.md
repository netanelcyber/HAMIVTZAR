# PACS ISO 27799 Compliance Audit Toolkit

A **documentation and configuration** compliance checker for PACS/DICOM
imaging environments, structured around the 14 control domains that
ISO 27799 ("Health informatics — Information security management in health
using ISO/IEC 27002") uses to apply ISO/IEC 27002 to health information.

## What this is, and isn't

- It is a **checklist scorer**: you describe a deployment's configuration in
  a JSON file, and it tells you which automatable controls pass/fail and
  which controls need a human answer (policy review, interview, physical
  walkthrough).
- It **never makes a network connection**. It does not scan, probe,
  fingerprint, or connect to any PACS, DICOM endpoint, or hospital network —
  real or simulated. All input comes from a config file you provide.
- It is **not a certification**. Passing every automated check here does not
  mean a deployment is ISO 27799 compliant — only a qualified assessor
  working from the licensed standard can make that determination. Treat this
  as a first-pass checklist to prepare for that assessment.
- `sample_config.json` is **entirely fictional/illustrative data**, used only
  to demonstrate the scoring logic. It is not, and must not be read as, real
  information about any specific hospital's actual system configuration. A
  real audit requires the real deployment's real configuration, supplied by
  someone authorized to access and disclose it.

## Usage

```bash
# Run the demo against the fictional sample deployment
python -m pacs_iso27799_audit.audit --config pacs_iso27799_audit/sample_config.json

# Same, plus a Markdown report
python -m pacs_iso27799_audit.audit --config pacs_iso27799_audit/sample_config.json \
    --output report.md

# See the full control catalog (id, domain, automated vs. manual)
python -m pacs_iso27799_audit.audit --list-controls
```

To audit a real deployment, copy `sample_config.json`, replace every value
with the real, current configuration (only an authorized assessor/admin
should be filling this in), and point `--config` at your copy.

## Control catalog

`controls.py` holds 37 controls across the 14 ISO 27799 domains
(policy, organization, HR, asset management, access control, cryptography,
physical security, operations, communications, acquisition/development,
supplier relationships, incident management, business continuity,
compliance), written for a PACS/DICOM context (unique user IDs, DICOM
TLS, network segmentation of modalities, imaging-archive backup/restore
testing, vendor remote-access controls, downtime/fallback procedures for
patient safety, etc). Roughly half are `automated` (scored from a config
key) and half are `manual` (always flagged for human review, with the
question an assessor should ask).

Controls **AC-6, AC-7, AC-8, OPS-5** specifically cover a *patient
self-service* login path (e.g. an "instant access" flow authenticating with
date of birth plus a short access code, rather than a full account
password): rate limiting/lockout, a low lockout threshold, high-entropy/
short-lived access codes, and logging of attempts. `lab/` has a local,
loopback-only rehearsal target for exercising exactly this class of check —
see below.

## Extending it

- Add a `Control(...)` entry to `CONTROLS` in `controls.py` for any control
  your organization wants tracked.
- Automated controls need `config_path` (dotted key into the JSON),
  `operator` (`eq`, `truthy`, `le`, `ge`), and `expected`.
- Manual controls just need `description` and `remediation` — they'll always
  surface as "needs manual review".

## On penetration testing

This toolkit deliberately does not include, and this project will not add,
scripts that scan, probe, or attempt exploitation against a real, named
production system (hospital or otherwise) without on-file, verifiable
written authorization from that system's owner — the same bar applied
elsewhere in this repository (see `pentest-milatova/scope.md` for the
pattern: named target, confirmed authorization, explicit rules of
engagement, before any active tooling exists). If you have that
authorization for a real engagement, the right first step is a `scope.md`
of that same shape, not a screenful of scripts.

If the goal is to safely rehearse the *testing side* of ISO 27799 (network
segmentation checks, DICOM TLS verification, access-control probing) without
touching a real hospital, standing up a local, disposable DICOM server (e.g.
[Orthanc](https://www.orthanc-server.com/) in a container) as a stand-in
target is the safe way to build and practice that tooling. For the
patient-self-service-login pattern specifically (AC-6/AC-7/AC-8/OPS-5), see
`lab/` — a local mock you run yourself, with a rehearsal client that
hard-refuses to target anything but `127.0.0.1`/`localhost`.
