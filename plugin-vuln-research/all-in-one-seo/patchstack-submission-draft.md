# Patchstack / WPScan submission draft — All in One SEO (AIOSEO)

Copy/paste into Patchstack's (patchstack.com/report) or WPScan's
submission form after logging into your own account. Not submitted
automatically — no API/account access exists for this from here.

---

**Title:** Server-Side Request Forgery (SSRF) in "Import robots.txt from URL" tool — likely incomplete fix for CVE-2022-42494

**Plugin:** All in One SEO (AIOSEO) — `all-in-one-seo-pack`

**Affected version tested:** `4.9.10` (commit `1421c9ee420793a0f7d74946c5086dc02e9de415`, 2026-07-08). Please confirm against the latest release, as this environment could not fetch a newer copy at review time.

**Vulnerability class:** CWE-918 (SSRF)

**Severity (suggested):** Medium. Requires the `aioseo_tools_settings`
capability (admin-level in a default install) to reach — not a
privilege-escalation or unauthenticated issue by itself, but a real,
concrete SSRF primitive with TLS verification explicitly disabled.

**Description:**

`app/Common/Tools/RobotsTxt.php`, method `importRobotsTxtFromUrl()` (line
~490), reached via the REST route `tools/import-robots-txt` →
`Api\Tools::importRobotsTxt()` (`app/Common/Api/Tools.php:27`, registered
in `Api.php:139` with `access: 'aioseo_tools_settings'`):

```php
// Api/Tools.php
$url = ! empty( $body['url'] ) ? sanitize_url( $body['url'], [ 'http', 'https' ] ) : '';
aioseo()->robotsTxt->importRobotsTxtFromUrl( $url, $blogId );

// RobotsTxt.php
$request = wp_remote_get( $url, [ 'timeout' => 10, 'sslverify' => false ] );
$robotsTxtContent = wp_remote_retrieve_body( $request );
```

The URL is only scheme-restricted (`http`/`https`), not host-restricted.
There is no check against internal/private IP ranges (RFC 1918, loopback,
link-local `169.254.0.0/16` — including cloud metadata endpoints like
`169.254.169.254`) before the request is issued, and TLS certificate
verification is explicitly disabled (`sslverify => false`), which is a
separate misconfiguration (MITM exposure) on top of the SSRF.

**Why this is being reported despite CVE-2022-42494 already existing:**
public records show CVE-2022-42494 ("All in One SEO Pack Plugin < 4.2.6
SSRF Vulnerability") already covers an SSRF in this same
robots.txt-from-URL feature. Based on what's visible in the current
`4.9.10` source, the fix that was applied appears to have been **adding
the `aioseo_tools_settings` capability gate** — but the underlying
SSRF-capable primitive (arbitrary-host fetch, TLS verification disabled,
no private-IP filtering) is still present in the code, just now requiring
authentication. This report is to confirm whether that's considered an
acceptable resolution or whether the underlying primitive itself should
still be hardened (this often matters for compliance/defense-in-depth
even when capability-gated, since admin-panel compromise via a *different*
vector — credential stuffing, phishing, a chained CSRF/XSS elsewhere — is
a realistic path that would then inherit this SSRF).

**Steps to Reproduce:**

1. As a user with the `aioseo_tools_settings` capability, send
   `POST /wp-json/aioseo/v1/tools/import-robots-txt` with JSON body
   `{"source": "url", "url": "http://169.254.169.254/latest/meta-data/", "blogId": 0}`
   (adjust target to an internal address reachable from the hosting
   environment — not tested against any live/production system by us).
2. Observe the server issues the outbound request via `wp_remote_get()`
   with certificate verification disabled and no destination filtering.

**Impact:** internal network reconnaissance, port scanning, and
potentially retrieving cloud-provider instance metadata (IAM
credentials on AWS/GCP-hosted sites) from an admin-gated action — a
much larger blast radius than the WordPress install alone if the hosting
environment is cloud-based.

**Remediation:**
- Set `'sslverify' => true`.
- Validate the resolved IP (post-DNS-resolution, to be rebinding-safe)
  against private/reserved ranges before issuing the request — WordPress
  core's `wp_http_validate_url()` plus an explicit check, or a documented
  equivalent.

**Testing disclosure:** static source review only; no live WordPress
installation was targeted or tested. Full methodology and additional
checked-and-patched items (two more recent, already-fixed CVEs on
`ai/credits`/`ai/image-generator`) documented at
`plugin-vuln-research/all-in-one-seo/FINDINGS.md` in the researcher's own
working repo, available on request.
