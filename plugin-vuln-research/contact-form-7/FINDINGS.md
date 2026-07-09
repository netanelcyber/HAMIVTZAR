# Contact Form 7 — static source review findings (OWASP Top 10 structured)

- **Source:** `https://github.com/rocklobster-in/contact-form-7` (official
  active repo), commit `c78462421402eb465353b98f36465b00d3683019`
  (2026-06-19), version `6.2-dev`.
- **Method:** static review only, organized by OWASP Top 10 (2021)
  category instead of an ad-hoc pattern list, per request. 87 PHP files
  (small, focused plugin compared to the monorepos reviewed so far). No
  live site was touched; nothing was executed.
- **Vendor disclosure channel:** contactform7.com doesn't run its own
  bounty; CF7 vulnerabilities are typically coordinated through
  WPScan/Patchstack or reported directly via the GitHub repo's issue
  tracker (`rocklobster-in/contact-form-7`).
- **Note on this pass's process change:** from here on, findings are
  organized under OWASP Top 10 (2021) categories rather than an ad-hoc
  vulnerability-class list, per request. Categories with no findings are
  still listed with what was checked, so the absence is a documented
  negative result, not silence.

## Result: no confirmed exploitable vulnerability found this pass

CF7 has a well-known history of real, historical CVEs in exactly two
areas — unrestricted file upload and mail-header injection — and the
current code shows deliberate, layered hardening in both, consistent with
lessons already learned and fixed years ago. Reviewed against every OWASP
Top 10 category below; only two categories had anything worth noting, and
neither is a new exploitable finding.

---

### A01:2021 – Broken Access Control

**Checked:** all REST routes (`includes/rest-api.php`, namespace
`contact-form-7/v1`).

- `/contact-forms`, `/contact-forms/{id}` (read/create/update/delete):
  gated on `current_user_can( 'wpcf7_edit_contact_form', $id )` and
  siblings — correctly uses **per-object meta-capability mapping with the
  ID**, not a blanket `manage_options`/`edit_posts` check, which avoids the
  classic IDOR mistake (capability granted for form A doesn't imply access
  to form B).
- `/contact-forms/{id}/feedback` (submit), `/feedback/schema`, `/refill`:
  `permission_callback => '__return_true'`. This is correct, not a gap —
  these are the public form-submission/validation-schema/CAPTCHA-refill
  endpoints that anonymous site visitors must be able to reach for the
  contact form to function at all.

No AJAX (`wp_ajax_*`) handlers exist in this plugin at all — everything
admin-facing goes through the capability-checked REST routes above.

**Result:** no finding.

---

### A02:2021 – Cryptographic Failures

**Checked:** random-value generation for filenames/tokens
(`wpcf7_maybe_add_random_dir()` uses `wp_rand()`), no hardcoded secrets or
custom crypto found.

**Result:** no finding. (`wp_rand()` here is used for an upload
subdirectory name, not a security token — collision resistance, not
unpredictability, is what matters there, and it's checked with
`file_exists()`/regenerated on collision regardless.)

---

### A03:2021 – Injection

**Checked:** the two historically-relevant sub-classes for this plugin:

- **Mail header injection** (`includes/mail.php`, `WPCF7_Mail::compose()`):
  `subject`, `sender`, `recipient` all pass through `wpcf7_strip_newline()`
  (strips `\r`/`\n`) before being placed into `From:`/headers — the classic
  CRLF-into-header injection vector is closed. `additional_headers` (the
  admin-authored template, not raw end-user input) is explicitly split by
  line and each line trimmed, rather than trusted as one opaque blob.
- **SQL injection:** no `$wpdb` raw-query usage found in the plugin at all
  (form/submission data doesn't appear to touch custom SQL — it's stored as
  post content/meta via core WP APIs).
- **XSS:** form-tag rendering consistently uses `esc_attr()`/`esc_html()`
  (e.g. `modules/file.php`); did not find a raw echo of `$_GET`/`$_POST`/
  `$_REQUEST`.
