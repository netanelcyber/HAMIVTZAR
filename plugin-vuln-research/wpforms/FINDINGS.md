# WPForms Lite — static source review findings (OWASP Top 10 + CWE structured)

- **Source:** `https://github.com/common-repository/wpforms-lite` (community
  SVN-mirror bot — WPForms has no dedicated public dev repo; this is the
  freshest reachable copy from this environment). Commit
  `2dd679d2c3a20bf82d38ac3bd08ce4f20da72eb6`, dated **2024-11-01**, version
  `1.9.1.6`.
- **Freshness caveat:** this snapshot is ~1.5 years old relative to the
  current date, unlike the actively-synced dev repos used for
  Yoast/WooCommerce/Jetpack/CF7/Elementor/AIOSEO. The general
  architecture/patterns are almost certainly still representative, but
  **any finding below must be re-verified against the current release
  (`1.9.9.2`+ as of this research) before disclosure** — it's possible
  it's already been fixed independently of this review.
- **Method:** static review, OWASP Top 10 (2021) categories with an
  explicit CWE ID per finding, per request. 1,084 PHP files under `src/`
  (plus `includes/`, `lite/`). No live site was touched; nothing was
  executed.
- **Vendor disclosure channel:** WPForms (Awesome Motive) — no dedicated
  public bounty found; route through Patchstack/WPScan, same as AIOSEO
  (also an Awesome Motive product).
- **Prior disclosure check:** searched publicly for the main finding below
  (`wpforms_connect_process`, "WPForms Connect" + RCE/plugin-install) — no
  match found. Also checked the plugin's own recent public CVE history:
  **CVE-2026-25339** (sensitive form-data exposure to lower-privileged
  authenticated users, fixed in `1.9.9.2`, no relation to the finding
  below) and a stored-XSS CVE line (`CVE-2024-11223`/`GHSA` advisories) —
  neither matches the mechanism found here. Treat the search as
  best-effort, not proof of novelty.

---

## [High, conditional on token disclosure] Unauthenticated arbitrary plugin installation via WPForms Connect — CWE-494 (Download of Code Without Integrity Check), OWASP A08:2021 (Software and Data Integrity Failures) / A01:2021 (Broken Access Control)

- **Location:** `src/Lite/Admin/Connect.php`
  - Token/URL generation: `generate_url()` (admin-authenticated,
    `wp_ajax_wpforms_connect_url`, nonce-checked, requires
    `install_plugins`), lines ~72-157.
  - **The exposed sink:** `process()`
    (`add_action( 'wp_ajax_nopriv_wpforms_connect_process', [ $this, 'process' ] )`,
    line 46) — registered `nopriv`, i.e. reachable by **any unauthenticated
    visitor**, lines ~164-287.
- **How it's supposed to work:** an admin clicks "Upgrade to Pro" in
  wp-admin. `generate_url()` mints a random one-time token
  (`$oth = hash('sha512', wp_rand())`), stores the plaintext in the
  `wpforms_connect_token` option, and sends the browser to
  `upgrade.wpforms.com` with `hash_hmac('sha512', $oth, wp_salt())` as a
  query parameter (`oth`), along with this site's `admin-ajax.php` URL as
  the callback `endpoint`. wpforms.com's server is expected to validate
  the license key and then call back
  `admin-ajax.php?action=wpforms_connect_process&oth=<hash>&file=<pro-plugin-zip-url>`.
- **The vulnerable code:**
  ```php
  // process() -- reachable with NO authentication at all
  $post_oth = ! empty( $_REQUEST['oth'] ) ? sanitize_text_field( wp_unslash( $_REQUEST['oth'] ) ) : '';
  $post_url = ! empty( $_REQUEST['file'] ) ? esc_url_raw( wp_unslash( $_REQUEST['file'] ) ) : '';
  // ...
  $oth = get_option( 'wpforms_connect_token' );
  if ( hash_hmac( 'sha512', $oth, wp_salt() ) !== $post_oth ) {   // (1) not hash_equals()
      wp_send_json_error( $error );
  }
  delete_option( 'wpforms_connect_token' );                       // one-time use
  // ...
  $installer = new PluginSilentUpgrader( new ConnectSkin() );
  // ...
  $installer->install( $post_url );                               // (2) $post_url is NOT restricted to wpforms.com
  // ...
  $activated = activate_plugin( $plugin_basename, '', false, true ); // (3) auto-activated, no further check
  ```
