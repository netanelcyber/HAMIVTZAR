# Expert Lawyer (WordPress theme, Luzuk) — static source review findings (OWASP Top 10 + CWE structured)

- **Source:** user-supplied ZIP (`expertlawyer.1.3.7.zip`), theme slug `expert-lawyer`,
  version `1.3.7` (per `style.css`/`readme.txt` header), vendor Luzuk
  (`https://www.luzuk.com/`). Not a live site — a theme package only.
- **Method:** full-file static read of every one of the 38 PHP files shipped
  (root template files, `inc/`, `page-template/`, `template-parts/`
  — including all page/post templates, per the requested scope — and
  `woocommerce/`). No live WordPress installation was targeted or tested.
- **Vendor disclosure channel:** no dedicated security contact found for
  Luzuk; would need to go through the WordPress.org theme review team
  (this theme is distributed via wordpress.org/themes/expert-lawyer/) or
  Patchstack/WPScan.
- **Prior-disclosure check:** no CVE found for the "Expert Lawyer" theme
  itself. Luzuk (the same vendor) has three existing, currently-unpatched
  CVEs for *other* products — CVE-2024-51782 (Luzuk Slider, XSS),
  CVE-2024-51834 (Luzuk Team, XSS), CVE-2024-51871 (Luzuk Testimonials,
  XSS) — establishing a track record of shipping XSS-class bugs and not
  fixing them promptly. Treat that as relevant context, not as evidence
  about this theme's own code.

## Summary

Theme-wide output escaping is actually solid: all 77 Customizer settings
have an allowlist/type-appropriate `sanitize_callback`, and essentially
every template echoes Customizer/query values through `esc_html()`/
`esc_attr()`/`esc_url()`. One real finding stands out, and it's a
supply-chain one rather than a classic injection: the theme's own
"Themes Dashboard" admin page fetches and blindly `echo`s two remote HTML
files from the vendor's public GitHub repo, with no output sanitization
and no integrity/signature check at all.

---

### A08:2021 – Software and Data Integrity Failures (CWE-829, CWE-494)

**[Medium-High] Remote, unauthenticated, unsanitized HTML fetched from GitHub and echoed directly into wp-admin**

- **Location:** `functions.php`, `expert_lawyer_render_combined_dashboard()`
  (lines ~388–410), rendered via `expert_lawyer_themes_dashboard_page()` →
  registered with `add_theme_page( ..., 'manage_options', 'themes-dashboard', 'expert_lawyer_themes_dashboard_page' )`.
- **Description:**
  ```php
  $dashboard_url = 'https://raw.githubusercontent.com/LuzukThemes/themes-dashboard/main/dashboard.html';
  $dashboard_response = wp_remote_get($dashboard_url);
  $dashboard_html = wp_remote_retrieve_body($dashboard_response);
  ...
  <?php echo $dashboard_html; ?>
  ```
  and identically for `coupon.html`. Both bodies are fetched fresh on every
  page load (no caching/transient) and `echo`'d with **zero sanitization**
  (no `wp_kses_post()`, no escaping of any kind) directly into an
  admin-rendered page.
