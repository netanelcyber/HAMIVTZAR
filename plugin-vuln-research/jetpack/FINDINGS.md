# Jetpack — static source review findings

- **Source:** `https://github.com/Automattic/jetpack` (monorepo), commit
  `3b9717e5e18063c5b7b4d4312da1bf8b27c61580` (2026-07-09), plugin version
  `16.0` (`projects/plugins/jetpack/jetpack.php`).
- **Method:** static review only, same methodology as prior passes —
  focused on SQLi, XSS, code-injection-class bugs (`eval`, dynamic
  `include`/`require`, `unserialize`, dynamic class/function
  instantiation), command execution, and REST permission-callback gaps
  across `projects/plugins/jetpack/` (999 PHP files, excluding `tests/`).
  No live site was touched; nothing was executed.
- **Vendor disclosure channel:** Automattic's HackerOne program
  (hackerone.com/automattic) covers Jetpack, per the same `SECURITY.md`
  referenced in the WooCommerce review (same parent org/monorepo).
- **Prior disclosure check:** searched publicly for this exact pattern —
  no confirmed match, but as with prior passes, Patchstack's plugin page
  couldn't be fetched from this environment (blocked), so treat this as
  inconclusive, not a clean bill of health.

---

## [Low-Medium] Unsafe deserialization of a remote HTTP response body (CWE-502)

- **Location:** `json-endpoints/jetpack/class.jetpack-json-api-themes-install-endpoint.php:150-179`
  (`validate_themes()`), reached via `POST /sites/%s/themes/%s/install`.
- **Code:**
  ```php
  $params     = (object) array( 'slug' => $theme );
  $url        = 'https://api.wordpress.org/themes/info/1.0/'; // @todo Switch to .../1.1/, which uses JSON rather than PHP serialization.
  $args       = array(
      'body' => array(
          'action'  => 'theme_information',
          'request' => serialize( $params ),
      ),
  );
  $response   = wp_remote_post( $url, $args );
  $theme_data = unserialize( $response['body'] ); // no allowed_classes restriction
  ```
- **Description:** for any requested theme slug that isn't a `-wpcom`
  theme, this endpoint calls the *legacy, PHP-serialization-based*
  `api.wordpress.org/themes/info/1.0/` endpoint (WordPress core itself
  moved its own theme/plugin update checks to the JSON `1.1`/`1.2`
  endpoints years ago specifically to get away from unserializing remote
  responses — the `@todo` comment in this file shows the Jetpack team is
  already aware this specific call hasn't been migrated). The raw HTTP
  response body is then passed straight into `unserialize()` with no
  `allowed_classes` restriction.
- **Preconditions:** requires `install_themes` capability (admin-level) to
  reach the endpoint at all — this isn't reachable by an anonymous or
  low-privileged user. The remote host is hardcoded to the legitimate
  `api.wordpress.org`, so this is not attacker-controlled SSRF; exploiting
  the deserialization itself would require the response actually returned
  by (or something able to impersonate) `api.wordpress.org`'s legacy `1.0`
  endpoint to contain a malicious serialized payload — i.e., a supply-chain
  or network-path compromise on that specific dependency, not a
  directly-attacker-suppliable input in the ordinary sense.
- **Impact:** if that precondition were ever met, PHP object injection via
  unserialize is potentially exploitable into RCE given a suitable POP
  gadget chain among classes loaded by WordPress core, Jetpack, or any
  other active plugin/theme — same vulnerability class flagged in the
  Yoast SEO and WooCommerce reviews. Realistic likelihood is low (requires
  compromising or MITM'ing a real wordpress.org API response over HTTPS),
  but the fix is simple and the code path is already flagged by its own
  authors as legacy/overdue for migration.
- **Remediation:** either (a) migrate to `api.wordpress.org/themes/info/1.1/`
  (JSON, as the existing `@todo` comment already says to do), or at minimum
  (b) change to `unserialize( $response['body'], array( 'allowed_classes' => false ) )`
  as a low-effort interim mitigation.

---

## Checked, not found (negative results)

- All other `unserialize()`/`maybe_unserialize()` hits in
  `projects/plugins/jetpack/` (outside `tests/`) operate on Jetpack's own
  internally-generated data: post meta the plugin itself wrote
  (`sal/class.json-api-post-base.php`, `functions.global.php`), an
  internal endpoint-registry cache key built from `serialize()` on
  hardcoded route definitions (`class.json-api.php:484`,
  `sal/class.json-api-links.php:418` — confirmed not request-influenced),
  and a VideoPress player's own cached object
  (`modules/videopress/class.videopress-player.php`). No external-input
  write path found into any of these.
- `eval()` hits are exclusively in `tests/php/` (unit-test stubs for class
  isolation) — not production/request-reachable code.
- The one `proc_open()` hit is in `tools/build-asset-cdn-json.php`, a
  build-time script, not runtime plugin code reachable via a web request.
- No `system()`/`exec()`/`shell_exec()`/`passthru()`/`popen()` in
  production code.
- No direct `$wpdb->query()`/`get_*()` call with `$_GET`/`$_POST`/`$_REQUEST`
  interpolated directly into SQL.
- No `echo $_GET/$_POST/$_REQUEST/$_COOKIE[...]` without escaping.
- The `permission_callback => '__return_true'` REST routes found
  (`wpcom-endpoints/class-wpcom-rest-api-v2-endpoint-ai.php`'s
  `/jetpack-search/ai/search` and `/jetpack-search/ai/rank`,
  `class-wpcom-rest-api-v2-endpoint-mailchimp.php`, `hello.php`,
  `business-hours.php`, `class-wpcom-rest-api-v2-endpoint-instagram-gallery.php`)
  are all public, read-oriented, site-facing features (on-site AI search
  for visitors, a Mailchimp signup form, a business-hours widget, an
  Instagram embed) — intentionally public by design, same category as
  WooCommerce's Store API. Not a finding.

## Not covered this pass (scope limit)

999 files (and the plugin is one of ~19 in this monorepo) is too large for
a full pass. Not examined in depth: Jetpack Sync (the subsystem that
mirrors site data to WordPress.com — a historically sensitive area for
this plugin), the XML-RPC/connection-signature verification code itself
(`Automattic\Jetpack\Connection`), and the other 18 plugins in the
monorepo (Backup, Boost, Protect, Search, Social, VaultPress, etc.), which
are separate WordPress.org listings in their own right.
