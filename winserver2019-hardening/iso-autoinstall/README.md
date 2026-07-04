# Auto-harden on install (ISO injection)

Bakes `../scripts/Harden-WinServer2019.ps1` into a Windows Server 2019
installation ISO so hardening runs **automatically at the end of setup**,
before anyone logs on — no manual step after install.

## How it works

Two independent Windows Setup mechanisms, both triggered by files placed on
the installation media:

1. **`autounattend.xml`** (optional) — answer file at the ISO root. Makes the
   *installation wizard itself* unattended: disk partitioning, edition
   selection, EULA/OOBE screens, local Administrator password. If you'd
   rather click through Setup manually, don't include this file — the
   hardening step below runs either way.
2. **`oem/$OEM$/$$/Setup/Scripts/SetupComplete.cmd`** — this is the actual
   auto-harden mechanism. Windows Setup has a documented convention: any
   file tree placed under `sources\$OEM$\$$\` on the installation media gets
   copied into `%WINDIR%\` on the new install, and if
   `%WINDIR%\Setup\Scripts\SetupComplete.cmd` exists, Setup runs it
   automatically as `NT AUTHORITY\SYSTEM`, right after installation
   finishes and before the first logon prompt. This works for **both**
   unattended and manual/click-through installs — it doesn't depend on
   `autounattend.xml` at all.

   `SetupComplete.cmd` here runs `Harden-WinServer2019.ps1 -Apply` and then
   `Audit-WinServer2019.ps1`, logging both to
   `%WINDIR%\Setup\Scripts\hardening-logs\` on the installed machine so you
   can confirm what happened (`hardening-logs\audit-after-install.txt`).

   Because it runs as SYSTEM rather than an interactively-elevated admin,
   `Harden-WinServer2019.ps1` was updated to also accept the SYSTEM account
   (`S-1-5-18`) alongside interactive Administrators for its `-Apply`
   elevation check.

## Building the ISO

Pick the script for your host OS — both do the same thing: mount/extract
the source ISO, drop in the `$OEM$` tree (and `autounattend.xml` if you
want it), and repack a bootable ISO.

### From Windows (recommended — uses the officially supported tool)

Requires the Windows ADK "Deployment Tools" component (provides
`oscdimg.exe`).

```powershell
.\build\Build-AutoHardenIso.ps1 `
    -SourceIsoPath 'D:\iso\WindowsServer2019.iso' `
    -OutputIsoPath 'D:\iso\WindowsServer2019-autoharden.iso'

# Include the unattended answer file too (WIPES the target disk on install - see warning below):
.\build\Build-AutoHardenIso.ps1 -SourceIsoPath ... -OutputIsoPath ... -IncludeAnswerFile

# Leave specific hardening items out (e.g. keep Print Spooler for a print server):
.\build\Build-AutoHardenIso.ps1 -SourceIsoPath ... -OutputIsoPath ... -Skip PrintSpooler,RdpNla
```

### From Linux (xorriso-based, no ADK available)

Requires `p7zip-full` and `xorriso`.

```bash
./build/build-auto-harden-iso.sh \
    --source /path/to/WindowsServer2019.iso \
    --output /path/to/WindowsServer2019-autoharden.iso \
    --skip PrintSpooler,RdpNla   # optional
    # --with-answer-file          # optional, see warning below
```

This reconstructs the El Torito BIOS+UEFI boot catalog by extracting the
original boot images (`7z` preserves them under `[BOOT]/` on extraction).
**Boot-test the result in a VM before using it on real hardware** — this
path is not Microsoft-supported the way `oscdimg` is.

## Warnings

- **`-IncludeAnswerFile` / `--with-answer-file` wipes Disk 0 on the target
  machine with no prompt.** Only bake `autounattend.xml` into media you'll
  use on machines you intend to fully reimage. Leave it out if you just
  want the auto-harden step with a normal interactive install.
- **`-Apply` runs unattended, on every machine installed from this ISO,
  with no review step.** Test the resulting ISO in a VM first. If a
  particular fix doesn't fit your environment (e.g. the box is meant to be
  a print server or a domain controller where some defaults differ), pass
  `-Skip` at build time rather than disabling it after the fact.
- **About the embedded admin password:** `autounattend.xml`'s
  `AdministratorPassword` is stored in a form that's trivially recoverable
  from the ISO (base64, not encryption) — Setup requires `PlainText=true`
  for this element. Treat a built ISO containing a real password as a
  credential: don't leave it on shared storage, and rotate the password
  after first boot. Prefer leaving the password out of the answer file and
  setting it interactively or via your provisioning system instead.
- Some fixes (SMBv1 removal, PowerShell v2 removal, LSA protection) need a
  reboot to fully take effect — `SetupComplete.cmd` doesn't force one, so
  budget for a reboot after first logon (or add `shutdown /r /t 0` to the
  end of the script if you want it automatic — not included by default
  since it would reboot mid-provisioning without warning).