- **Why this matters architecturally:** the content executed in an
  admin's browser is entirely controlled by whatever is currently sitting
  in `LuzukThemes/themes-dashboard` on GitHub at request time — not
  pinned to any hash, not signed, not shipped with the theme package. This
  is the classic "remote-controlled admin content" supply-chain pattern:
  it is safe *only* as long as that one GitHub repo/account is never
  compromised. If it ever is (stolen GitHub token, disgruntled/former
  contributor, session hijack, or the repo being renamed/transferred),
  every site running this theme (and, per the shared `themes-dashboard`
  repo name, likely every other Luzuk theme too) would render arbitrary
  attacker HTML/JavaScript with full `manage_options` admin-session
  privileges the moment an admin opens Appearance → Themes Dashboard —
  i.e., immediate full site takeover (rogue admin creation, arbitrary
  plugin install via the already-authenticated session, etc.), no
  additional bug needed. This is the same *class* of impact (remote
  content trusted into an authenticated admin context) that has been
  actively exploited in real WordPress-theme incidents in the wild (see
  e.g. the July 2025 "Alone" theme remote-plugin-install campaign covered
  by The Hacker News — a different bug, same "untrusted remote content
  reaches privileged admin action" shape).
- **Secondary observation (not a vulnerability by itself, but relevant
  context):** `expert_lawyer_hide_admin_notices_on_custom_page()` actively
  calls `remove_all_actions('admin_notices')` /
  `remove_all_actions('all_admin_notices')` /
  `remove_all_actions('network_admin_notices')` specifically on this
  screen — suppressing *all* admin notices, including other plugins'
  security/update warnings, while the vendor's own remotely-fetched
  promotional content is displayed. A dark UX pattern, and it also means
  a compromised remote payload wouldn't be competing with any WordPress
  core security notice for the admin's attention on that screen.
- **Preconditions / who can trigger it:** requires an admin
  (`manage_options`) to visit Appearance → Themes Dashboard — this is the
  page WordPress itself would nudge them toward right after activating
  the theme, so in practice this is a "visited by nearly every installer"
  screen, not an obscure one.
- **Remediation:**
  - Don't remote-fetch executable-adjacent HTML into an authenticated
    admin context at all; ship the dashboard/coupon content statically in
    the theme package and update it via normal theme version releases.
  - If remote content must be kept, at minimum sanitize with
    `wp_kses_post()` (or a strict custom allowlist) before output, and add
    integrity verification (e.g., a pinned hash checked before rendering,
    or fetch over a signed/versioned release asset rather than a mutable
    `main` branch raw file).
  - Cache the fetched content (transient) instead of re-fetching on every
    page load, independent of the security fix.

---

### A03:2021 – Injection (Cross-Site Scripting)

No unescaped `echo`/`print` of request input or Customizer data was found
outside the case above. Specifically checked and confirmed safe:
- `page-template/custom-home-page.php:55` echoes
  `get_theme_mod('expert_lawyer_slider_effect')` unescaped, but that
  setting's `sanitize_callback` (`expert_lawyer_sanitize_choices`)
  allowlists the value against the registered dropdown's own `choices`
  array — an attacker (already requiring `edit_theme_options` capability
  to set it in the first place) cannot make it anything other than one of
  the theme's own fixed CSS class name options.
- `template-parts/post/content-audio.php` / `content-video.php` echo
  `$audio_html`/`$video_html` raw, but these come from WordPress core's
  own `get_media_embedded_in_content()` (author-authored post content,
  identical pattern to WordPress's default themes) — not
  request-influenced.
- All 77 Customizer settings in `inc/customizer.php` carry an appropriate
  `sanitize_callback` (verified 1:1 against `add_setting()` calls); custom
  callbacks (`expert_lawyer_sanitize_choices`, `_checkbox`, `_float`,
  `_phone_number`) were individually read and are sound (allowlist /
  type-cast, no pass-through).
- `searchform.php` correctly escapes `get_search_query()` via
  `esc_attr()`.

---

### A05:2021 – Security Misconfiguration

`inc/wptt-webfont-loader.php` (the widely-used, publicly-maintained WPTT
Webfont Loader library for self-hosting Google Fonts) is bundled but only
ever invoked (`functions.php:172`, `expert_lawyer_fonts_url()`) with a
hardcoded `fonts.googleapis.com` URL built from fixed font-family strings
— not attacker- or admin-influenced input reaches its remote-fetch/
file-write logic in this theme's usage.

## Not covered this pass (scope limit)

`inc/custom-header.php` (custom-header image support, thin/standard core
wrapper) and the `woocommerce/*` templates were read in full and contain
no logic beyond markup wrapper `echo` of static strings — no findings, not
because they were skipped, but because there was nothing beyond static
HTML structure to analyze there.
