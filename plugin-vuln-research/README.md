# Plugin vulnerability research — popular WordPress plugins

Static source-code security review of widely-installed, open-source
WordPress plugins, for responsible disclosure. This is source-code auditing
only — no live WordPress site is targeted, tested, or exploited. Each
plugin's source is cloned from its official public GitHub repository (not a
site running it) and reviewed the same way `../` reviewed WordPress core
itself.

## Rules for this research

- **Public source only.** Clone the plugin's official open-source
  repository; never point tooling at a live, third-party production site
  without a separate, explicit, scoped authorization (see
  `../pentest-milatova/scope.md` for what that looks like when it applies).
- **Static analysis only.** Read code, trace data flow, check against known
  CVE databases where reachable. Nothing is executed, no exploit is fired
  against any running instance.
- **No weaponization.** A finding here documents the vulnerability class,
  the vulnerable code location, preconditions, and remediation — enough for
  the vendor to fix it and for a defender to assess exposure. It does not
  include ready-to-run exploit scripts targeting live installs.
- **Responsible disclosure.** Anything found gets reported to the plugin's
  own security contact / Patchstack / WPScan / Wordfence, on a reasonable
  disclosure timeline — not published as a public exploit.
- Before writing something up as a "finding," search for whether it's
  already publicly known/patched (CVE databases, vendor changelog). Note in
  the report if that check was inconclusive rather than skipping it.
- **OWASP Top 10 (2021) structure.** Starting with the Contact Form 7 pass,
  findings reports are organized under OWASP Top 10 categories (A01 Broken
  Access Control, A02 Cryptographic Failures, A03 Injection, ... A10 SSRF)
  rather than an ad-hoc vulnerability-class list, so coverage per category
  is explicit — including categories with no findings, so the absence is a
  documented negative result, not silence.
- **CWE IDs.** Starting with the WPForms pass, each individual finding also
  carries a specific CWE number (e.g. CWE-502, CWE-494) alongside its OWASP
  category, so severity/class is precise rather than just the broad OWASP
  bucket.

## Plugins reviewed

| Plugin | Slug | Status |
|---|---|---|
| Yoast SEO | `wordpress-seo` | [`yoast-seo/FINDINGS.md`](yoast-seo/FINDINGS.md) — 2 findings |
| WooCommerce | `woocommerce` | [`woocommerce/FINDINGS.md`](woocommerce/FINDINGS.md) — 0 confirmed, 1 low-confidence note |
| Jetpack | `jetpack` | [`jetpack/FINDINGS.md`](jetpack/FINDINGS.md) — 1 finding (low-medium) |
| Contact Form 7 | `contact-form-7` | [`contact-form-7/FINDINGS.md`](contact-form-7/FINDINGS.md) — 0 confirmed (OWASP-structured) |
| UpdraftPlus | `updraftplus` | blocked — see note below |
| Akismet Anti-Spam | `akismet` | blocked — see note below |
| Elementor Website Builder | `elementor` | [`elementor/FINDINGS.md`](elementor/FINDINGS.md) — 0 confirmed (OWASP-structured, partial coverage) |
| All in One SEO | `all-in-one-seo-pack` | [`all-in-one-seo/FINDINGS.md`](all-in-one-seo/FINDINGS.md) — 1 finding (medium, SSRF) + 2 known CVEs confirmed patched |
| WPForms Lite | `wpforms-lite` | [`wpforms/FINDINGS.md`](wpforms/FINDINGS.md) — 1 finding (high, conditional — CWE-494/CWE-306) |
| Classic Editor | `classic-editor` | [`classic-editor/FINDINGS.md`](classic-editor/FINDINGS.md) — 0 confirmed (full file read) |
| Really Simple Security | `really-simple-ssl` | [`really-simple-security/FINDINGS.md`](really-simple-security/FINDINGS.md) — 0 confirmed, 1 low-medium note (CWE-327) |
| LiteSpeed Cache | `litespeed-cache` | not started |
| Wordfence Security | `wordfence` | not started |
| MonsterInsights | `google-analytics-for-wordpress` | not started |
| Advanced Custom Fields | `advanced-custom-fields` | not started |
| Rank Math SEO | `seo-by-rank-math` | not started |

Ranks 6-16 above are a best-effort candidate list based on general
knowledge of long-standing popular WordPress plugins, not a live fetch —
`wordpress.org`/`api.wordpress.org` are blocked by this environment's
egress policy, so there's no way to pull the actual current "Popular"
ranking from here. Treat the ordering as approximate.

**UpdraftPlus** has no dedicated actively-maintained dev GitHub repo (unlike
Yoast/WooCommerce/Jetpack/CF7). The only mirrors reachable from this
environment (`wp-plugins/updraftplus`, `WPPlugins/updraftplus` — community
SVN-mirror bots) are stale, frozen at 2015 (v1.11.3) and 2017 (v1.13.4)
respectively — auditing either would mean reviewing decade-old code and
presenting it as current, which isn't useful for real disclosure. Skipped
until a current source is available (e.g. the user supplies a zip/current
mirror, or wordpress.org's SVN becomes reachable).

**Akismet** has the same problem: no dedicated actively-maintained dev
GitHub repo (Automattic ships it as part of the WordPress.org plugin
directory and their VIP mu-plugins bundle, not a standalone dev repo), and
the only community SVN mirror reachable from here (`wp-plugins/akismet`)
is frozen at 2015 (v3.1.6a1). Skipped for the same reason as UpdraftPlus.

**WPForms Lite** also has no dedicated dev repo, but its `common-repository`
mirror is at least reasonably recent (2024-11-01, v1.9.1.6, vs. the current
v1.9.9.2+) — reviewed with that freshness gap explicitly caveated in
`wpforms/FINDINGS.md`; any finding there should be re-verified against the
current release before disclosure.