- **Two independent weaknesses, either alone concerning, together serious:**
  1. **(CWE-494)** `$post_url` — the ZIP to download and install as a
     plugin — is only run through `esc_url_raw()` (syntax sanitization),
     never checked against an allowlisted host (e.g. `downloads.wordpress.org`
     or `wpforms.com`). Whatever URL is supplied is downloaded, unzipped,
     installed, and **activated**, with full plugin-execution privileges
     on the site.
  2. **(CWE-306-adjacent, broken access control)** the *only* gate on this
     otherwise-completely-unauthenticated, plugin-installing endpoint is
     possession of the `oth` value. It's high-entropy (a SHA-512 HMAC), so
     brute-forcing it directly is infeasible — but the value is designed
     to leave the server: it's placed in a URL sent to a third-party
     domain (`upgrade.wpforms.com`) via a full-page browser navigation,
     and it's also returned verbatim in the JSON body of the
     admin-authenticated `generate_url()` AJAX response (`back_url`).
     Anything that can observe that outbound URL or that JSON response —
     a Referer leak to `upgrade.wpforms.com` or any third-party resource
     it loads, browser history/proxy logs, a MITM on a non-HTTPS hop, an
     XSS bug anywhere on the admin's `wpforms-settings` page, or a
     compromise of `upgrade.wpforms.com` itself — yields a token that can
     be replayed against **any URL** the attacker chooses, with no login
     required.
  3. **(CWE-208, minor)** the token comparison uses `!==` rather than
     `hash_equals()`. Low practical severity on its own for a 512-bit
     HMAC, but still a best-practice deviation worth fixing alongside the
     above.
- **Why this is being reported as "conditional" rather than a clean
  zero-click bug:** exploitation requires the `oth` value to leak through
  one of the channels above first — an attacker with no other foothold
  cannot forge a valid token from scratch. This is meaningfully different
  from, say, a straightforward unauthenticated SQLi. But it's still a real
  design weakness: a single powerful, unauthenticated, no-login-required
  action (arbitrary code execution via plugin install) is protected by
  exactly one secret that the architecture itself routes through a
  third-party domain and an AJAX response body, rather than binding the
  installation step to, e.g., a fresh admin-session check or re-validating
  the license key server-side-to-server-side before installing.
- **Impact if the precondition is met:** full remote code execution —
  installing and auto-activating an attacker-hosted "plugin" ZIP is
  equivalent to arbitrary PHP execution on the server.
- **Remediation:**
  - Validate `$post_url`'s host against an allowlist (e.g. only accept
    URLs on `wpforms.com`/a documented CDN domain) before passing to the
    installer.
  - Use `hash_equals()` instead of `!==` for the token comparison.
  - Consider binding the callback to something not routed through a
    third-party redirect and a client-visible AJAX response — e.g. a
    server-to-server confirmation call back to wpforms.com to validate
    the token before installing, rather than trusting whoever presents it.

---

## Checked, not found (negative results, CWE/OWASP-labeled)

- **A10:2021 (SSRF) / CWE-352 (CSRF) — Stripe webhook route**
  (`src/Integrations/Stripe/Api/WebhookRoute.php`): registered with
  `permission_callback => '__return_true'` (necessarily public — Stripe
  calls it server-to-server), but `dispatch_stripe_webhooks_payload()`
  validates every request via Stripe's own official
  `Webhook::constructEvent($payload, $signature, $secret)` SDK method
  (HMAC signature verification against a per-site webhook signing secret
  from `wpforms_setting('stripe-webhooks-secret-...')`), throwing and
  returning HTTP 500 on failure. Correctly implemented — no finding.
- **A01:2021 (Broken Access Control) — anti-spam token endpoint**
  (`src/Forms/Token.php`, `wp_ajax_nopriv_wpforms_get_token`): intentionally
  public (issues a time-boxed, per-form anti-spam token to anonymous
  visitors filling out a public form, computed as
  `md5(date-bucket . form-id . site-secret-key)`). This is friction against
  spam bots, not a security boundary, and is appropriately scoped — no
  finding.
- **A08:2021 (Software and Data Integrity Failures) / CWE-502 — payment
  meta deserialization** (`src/Db/Payments/Meta.php:236`,
  `maybe_unserialize()`): reads WPForms' own custom payments-meta table;
  newer writes are `wp_json_encode()`'d (visible a few lines above in the
  same file), so this `maybe_unserialize()` call is a backward-compat read
  path for old rows the plugin itself wrote — no external-input write path
  found into this table. No finding.
- **A03:2021 (Injection):** no `$wpdb` raw-query call found with request
  superglobals interpolated directly; no `eval()`/`create_function()` in
  `src/`.

## Not covered this pass (scope limit)

Given the ~1.5-year-old source, this pass focused on the highest-signal
areas (AJAX/REST access control, deserialization, the Connect/upgrade
flow) rather than a full line-by-line read of 1,084 files. Not covered:
the form-builder/entry-storage pipeline in depth, the `lite/` upsell UI
code, and the Smart Tags system. **Before acting on the Connect.php
finding, re-clone against the current WPForms release and confirm the
code still matches** — this is the single most important follow-up given
the freshness gap.
