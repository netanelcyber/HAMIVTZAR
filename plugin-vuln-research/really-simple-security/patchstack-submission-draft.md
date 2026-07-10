# Patchstack / WPScan submission draft — Really Simple Security

Copy/paste into Patchstack's (patchstack.com/report) or WPScan's
submission form after logging into your own account. Not submitted
automatically — no API/account access exists for this from here.

**Framing note:** unlike the Jetpack/AIOSEO/WPForms drafts, this one has
**no demonstrated reachable exploitation path** — it's a cryptographic
hygiene finding reported as a hardening recommendation. Some bounty
programs won't reward/triage this without a working PoC; consider
whether to submit as a formal vulnerability report or route it as a
hardening suggestion via the vendor's normal support channel instead.
Judgment call is yours.

---

**Title:** Unauthenticated (non-MAC) AES-256-CBC encryption feeding an unrestricted unserialize() call — hardening recommendation, no confirmed reachable exploit path

**Plugin:** Really Simple Security (formerly Really Simple SSL) — `really-simple-ssl`

**Affected version reviewed:** `9.6.1` (commit `8d28a51650845049555b7cbe1a607ded7723a45e`, 2026-07-07).

**Vulnerability class:** CWE-327 (Use of a Broken or Risky Cryptographic
Algorithm) / CWE-353 (Missing Support for Integrity Check), chained with
CWE-502 (Deserialization of Untrusted Data) in the code path, though no
reachable attacker-controlled input into that path was found.

**Severity (suggested):** Low. Reporting for defense-in-depth, not as an
active exploit.

**Description:**

`lib/admin/class-encryption.php` (`Encryption` trait, duplicated in
`core/app/Traits/HasEncryption.php`) implements the plugin's shared
encrypt/decrypt helper using `aes-256-cbc` with a random IV but **no
HMAC or authentication tag**:

```php
$iv = openssl_random_pseudo_bytes(openssl_cipher_iv_length('aes-256-cbc'));
$encrypted = openssl_encrypt($data, 'aes-256-cbc', $key, 0, $iv);
return base64_encode($encrypted . '::' . $iv);
```

CBC without a MAC is malleable — an attacker able to modify stored
ciphertext can predictably corrupt/flip bits in the decrypted plaintext
without knowing the key. When `decrypt(..., 'array', ...)` is used, the
resulting (potentially tampered) plaintext is passed to `unserialize()`
with no `allowed_classes` restriction:

```php
if ( 'array' === strtolower( $type ) ) {
    $unserialized_data = @unserialize( $decrypted_data );
    return ( is_array( $unserialized_data ) ) ? $unserialized_data : [];
}
```

This is the shape of a known real-world attack chain (ciphertext
malleability → engineered deserialization → PHP object injection), *if*
an attacker can reach and modify the specific ciphertext blob being
decrypted.

**Why no severity escalation:** every call site of `decrypt()`/
`decrypt_if_prefixed()` found in this codebase operates on **plugin
settings values that only an already-`manage_options`-level admin can
write** through the plugin's own settings UI (hosting control-panel
passwords for cPanel/Plesk/DirectAdmin, a Cloudways API key, license
data) — read via `rsssl_get_option(...)`. No call site was found where
the ciphertext originates from lower-privileged or unauthenticated
request input, and no reachable `type: 'array'` (the only path that
reaches `unserialize()`) call was found fed by anything but the plugin's
own previously-encrypted settings. **We did not find a way for an
external attacker to reach or modify the relevant ciphertext without
already having equivalent admin-level access**, which would make this
moot as an escalation path in the configurations we could trace.

**Steps to Reproduce:** none provided — this is a code-review finding
about a risky cryptographic construction, not a demonstrated exploit
against a specific reachable endpoint. If the vendor's own review finds
a call site we missed (e.g. a settings field indirectly reachable at a
lower privilege level, or a future feature reusing this trait for
externally-sourced data), the malleability + unrestricted-unserialize
combination would become directly relevant.

**Impact (if a reachable path exists that we didn't find):** PHP object
injection, potentially escalating to RCE given a suitable POP gadget
chain among classes loaded on the site.

**Remediation:**
- Switch to authenticated encryption: AES-256-GCM, or CBC plus a
  separately-verified HMAC checked *before* decrypting/unserializing.
- Add `unserialize( $data, [ 'allowed_classes' => false ] )` for the
  `'array'` path regardless, as defense in depth independent of the
  above.

**Testing disclosure:** static source review only; no live WordPress
installation was targeted or tested. This pass concentrated most of its
budget on the plugin's 2FA/login-bypass subsystem (given the plugin's own
prior CVE-2024-10924, a critical unauthenticated-login-bypass in that
exact area) and found that subsystem to be soundly re-architected with no
bypass identified. Full methodology documented at
`plugin-vuln-research/really-simple-security/FINDINGS.md` in the
researcher's own working repo, available on request.
