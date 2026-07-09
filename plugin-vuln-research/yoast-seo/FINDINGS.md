# Yoast SEO — static source review findings

- **Source:** `https://github.com/Yoast/wordpress-seo`, commit
  `0a4c8014a4eaa1c9dbb086ec3fbdb549d47f847a` (2026-07-08), version
  `28.1-RC2` / stable tag `28.0`.
- **Method:** static review only (grep-driven data-flow tracing, same
  methodology used against WordPress core), focused on SQL injection, XSS,
  auth/nonce gaps, and code-injection-class bugs (`eval`, dynamic
  `include`/`require`, `unserialize`, dynamic class/function instantiation,
  command execution). No live site was touched; nothing was executed.
- **Prior disclosure check:** searched public sources for both findings
  below; found no exact match, but Patchstack's and wp-safety.org's plugin
  pages returned HTTP 403 to automated fetches from this environment, so
  that check is **inconclusive, not a clean bill of health** — re-verify
  against Patchstack/WPScan/the plugin's own changelog before disclosing.

---

## [Medium] Arbitrary class instantiation from unsanitized POST input, bypassing the plugin's own importer allowlist

- **Location:** `admin/views/tool-import-export.php`, both branches:
  - Import: lines 24–32 (`$_POST['import_external_plugin']`)
  - Cleanup: lines 35–43 (`$_POST['clean_external_plugin']`)
- **Code:**
  ```php
  if ( isset( $_POST['import_external'] ) && wp_unslash( $_POST['import_external'] ) === __( 'Import', 'wordpress-seo' ) ) {
      check_admin_referer( 'wpseo-import-plugins' );
      if ( isset( $_POST['import_external_plugin'] ) && is_string( $_POST['import_external_plugin'] ) ) {
          $yoast_seo_class = wp_unslash( $_POST['import_external_plugin'] );
          if ( class_exists( $yoast_seo_class ) ) {
              $yoast_seo_import = new WPSEO_Import_Plugin( new $yoast_seo_class(), 'import' );
          }
      }
  }
  ```
- **Description:** the plugin already maintains an explicit allowlist of
  supported importer classes — `WPSEO_Plugin_Importers::get()`
  (`admin/import/plugins/class-importers.php`), used correctly elsewhere
  (e.g. `admin/import/class-import-detector.php`). This code path doesn't
  consult it. Instead it takes the raw POST value, checks only
  `class_exists()`, and calls `new $yoast_seo_class()` directly. Because PHP
  evaluates `new $yoast_seo_class()` *before* checking the
  `WPSEO_Plugin_Importer` type-hint on `WPSEO_Import_Plugin::__construct()`,
  the constructor of **any class currently loaded in the request** — WP
  core, Yoast itself, or any other active plugin/theme — runs with attacker
  control over which class, before the type-hint mismatch (if any) surfaces
  as a `TypeError`.
