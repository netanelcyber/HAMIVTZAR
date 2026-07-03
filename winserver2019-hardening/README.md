# Windows Server 2019 — Common Vulnerabilities & Hardening

Defensive hardening kit for **Windows Server 2019**: a catalogue of the
misconfigurations/CVEs most commonly found on unhardened Server 2019 boxes
(the same issues internal pentests and ransomware crews look for first),
plus two PowerShell scripts to check for them and fix them.

> Run this **only on servers you own or are authorized to change**. `Harden.ps1`
> modifies registry keys, services, and security policy — read the findings
> below and the inline comments before applying anything in production, and
> test in a maintenance window / on a snapshot first.

## Layout

- `FINDINGS.md` — one entry per vulnerability class: description, impact,
  how it's detected, and the remediation applied.
- `scripts/Audit-WinServer2019.ps1` — **read-only**. Checks the current state
  of every item in `FINDINGS.md` and prints a PASS/FAIL report. Safe to run
  anywhere, no changes are made.
- `scripts/Harden-WinServer2019.ps1` — applies the fixes. Defaults to
  `-WhatIf`-style dry run (prints what it *would* do); pass `-Apply` to
  actually change anything. Each check can be skipped individually.
- `output/` — audit reports land here (gitignored).

## Usage

On the target server, in an elevated PowerShell session:

```powershell
# 1. See where the box currently stands (no changes made)
.\scripts\Audit-WinServer2019.ps1 -ReportPath .\output\audit-report.txt

# 2. Dry run of the fixes (prints planned actions, changes nothing)
.\scripts\Harden-WinServer2019.ps1

# 3. Apply the fixes (reboot required afterwards for some items, e.g. SMBv1/LSA)
.\scripts\Harden-WinServer2019.ps1 -Apply

# Re-run the audit to confirm
.\scripts\Audit-WinServer2019.ps1 -ReportPath .\output\audit-report-after.txt
```

Individual checks can be excluded, e.g. to leave the Print Spooler alone on a
print server:

```powershell
.\scripts\Harden-WinServer2019.ps1 -Apply -Skip PrintSpooler
```

## Scope

These are baseline, generally-safe hardening items aligned with CIS
Benchmark for Windows Server 2019 and Microsoft's own guidance for
SMBv1/PrintNightmare/Zerologon/BlueKeep-class issues. It is **not** a full
CIS/STIG implementation and does not replace patch management — apply
Windows Updates regardless, since several of the CVEs referenced below
(BlueKeep, Zerologon, PrintNightmare) are ultimately fixed by security
updates and the registry/service mitigations here are defense-in-depth,
not a substitute for patching.

See [`FINDINGS.md`](FINDINGS.md) for the full list.
