# Really Simple Security (formerly Really Simple SSL) — static source review findings (OWASP Top 10 + CWE structured)

- **Source:** `https://github.com/Really-Simple-Plugins/really-simple-ssl`
  (official active repo), commit `8d28a51650845049555b7cbe1a607ded7723a45e`
  (2026-07-07), version `9.6.1`.
- **Method:** OWASP Top 10 (2021) + CWE-per-finding. 364 PHP files. No live
  site was touched; nothing was executed.
- **Vendor disclosure channel:** Wordfence Threat Intelligence has a
  history of coordinating with this vendor (see prior CVE below); also
  reachable via Patchstack/WPScan.
- **Why this pass went deeper than usual on authentication logic:** this
  plugin was the source of **CVE-2024-10924** (Nov 2024), a critical,
  widely-covered unauthenticated admin-login-bypass in its own
  two-factor-authentication REST check, affecting 4M+ sites. That history
  makes the current 2FA implementation the single highest-value place to
  look for a regression or a new variant of the same bug class, so this
  pass spent most of its budget there rather than doing a broad shallow
  sweep.

## Summary

No confirmed exploitable vulnerability found. The 2FA/login-bypass surface
— the exact area of the plugin's prior critical CVE — was traced in depth
and appears to have been substantially rewritten since 2024 into a
properly-separated repository/service/controller architecture with
correct nonce binding, `hash_equals()` throughout, and rate limiting. One
cryptographic hygiene issue (CWE-327/CWE-353) was found but no reachable
exploitation path for it.

---

### A01:2021 – Broken Access Control / A07:2021 – Identification and Authentication Failures

**Deep-dive: the "skip 2FA" one-time-login mechanism**
(`security/wordpress/two-fa/class-rsssl-two-factor.php::maybe_skip_auth()`,
`class-rsssl-two-factor-settings.php::rsssl_one_time_login_url()`) — this
is architecturally the closest analogue to the 2024 CVE (a URL-based
mechanism that calls `wp_set_auth_cookie()` directly), so it was traced
end to end:

- The `rsssl_one_time_login` URL parameter is a **trivially reversible**
  "obfuscation" (`base64_encode('user-' . $id . '-id')`, confirmed by
  reading `obfuscate_user_id()`/`deobfuscate_user_id()`) — not a secret,
  by design.
- The real gate is a 128-bit token (`bin2hex(openssl_random_pseudo_bytes(16))`)
  stored server-side in a transient (`skip_two_fa_token_{user_id}`) with a
  **2-minute TTL**, deleted on first use (single-use), and compared with
  `hash_equals()` (`class-rsssl-two-factor.php` line ~288) — no
  timing-attack surface.
- Traced every call site that *generates* this token/URL
  (`providers/class-rsssl-two-factor-email.php` lines ~268 and ~411, and
  `class-rsssl-two-factor.php` line ~1539): all three only run **after**
  the user has already passed WordPress core's primary
  `wp_authenticate_username_password()` check (per the code's own comment,
  "Run only after the core wp_authenticate_username_password() check") —
  i.e., the skip link only ever offers bypassing the *second* factor, for
  an account where 2FA is already configured as optional/"open" for that
  role, never the first factor (username+password).
- The generated link is rendered directly into the already-authenticated
  (password-wise) user's own 2FA-challenge page response, or emailed to
  the account's own registered address — not exposed to an unauthenticated
  third party independent of already knowing that account's password.

**Result:** no bypass found. This looks like a deliberate post-incident
hardening: nonce binds user ID + expiration into the hash itself (not just
the raw token), `hash_equals()` is used consistently, and the "skip"
token is short-lived, single-use, and only reachable after primary
credential verification.

**Also checked:** rate limiting on failed 2FA code attempts
(`is_user_rate_limited()`/`handle_failed_attempt()`) — failed attempts are
timestamped per-user and gated with an escalating time delay, with a
"reset compromised password" path after repeated failures. Reasonable
brute-force mitigation.

---

### A02:2021 – Cryptographic Failures (CWE-327, CWE-353)

**[Low-Medium, no confirmed reachable exploit] Unauthenticated AES-256-CBC encryption**

- **Location:** `lib/admin/class-encryption.php` (`Encryption` trait,
  used across the plugin) and its duplicate in
  `core/app/Traits/HasEncryption.php`.
- **Description:** `encrypt()`/`decrypt()` use `aes-256-cbc` with a random
  IV but **no HMAC or authentication tag** (`openssl_encrypt(..., 'aes-256-cbc', $key, 0, $iv)`,
  no `openssl_encrypt(..., OPENSSL_RAW_DATA)` + separate MAC, no GCM).
  CBC without a MAC is malleable: an attacker able to modify the stored
  ciphertext can predictably corrupt/flip bits in the decrypted plaintext
  of the affected and following blocks without knowing the key. When
  `decrypt(..., 'array', ...)` is used, the (potentially attacker-tampered)
  decrypted bytes are then passed to `unserialize()` with no
  `allowed_classes` restriction (`class-encryption.php` line ~125,
  `HasEncryption.php` line ~108) — the classic ciphertext-malleability
  chained into deserialization pattern.
- **Why this isn't scored higher:** traced every call site
  (`->decrypt(...)`/`->decrypt_if_prefixed(...)`) in the codebase. All of
  them operate on plugin **settings values the site's own admin
  configured** (hosting control-panel passwords for cPanel/Plesk/
  DirectAdmin, a Cloudways API key, license data) — read via
  `rsssl_get_option(...)`, which only an already-`manage_options`-level
  admin can write through the plugin's own settings UI. No call site was
  found where the ciphertext originates from lower-privileged or
  unauthenticated request input. No reachable `type: 'array'` decrypt call
  (the one that actually reaches `unserialize()`) was found being fed by
  anything other than the plugin's own previously-encrypted settings
  either.
- **Remediation (worth doing as defense-in-depth regardless of current
  reachability):** switch to authenticated encryption (AES-256-GCM, or
  CBC + a separate HMAC verified before decrypting/unserializing), and add
  `unserialize($data, ['allowed_classes' => false])` for the `'array'`
  path specifically.

---

### A03:2021 – Injection

No `$wpdb` raw-query call found with request superglobals interpolated
directly. No `eval()`/`create_function()` anywhere in the plugin.

---

### A08:2021 – Software and Data Integrity Failures (CWE-502)

Covered above under A02 (the CBC-without-MAC-plus-unserialize chain).
One additional `unserialize()` call
(`security/wordpress/rename-admin-user.php:143`) reads WordPress core's
own `site_admins` network option — internal data, not request-influenced.

## Not covered this pass (scope limit)

364 files, and this pass deliberately concentrated its budget on the
authentication/2FA subsystem given the plugin's CVE history, rather than
spreading evenly. Not covered: the "vulnerability detection" scanner
feature (likely makes outbound HTTP requests — worth an A10/SSRF-focused
follow-up given the plugin's own name suggests network-facing scanning
logic), the firewall/hardening rule engine, and the Let's Encrypt/hosting
API integrations (`lets-encrypt/integrations/*`) beyond confirming how
they use the encryption trait.
