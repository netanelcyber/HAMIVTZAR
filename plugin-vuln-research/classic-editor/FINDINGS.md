# Classic Editor — static source review findings (OWASP Top 10 + CWE structured)

- **Source:** `https://github.com/WordPress/classic-editor` (official
  repo, maintained directly by WordPress core contributors), commit
  `bb8d0cc7bfafa7458d90503c44e3c7723cb7324c` (2026-05-27), version `1.7.0`.
- **Method:** OWASP Top 10 (2021) + CWE-per-finding, same as prior passes.
  This plugin is small enough (a single 1,064-line PHP file, no AJAX/REST
  endpoints at all) that it was read in full rather than sampled.
- **Vendor disclosure channel:** WordPress core security (security@wordpress.org)
  / HackerOne (hackerone.com/wordpress), since this is a core-team-maintained
  plugin.
- **Prior disclosure check:** not applicable — no finding to check.

## Result: no vulnerability found (full read of a small, actively-maintained file)

### A01:2021 – Broken Access Control

**Checked:** the only two state-changing actions in the whole plugin.

- `save_user_settings( $user_id )`: requires
  `wp_verify_nonce( $_POST['classic-editor-user-settings'], 'allow-user-settings' )`
  **and** (`$user_id === get_current_user_id()` OR
  `current_user_can( 'edit_user', $user_id )`) before writing — correct
  per-object capability check, avoids one user changing another's editor
  preference without permission.
- `save_network_settings()`: requires a nonce
  (`allow-site-admin-settings`) **and** `current_user_can( 'manage_network_options' )`.
- Both writes are also constrained to two hardcoded enum values each
  (`classic`/`block`, `allow`/`disallow`) via `validate_option_editor()`/
  `validate_option_allow_users()` sanitize callbacks registered through
  WordPress core's Settings API — no arbitrary value can ever be stored.
- No AJAX (`wp_ajax_*`) or REST routes exist in this plugin at all; every
  interaction goes through WordPress core's own Settings API / post meta
  functions.

**Result:** no finding.

---

### A02:2021 – Cryptographic Failures

Not applicable — no secrets, tokens, or crypto in this plugin.

---

### A03:2021 – Injection (CWE-89 SQLi, CWE-79 XSS, CWE-94 Code Injection)

**Checked:** every `echo`/output statement and every data-read path.

- No direct database queries anywhere — all persistence goes through
  `get_option()`/`update_option()`/`get_post_meta()`/`update_post_meta()`/
  `get_network_option()` (WordPress core APIs).
- No `eval()`, `unserialize()`, or dynamic `include`/`require`.
- The one raw `echo` of a non-constant-looking value
  (`safari_18_temp_fix()`: `echo $clear;`) is actually a hardcoded
  ternary result (`is_rtl() ? 'right' : 'left'`), not user input.
- All URLs built from request data (`add_query_arg()`/`remove_query_arg()`
  results in `do_meta_box()`, `add_edit_links()`) are passed through
  `esc_url()` before being echoed into `href` attributes.
- `$_GET['classic-editor']`/`$_REQUEST['classic-editor']` are read in
  several places (`is_classic()`, `redirect_location()`,
  `get_edit_post_link()`, `choose_editor()`) but only ever via `isset()` —
  used purely as a boolean UI-preference flag, never echoed or used to
  build a query/command. The missing nonce checks on these reads
  (annotated `phpcs:ignore ... NonceVerification` by the plugin's own
  authors) are appropriate: toggling which editor view loads for the
  current request isn't a state-changing action worth CSRF-protecting.

**Result:** no finding.

---

### A04:2021 – Insecure Design

The overall design (toggle a UI preference via WordPress core's Settings
API, gate the two writes behind nonce + capability, never accept
free-form input) is minimal and appropriately scoped for what the plugin
does. No finding.

---

### A05:2021 – Security Misconfiguration

Not applicable — no configuration surface beyond the two enum settings
already covered under A01.

---

### A06:2021 – Vulnerable and Outdated Components

No third-party dependencies (single self-contained PHP file plus one
small first-party JS file for the block-editor "switch to classic"
button). No finding.

---

### A07:2021 – Identification and Authentication Failures

Not applicable — relies entirely on WordPress core's own auth/capability
system, correctly checked (see A01).

---

### A08:2021 – Software and Data Integrity Failures (CWE-502)

No `unserialize()`/`maybe_unserialize()` anywhere in the plugin. No
finding.

---

### A09:2021 / A10:2021

Not applicable — no logging surface, no outbound HTTP requests
(`wp_remote_*`) anywhere in the plugin.

## Conclusion

Small, actively-maintained, core-team-authored plugin with a narrow
feature surface (one settings toggle, no AJAX/REST, no database queries
of its own). Read in full; no vulnerability found. This is a useful data
point for the research as a whole: a plugin's small size and single-vendor
(WordPress core team) authorship track with a clean result here, unlike
the larger multi-vendor-integration plugins reviewed earlier (Yoast,
Jetpack, AIOSEO, WPForms) where every finding so far has clustered around
either legacy compat code or third-party service integration flows
(import/export, OAuth-style connect flows, webhook/API calls) rather than
the plugin's core feature logic.
