# Windows Server 2019 — Common Vulnerability Findings

Each entry follows the same template used in `pentest-milatova/findings/`:
description, impact, detection, remediation. `Id` maps to the `-Skip <Id>`
name in `Harden-WinServer2019.ps1`.

---

### [Critical] `Smb1` — SMBv1 enabled (EternalBlue / WannaCry / NotPetya)

- **Description:** The legacy SMBv1 protocol is still installed/enabled.
  SMBv1 is the protocol exploited by MS17-010 (CVE-2017-0143..0148,
  "EternalBlue"), used by WannaCry and NotPetya for unauthenticated remote
  code execution and worming.
- **Impact:** Unauthenticated remote code execution as SYSTEM; self-propagating
  worm risk on any network segment reachable by the host.
- **Detection:** `Get-WindowsOptionalFeature -Online -FeatureName SMB1Protocol`
- **Remediation:** Disable the SMB1Protocol Windows feature and stop/disable
  the `lanmanworkstation`/`lanmanserver` dependency isn't required — only the
  feature needs removing. Requires reboot.

---

### [High] `SmbSigning` — SMB signing not required

- **Description:** SMB signing (`RequireSecuritySignature`) is not enforced
  on the server, allowing SMB relay attacks (e.g. relaying captured
  NTLM auth to this host).
- **Impact:** An attacker with a man-in-the-middle position (e.g. via LLMNR/
  NBT-NS poisoning) can relay authentication to gain SYSTEM-level file
  system access.
- **Detection:** Registry
  `HKLM\SYSTEM\CurrentControlSet\Services\LanManServer\Parameters!RequireSecuritySignature`
- **Remediation:** Set `RequireSecuritySignature = 1` for both server and
  workstation Lanman parameters.

---

### [Critical] `RdpNla` — RDP without Network Level Authentication

- **Description:** Remote Desktop is enabled without NLA, meaning the RDP
  session is established (and the vulnerable RDP protocol stack is exposed
  to unauthenticated network traffic) before Windows credentials are
  checked. This is the class of exposure exploited by BlueKeep
  (CVE-2019-0708) and follow-on "wormable RDP" CVEs.
- **Impact:** Unauthenticated pre-auth exposure of the RDP stack; on
  unpatched hosts, potential unauthenticated remote code execution.
- **Detection:** Registry
  `HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp!UserAuthentication`
- **Remediation:** Enable NLA (`UserAuthentication = 1`) and confirm RDP
  Security Layer is set to Negotiate/SSL. Patching (Windows Update) is still
  required to fully close BlueKeep-class kernel bugs — NLA is a mitigating
  control, not a substitute.

---

### [Critical] `PrintSpooler` — Print Spooler exposed (PrintNightmare)

- **Description:** The Print Spooler service (`spoolsv.exe`) is running,
  including on servers that don't need print sharing. PrintNightmare
  (CVE-2021-34527, CVE-2021-1675) allows remote/local privilege escalation
  and RCE via the spooler's driver-installation RPC calls.
- **Impact:** Remote code execution as SYSTEM, or local privilege escalation
  to Domain Admin on a Domain Controller.
- **Detection:** `Get-Service Spooler`
- **Remediation:** Disable and stop the Spooler service on servers that do
  not act as print servers. Where printing is required, apply the point-fix
  registry restrictions (`RestrictDriverInstallationToAdministrators = 1`,
  `NoWarningNoElevationOnInstall = 0`) in addition to patching.

---

### [Critical] `Netlogon` — Zerologon mitigation not enforced

- **Description:** The Netlogon secure channel does not enforce
  `FullSecureChannelProtection`, leaving the host vulnerable to the
  Zerologon exploit chain (CVE-2020-1472) if the corresponding security
  update is also missing. Primarily relevant on Domain Controllers.
- **Impact:** Unauthenticated attacker can reset the machine account
  password of the Domain Controller and take over the domain.
- **Detection:** Registry
  `HKLM\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters!FullSecureChannelProtection`
- **Remediation:** Set `FullSecureChannelProtection = 1` (enforcement mode).
  This is a defense-in-depth setting — the August 2020 security update (and
  later the enforcement-phase update) must also be installed.

---

### [High] `WeakTls` — Deprecated TLS/SSL protocols and ciphers enabled

- **Description:** SSL 2.0, SSL 3.0, TLS 1.0 and TLS 1.1 are enabled via
  SChannel, along with weak ciphers (RC4, DES, 3DES, NULL, export-grade).
- **Impact:** Enables downgrade/POODLE/BEAST/RC4-bias style attacks against
  any TLS service on the box (RDP, IIS, WinRM-over-HTTPS, etc.), and fails
  most compliance scans (PCI-DSS, etc.).
- **Detection:** Registry under
  `HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviderS\SCHANNEL\Protocols`
- **Remediation:** Disable SSL 2.0/3.0 and TLS 1.0/1.1 (server + client),
  disable RC4/3DES/NULL/export ciphers, enable TLS 1.2 (and 1.3 where
  supported) as the only allowed protocols.

---

### [Medium] `LlmnrNbtNs` — LLMNR / NetBIOS Name Service enabled

- **Description:** LLMNR and NBT-NS are enabled, allowing name-resolution
  poisoning (Responder-style attacks) to capture NTLM hashes from any host
  on the broadcast segment.
- **Impact:** Credential capture (NTLMv2 hashes) for offline cracking or
  SMB relay, from an attacker with only network access — no prior
  authentication needed.