- **Preconditions:** requires an authenticated user with access to the Yoast
  SEO Tools admin page (`manage_options`/`wpseo_manage_options`) and a valid
  `wpseo-import-plugins` (or `wpseo-clean-plugins`) nonce — i.e., this is
  reachable only by a user who is already an administrator (or has been
  granted Yoast's manage-options-equivalent capability). It is not a
  privilege-escalation path by itself.
- **Impact:** classic CWE-470 (unsafe reflection / externally-controlled
  class selection). Real-world impact is bounded by the admin-only
  precondition, but it's a genuine missing-validation bug with a ready-made
  fix already sitting in the codebase: if any other active plugin/theme
  exposes a class whose bare constructor has a meaningful side effect
  (writes a file, calls an external service, mutates state), an admin
  session (or an admin tricked via a chained CSRF/XSS elsewhere, since the
  nonce only proves same-origin-with-valid-nonce, not developer intent) can
  trigger that side effect through this endpoint without it being one of
  the plugin's own intended importers.
- **Remediation:** validate `$yoast_seo_class` against
  `WPSEO_Plugin_Importers::get()` *before* instantiating anything, e.g.:
  ```php
  if ( in_array( $yoast_seo_class, WPSEO_Plugin_Importers::get(), true ) && class_exists( $yoast_seo_class ) ) {
      ...
  }
  ```

---

## [Medium, conditional] Unsafe deserialization of imported plugin postmeta (CWE-502)

- **Primary location:** `admin/import/plugins/class-import-rankmath.php:120`
  ```php
  // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions -- Reason: We can't control the form in which Rankmath sends the data.
  $robots_values = unserialize( $post_meta->meta_value );
  ```
  reached via `import_meta_robots()` iterating
  `$wpdb->get_results("SELECT post_id, meta_value FROM $wpdb->postmeta WHERE meta_key = 'rank_math_robots'")`
  — i.e., every row's `meta_value` currently stored under that key gets
  unserialized, unconditionally, for a plain `unserialize()` call with no
  `allowed_classes` restriction.
- **Same underlying pattern, softer wrapper**, in three sibling importers
  (via `maybe_unserialize()` rather than raw `unserialize()`):
  - `admin/import/plugins/class-import-aioseo.php:104`
  - `admin/import/plugins/class-import-squirrly.php:205`
  - `admin/import/plugins/class-import-smartcrawl.php:118`

  Note `maybe_unserialize()` (WordPress core, `wp-includes/functions.php`)
  only guards against non-serialized garbage via `is_serialized()` before
  calling `@unserialize(trim($data))` — it does **not** pass
  `['allowed_classes' => false]`, so it provides no protection against
  object injection once the string is well-formed serialized data. This was
  confirmed directly against WordPress core source in this same research
  effort.
- **Preconditions (all required):**
  1. A postmeta row with the relevant key (`rank_math_robots`,
     `aioseo_*`, etc.) contains attacker-influenced serialized data. Plausible
     on any site migrating from the competing plugin, or via any other
     plugin/vector that allows postmeta writes (lower-privileged custom
     fields, a separate vulnerable plugin, a compromised import/export
     feature, etc.) — this is exactly the class of precondition these
     importers exist to consume.
  2. An administrator runs the corresponding "Import from X" tool
     (`admin/views/tool-import-export.php`, gated by the same
     `wpseo-import-plugins` nonce + `manage_options`-level capability as
     Finding 1).
  3. A usable POP gadget chain exists among classes loaded by WordPress
     core or any other currently-active plugin/theme at that moment (as
     with any PHP object-injection finding — exploitability depends on the
     rest of the site's installed code, not on Yoast SEO alone).
- **Impact:** if a gadget chain is available, ranges from data
  tampering/DoS up to remote code execution, contingent on precondition 3.
  Without a known gadget chain present, the practical impact is denial-of-
  service/import-corruption at worst. This is the same vulnerability class
  as numerous historical WordPress plugin CVEs involving import/migration
  features that deserialize data from a competing plugin's stored settings.
- **Remediation:** replace `unserialize( $post_meta->meta_value )` with
  `unserialize( $post_meta->meta_value, [ 'allowed_classes' => false ] )` in
  all four locations (this still allows the scalar/array `robots_values`
  format these importers expect, since the imported data is a plain array,
  never a plugin-defined object) — this alone closes the object-injection
  angle regardless of gadget-chain availability elsewhere on the site.

---

## Checked, not found (negative results, for completeness)

Within `src/` (the modern, namespaced codebase) and spot-checks of
`admin/`/`inc/`:

- No `eval()`/`create_function()`/`assert()` usage.
- No `system()`/`exec()`/`shell_exec()`/`passthru()`/`proc_open()`/`popen()`
  usage.
- No direct `echo $_GET/$_POST/$_REQUEST/$_COOKIE[...]` without escaping.
- No `wp_ajax_nopriv_*` handlers in `src/`.
- SQL: all `$wpdb->query()`/`get_*()` calls in `src/` either use
  `$wpdb->prepare()` upstream or interpolate only hardcoded
  table/column-name literals (never request input) plus DB-sourced integer
  IDs — no injectable string reaches a query. (Minor hardening nit, not a
  vulnerability: `indexable-cleanup-repository.php` implodes `$orphans`
  arrays — always integer primary keys from a prior `SELECT` — directly
  into an `IN (...)` clause instead of casting via
  `array_map('absint', $orphans)` first; not exploitable since the values
  never originate from request input, but worth tightening as defense in
  depth.)
- `require_once $path` in `src/helpers/require-file-helper.php:18` — `$path`
  traced back to a hardcoded plugin-relative path, not request-influenced.