- **Code injection:** no `eval()`, no dynamic `include`/`require` on
  request-influenced paths, no `unserialize()` anywhere in the plugin.

**Result:** no finding.

---

### A04:2021 – Insecure Design

**Checked:** the file-upload architecture as a whole
(`includes/file.php`) — this is the category where CF7's *design*, not
just input filtering, matters most given its CVE history:

- Uploaded files land in a **randomly-named subdirectory**
  (`wpcf7_maybe_add_random_dir()`) under a dedicated temp dir, not the
  regular media library.
- That temp dir is **`.htaccess`-protected with a hard `Require all
  denied`/`Deny from all`** (both Apache 2.4+ and 2.2 syntax), written by
  the plugin itself on init — so even a successfully-uploaded malicious
  file can't be requested directly over HTTP.
- Files are **`chmod`'d `0400`** (owner-read-only) immediately after the
  move.
- A `shutdown`-hooked cleanup (`wpcf7_cleanup_upload_files()`) removes
  anything older than 60 seconds, capping the exposure window regardless.

This is defense-in-depth done correctly: even if a filename/MIME check
were bypassed, three independent controls (unguessable path, deny-all
`.htaccess`, auto-expiry) stand between an uploaded file and execution or
even direct retrieval.

**Result:** no finding — worth citing as a good design pattern, similar to
the WooCommerce QR-login note in the prior pass.

---

### A05:2021 – Security Misconfiguration

**Checked:** the `.htaccess`-writing logic itself
(`wpcf7_init_uploads()`) for a stale/bypassable rule (e.g. only writing
the Apache 2.2 or 2.4 block but not both, or skipping if the file already
exists with old content). It writes both syntaxes and re-checks the first
line of an existing file to detect and rewrite pre-2.4 versions.

**Result:** no finding.

---

### A06:2021 – Vulnerable and Outdated Components

**Checked:** `composer.json`/`package.json` — all runtime dependencies are
first-party (`rocklobsterinc/form-data-tree`, `rocklobsterinc/functions`,
`rocklobsterinc/swv`), maintained by the same author/org as the plugin
itself. No third-party dependency with a known-CVE version pin found.
`@wordpress/scripts` is a build-time-only devDependency (not shipped to
the runtime plugin).

**Result:** no finding.

---

### A07:2021 – Identification and Authentication Failures

Not applicable — CF7 has no login/session/authentication system of its
own; it relies entirely on WordPress core's.

---

### A08:2021 – Software and Data Integrity Failures

**Checked:** deserialization (none found — see A03), and the attachment
mechanism (`includes/mail.php` attachments filter): every attachment path
is validated with `wpcf7_is_file_path_in_content_dir()` before being
`path_join()`'d against `WP_CONTENT_DIR`, rejecting paths that would
escape it (path traversal in the attachment feature was also a historical
CVE class for this plugin, in older versions).

**Result:** no finding.

---

### A09:2021 – Security Logging and Monitoring Failures

Not meaningfully applicable to a client-side-installed plugin's own code
(no centralized logging infrastructure to assess).

---

### A10:2021 – Server-Side Request Forgery (SSRF)

**Checked:** outbound HTTP calls in the plugin (Akismet/reCAPTCHA/Stripe
module integrations). All target hardcoded, vendor-documented hosts
(`www.google.com/recaptcha/...`, Stripe's API, Akismet's API) — no
user-suppliable URL parameter found feeding into `wp_remote_get()`/
`wp_remote_post()`.

**Result:** no finding.

---

## Not covered this pass (scope limit)

The `modules/` directory has ~15 integration modules (Stripe, reCAPTCHA,
Constant Contact, Akismet, etc.) — reviewed representative ones (file,
mail-related) in depth; the payment (Stripe) and third-party API modules
were only spot-checked for the A10/A06 items above, not fully hand-reviewed
line by line.