- **Detection:** Registry `HKLM\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient!EnableMulticast`
  and NetBT interface settings.
- **Remediation:** Disable LLMNR via policy and disable NetBIOS over TCP/IP
  on all adapters.

---

### [High] `WDigest` — WDigest credential caching enabled

- **Description:** WDigest authentication is enabled, which caches
  reversible/plaintext-equivalent credentials in LSASS memory for any
  interactively logged-on user.
- **Impact:** Tools like Mimikatz can extract cleartext passwords from
  LSASS memory for any signed-in account, not just password hashes.
- **Detection:** Registry
  `HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest!UseLogonCredential`
- **Remediation:** Set `UseLogonCredential = 0`.

---

### [High] `LsaProtection` — LSA protection (RunAsPPL) not enabled

- **Description:** LSASS is not running as a Protected Process (Light),
  making it easier for credential-dumping tools to read its memory even
  with WDigest disabled.
- **Impact:** Local admin-level attacker can dump credentials/Kerberos
  tickets from LSASS more easily.
- **Detection:** Registry `HKLM\SYSTEM\CurrentControlSet\Control\Lsa!RunAsPPL`
- **Remediation:** Set `RunAsPPL = 1` (requires reboot; verify no
  incompatible unsigned LSA plugins/AV drivers are in use first).

---

### [Medium] `NtlmV1` — NTLMv1 / LM hashes permitted

- **Description:** `LmCompatibilityLevel` allows LM/NTLMv1 authentication
  instead of requiring NTLMv2.
- **Impact:** LM/NTLMv1 are cryptographically weak and vulnerable to
  fast offline cracking and relay/downgrade attacks.
- **Detection:** Registry
  `HKLM\SYSTEM\CurrentControlSet\Control\Lsa!LmCompatibilityLevel`
- **Remediation:** Set `LmCompatibilityLevel = 5` (send NTLMv2 only, refuse
  LM/NTLM).

---

### [Medium] `AnonEnum` — Anonymous SAM/share enumeration allowed

- **Description:** `RestrictAnonymous`/`RestrictAnonymousSAM` permit
  unauthenticated (null-session) enumeration of local accounts and shares.
- **Impact:** Unauthenticated attacker can enumerate local usernames and
  shares as reconnaissance for password-spray or share-access attacks.
- **Detection:** Registry
  `HKLM\SYSTEM\CurrentControlSet\Control\Lsa!RestrictAnonymous` /
  `RestrictAnonymousSAM`
- **Remediation:** Set both to `1` to block anonymous SAM/share
  enumeration.

---

### [Medium] `GuestAccount` — built-in Guest account enabled

- **Description:** The built-in `Guest` account is enabled.
- **Impact:** Provides an unauthenticated/low-friction foothold account.
- **Detection:** `Get-LocalUser Guest`
- **Remediation:** Disable the account (`Disable-LocalUser Guest`).

---

### [Medium] `PasswordPolicy` — Weak local password/lockout policy

- **Description:** Minimum password length/complexity/lockout threshold do
  not meet baseline (e.g. minimum length < 14, no account lockout after
  repeated failures).
- **Impact:** Increases exposure to online/offline password guessing and
  brute-force attacks.
- **Detection:** `net accounts`
- **Remediation:** Enforce minimum password length 14, lockout threshold 5
  invalid attempts, 15-minute lockout duration (adjust to org policy /
  domain GPO if domain-joined — local policy is overridden by GPO).

---

### [Medium] `PowerShellV2` — Windows PowerShell 2.0 engine still installed

- **Description:** The legacy PowerShell 2.0 engine is present alongside
  PowerShell 5.1. It lacks AMSI integration, script block logging, and
  Constrained Language Mode enforcement, so it's a common "downgrade
  attack" target to evade modern PowerShell logging/AMSI.
- **Impact:** Attackers with code execution can invoke `powershell -version 2`
  to run malicious scripts invisibly to AMSI/logging-based detection.
- **Detection:** `Get-WindowsOptionalFeature -Online -FeatureName MicrosoftWindowsPowerShellV2Root`
- **Remediation:** Remove the PowerShell v2 optional feature.

---

### [Low] `Firewall` — Windows Defender Firewall disabled on an active profile

- **Description:** One or more firewall profiles (Domain/Private/Public)
  is disabled.
- **Impact:** Removes host-based network filtering; increases lateral
  movement and exposure of local services.
- **Detection:** `Get-NetFirewallProfile`
- **Remediation:** Enable the firewall on all profiles.

---

### [Low] `Defender` — Windows Defender real-time protection disabled

- **Description:** Real-time monitoring is turned off (and no
  third-party AV is confirmed installed in its place).
- **Impact:** No on-access malware detection.
- **Detection:** `Get-MpComputerStatus`
- **Remediation:** Re-enable real-time monitoring
  (`Set-MpPreference -DisableRealtimeMonitoring $false`).

---

### [Info] `WindowsUpdate` — Missing security updates

- **Description:** Several of the above (BlueKeep, Zerologon,
  PrintNightmare) are ultimately closed by Microsoft security updates, not
  registry mitigations alone.
- **Impact:** Registry-level mitigations reduce but do not eliminate risk
  without the corresponding patch.
- **Detection:** `Get-HotFix` / Windows Update history — not automated by
  these scripts (patch cadence is environment-specific).
- **Remediation:** Keep the server on a current patch baseline via WSUS /
  Windows Update / your patch management tooling. Out of scope for
  `Harden-WinServer2019.ps1`.
