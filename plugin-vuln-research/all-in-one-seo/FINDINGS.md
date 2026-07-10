# All in One SEO (AIOSEO) — static source review findings (OWASP Top 10 structured)

- **Source:** `https://github.com/awesomemotive/all-in-one-seo-pack`
  (official active repo), commit `1421c9ee420793a0f7d74946c5086dc02e9de415`
  (2026-07-08), version `4.9.10`.
- **Method:** static review, OWASP Top 10 (2021) structure. 577 PHP files
  under `app/` (excluding `vendor/`). No live site was touched; nothing
  was executed.
- **Vendor disclosure channel:** AIOSEO (Awesome Motive) vulnerabilities
  are tracked on Patchstack/WPScan; Awesome Motive doesn't appear to run
  its own public bounty, so route findings through those.
- **Prior disclosure check:** searched publicly before writing anything
  up — this plugin has real CVE history (see A10 below), which changed
  how this pass was framed: instead of only hunting for new bugs, it also
  spot-checked whether previously-disclosed issue classes are actually
  fixed in the current `4.9.10` source.

## Summary

One finding worth flagging (A10, likely the same class as a historical
CVE, framed as "verify the fix" rather than "new bug"), plus two
previously-disclosed CVEs checked and found to be already patched in this
version, plus one positive practice worth citing (A08).

---

### A01:2021 – Broken Access Control

**Checked:** the plugin's central REST route table
(`app/Common/Api/Api.php`), which maps every route to an `access`
capability string, and the `wp_ajax_nopriv_*` registrations.

- **Verified already patched (was CVE-2025-14384-class / contributor
  authorization bypass):** `ai/credits` (GET) and `ai/image-generator`
  (POST/DELETE) both require `access: 'aioseo_page_ai_content_settings'`
  in the current source (`Api.php:47,58,67,213`) — public reporting
  described these as missing capability checks reachable by
  Contributor-level accounts in earlier `4.9.x` versions (AI credits
  info disclosure, and unauthorized media-attachment deletion via the
  image generator). Both routes are capability-gated in `4.9.10`. Did not
  independently verify which WordPress roles are actually granted
  `aioseo_page_ai_content_settings` by default — recommend confirming
  Contributor doesn't have it before treating this as fully closed.
- **Public-by-design `nopriv` AJAX endpoints**
  (`app/Common/SearchStatistics/Api/Listener.php`,
  `app/Lite/Admin/Connect.php`): part of the Google Search Console OAuth
  handoff. `isInstalled()` leaks plugin version + Pro/Lite status to any
  unauthenticated requester (minor info disclosure, same class as
  `readme.txt`'s already-public `Stable tag`, so not scored as a distinct
  finding). `reauthenticate()` validates a trust token via `hash_equals()`
  against a 512-bit SHA-512 hash of a `wp_generate_password(128, true, true)`
  value (see A02) — doesn't persist anything itself. The actual
  state-changing step (`saveAndRedirect()`, which stores the Search
  Console connection profile) only runs from `admin_init` handlers that
  additionally require three separate `hasCapability()` checks — correctly
  gated behind real WP admin-session capabilities, not just the trust
  token.

**Result:** two known issue-classes confirmed already fixed in this
version; no new finding.

---

### A02:2021 – Cryptographic Failures

**Checked:** the Search Console "trust token" mechanism
(`app/Common/SearchStatistics/Api/TrustToken.php`): generated via
`hash('sha512', wp_generate_password(128, true, true) . uniqid('', true))`
and compared via `hash_equals()` (constant-time). Well-implemented.

**Result:** no finding.

---

### A03:2021 – Injection

**Checked:** no `$wpdb` raw-query call found with request superglobals
interpolated directly; no `eval()`/`create_function()` in `app/`.

**Result:** no finding.

---

### A04:2021 – Insecure Design

Not separately assessed this pass beyond the items under other
categories.

---

### A05:2021 – Security Misconfiguration

**Related to A10:** `wp_remote_get( $url, [ 'timeout' => 10, 'sslverify' => false ] )`
in `importRobotsTxtFromUrl()` — disabling TLS certificate verification on
an outbound fetch is a misconfiguration independent of the SSRF angle
below: it exposes the fetch itself to MITM tampering of the "imported"
robots.txt content, on top of the SSRF exposure. Trivial fix:
`'sslverify' => true`.

---

### A06:2021 – Vulnerable and Outdated Components

