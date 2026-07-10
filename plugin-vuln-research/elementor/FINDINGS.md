# Elementor Website Builder — static source review findings (OWASP Top 10 structured)

- **Source:** `https://github.com/elementor/elementor` (official active
  repo), commit `0b8e0eebe599c433ab120f4ce112e22a8568e69d` (2026-07-09),
  version `4.3.0`.
- **Method:** static review, OWASP Top 10 (2021) structure, same as the
  Contact Form 7 pass. 1,740 PHP files — a page builder has a much larger
  attack surface (widget rendering, AJAX-driven editor, template
  import/export) than the plugins reviewed so far, so this pass leans on
  targeted checks of the highest-risk subsystems rather than a full
  line-by-line read of every file.
- **Vendor disclosure channel:** Elementor runs its own bug bounty via
  Bugcrowd (per their published security policy) — that's the right venue
  for anything found here, not WPScan/Patchstack directly.
- **Prior disclosure check:** not separately searched per-finding this
  pass given the note below is a shared upstream pattern, not a novel
  Elementor-specific bug (see A08).

## Result: no confirmed exploitable vulnerability found this pass

---

### A01:2021 – Broken Access Control

**Checked:** AJAX handlers (`wp_ajax_*`/`wp_ajax_nopriv_*`). Only two
`nopriv` (public) registrations exist:

- `core/base/background-process/wp-async-request.php` — Elementor's
  vendored copy of the well-known `WP_Async_Request` base class (also used
  by WooCommerce and Jetpack, reviewed in prior passes); the `nopriv` hook
  is required by design so a background task can loopback-request itself
  without an authenticated session, and it's gated by an unguessable
  per-request identifier, not user input.
- `modules/floating-buttons/module.php`'s `elementor_send_clicks` (click
  analytics for a public-facing widget) — validates input via
  `filter_input_array()` with `FILTER_VALIDATE_INT`/`FILTER_REQUIRE_ARRAY`
  and checks a nonce (`wp_verify_nonce()`) before proceeding. Appropriately
  public (anonymous visitors trigger it by clicking a widget) with
  sensible input validation.

Did not find an editor-facing (content-modifying) AJAX action registered
`nopriv` or without a capability check.

**Result:** no finding.

---

### A02:2021 – Cryptographic Failures

**Checked:** nonce usage patterns, no custom crypto or hardcoded secrets
found in the areas reviewed.

**Result:** no finding.

---

### A03:2021 – Injection

**Checked:** no `$wpdb` raw-query call found with `$_GET`/`$_POST`/
`$_REQUEST` interpolated directly; no `eval()`/`create_function()`
anywhere in the plugin; no direct unescaped echo of request superglobals
found in the areas reviewed.

**Result:** no finding.

---

### A04:2021 – Insecure Design

Not separately assessed beyond A01/A08 this pass — would need a deeper
look at the editor's data-saving pipeline (how widget/page-settings JSON
is validated server-side) to say more; out of scope for this pass's depth.

---

### A05:2021 – Security Misconfiguration

Not separately assessed this pass.

---

### A06:2021 – Vulnerable and Outdated Components

Not checked this pass (would require reviewing `composer.json` and the
bundled third-party libraries under a vendor-equivalent directory, not yet
located/reviewed).

---

### A07:2021 – Identification and Authentication Failures

Not applicable — relies entirely on WordPress core's session/auth system,
same as the other plugins reviewed.

---

### A08:2021 – Software and Data Integrity Failures

**Checked:** `unserialize()`/`maybe_unserialize()` call sites.

- **Shared upstream pattern, not a novel Elementor bug:**
  `core/utils/import-export/wp-import.php` is Elementor's adapted copy of
  the **official WordPress Importer plugin's** `class-wp-import.php` (the
  file's own header comment says so explicitly — "Originally made by
  WordPress part of WordPress/Importer"). It calls `maybe_unserialize()` on
  postmeta values read from an imported WXR/XML file, the same pattern
  present in the official `wordpress-importer` plugin itself. This is
  gated behind `import`-level capability (admin-only) to reach at all, and
  since it's inherited from a widely-used, already-publicly-scrutinized
  upstream component rather than something Elementor wrote from scratch,
  it isn't written up as a distinct Elementor finding — flagging it here
  for the record since it's the same vulnerability *class* as the Yoast
  SEO and Jetpack findings in this research, just via shared/vendored
  code rather than a plugin-specific bug.
- **Checked, not exploitable:** `modules/site-navigation/data/endpoints/duplicate-post.php:128`
  and `core/base/background-process/wp-background-process.php:337` both
  operate on the plugin's own already-existing DB data (duplicating
  postmeta from one existing post to a new one; resuming an internally
  queued background-task batch) — no external-input write path into either.

**Result:** no new finding (one shared-upstream-pattern note, not scored
as a distinct Elementor vulnerability).

---

### A09:2021 – Security Logging and Monitoring Failures

Not applicable / not assessed.

---

### A10:2021 – Server-Side Request Forgery (SSRF)

Not checked in depth this pass — Elementor has remote font/library/kit
import features that would be the natural place to look (fetching a
user-supplied URL server-side); flagged as a priority for a deeper
follow-up pass rather than covered here.

---

## Not covered this pass (scope limit)

1,740 files is large. This pass covered AJAX/capability patterns,
deserialization call sites, and a quick injection sweep — it did **not**
cover: the editor's REST/AJAX data-saving pipeline in depth (A04), remote
kit/template import via URL (A10 priority), bundled third-party libraries
(A06), or the dynamic-tags/widget-rendering system's output-escaping
consistency (a large surface for stored XSS in a page builder — spot
checks found `esc_attr()`/`esc_html()` used consistently where sampled,
but this wasn't exhaustively verified across all ~1,740 files). Recommend
a dedicated follow-up pass focused specifically on A10 and the
render/save pipeline given Elementor's size and editor-heavy design.