Not checked this pass (would need to review `vendor/` and
`package.json`/`package-lock.json` against known-CVE versions — not done
here).

---

### A07:2021 – Identification and Authentication Failures

Not applicable beyond the Search Console OAuth flow already covered under
A01/A02.

---

### A08:2021 – Software and Data Integrity Failures

**Positive practice worth citing:** `app/Common/Utils/Helpers.php:294`
(`maybeUnserialize()`) is AIOSEO's own wrapper around `unserialize()` that
**defaults `$allowedClasses` to `false`** and documents why: *"If the
serialized string contains an object, we abort to prevent PHP object
injection."* This is stricter than WordPress core's own built-in
`maybe_unserialize()` (confirmed in this same research effort to have no
`allowed_classes` restriction at all) and better than the unprotected
`unserialize()`/`maybe_unserialize()` calls flagged in the Yoast SEO and
Jetpack reviews. One direct `get_option('trp_settings')` read in
`ThirdParty.php:678` still uses WP core's unprotected `maybe_unserialize()`
instead of AIOSEO's own safer wrapper, but that option is only ever
written by the third-party TranslatePress plugin (not user-request
input), so it isn't scored as an exploitable finding — just an
inconsistency worth tidying up.

**Result:** no finding (positive note).

---

### A09:2021 – Security Logging and Monitoring Failures

Not applicable / not assessed.

---

### A10:2021 – Server-Side Request Forgery (SSRF)

**[Medium] Likely the same class as CVE-2022-42494 ("All in One SEO Pack
Plugin < 4.2.6 SSRF Vulnerability") — verify current fix is complete.**

- **Location:** `app/Common/Tools/RobotsTxt.php:490`
  (`importRobotsTxtFromUrl()`), reached via the REST route
  `tools/import-robots-txt` → `Api\Tools::importRobotsTxt()`
  (`app/Common/Api/Tools.php:27`), registered in `Api.php:139` with
  `access: 'aioseo_tools_settings'`.
- **Code:**
  ```php
  $url = ! empty( $body['url'] ) ? sanitize_url( $body['url'], [ 'http', 'https' ] ) : '';
  // ...
  aioseo()->robotsTxt->importRobotsTxtFromUrl( $url, $blogId );
  // in RobotsTxt.php:
  $request = wp_remote_get( $url, [ 'timeout' => 10, 'sslverify' => false ] );
  ```
- **Description:** the "Import robots.txt from URL" tool accepts any
  `http`/`https` URL (scheme-restricted, but not host-restricted) and
  fetches it server-side with certificate verification disabled. There's
  no check against internal/private IP ranges, `localhost`, or
  cloud-metadata addresses (e.g. `169.254.169.254`) before the request is
  issued. Publicly-reported CVE-2022-42494 already covers an SSRF in this
  plugin's robots.txt-from-URL feature at versions ≤4.2.5.1/4.2.6; the
  fix, based on what's visible in this current `4.9.10` source, appears to
  have been **adding the `aioseo_tools_settings` capability gate**
  (admin-level, not unauthenticated as the original report implies) —
  but the underlying SSRF-capable primitive (arbitrary-host fetch,
  TLS verification disabled) is still architecturally present, just
  requiring authentication now.
- **Preconditions:** requires a user with the `aioseo_tools_settings`
  capability (admin-level in a default install).
- **Impact:** admin-gated SSRF is still a meaningful escalation path in
  practice — it turns an admin-panel compromise (via credential
  stuffing, phishing, or a chained CSRF/XSS elsewhere) into internal
  network reconnaissance or cloud-metadata-endpoint access (e.g. pulling
  IAM credentials on AWS/GCP-hosted sites), which can be a much bigger
  blast radius than the WordPress site alone.
- **Remediation:** set `'sslverify' => true`; add a host/IP allowlist or
  block private/reserved IP ranges (RFC 1918, loopback, link-local
  `169.254.0.0/16`) before issuing the request, e.g. via `wp_http_validate_url()`
  plus an explicit resolved-IP check (DNS rebinding-safe).

---

## Not covered this pass (scope limit)

577 files reviewed via targeted checks (deserialization, SSRF-shaped
`wp_remote_*` calls, AJAX/REST access-control table, the two
already-disclosed 2025/2026 CVEs), not a full line-by-line read. Not
covered: the sitemap generation/XML output pipeline, the Semrush/keyword
integrations, and the `vendor/` third-party dependency tree (A06).
