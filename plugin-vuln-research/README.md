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

## Plugins reviewed

| Plugin | Slug | Status |
|---|---|---|
| Yoast SEO | `wordpress-seo` | [`yoast-seo/FINDINGS.md`](yoast-seo/FINDINGS.md) — 2 findings |
| WooCommerce | `woocommerce` | [`woocommerce/FINDINGS.md`](woocommerce/FINDINGS.md) — 0 confirmed, 1 low-confidence note |
| Jetpack | `jetpack` | [`jetpack/FINDINGS.md`](jetpack/FINDINGS.md) — 1 finding (low-medium) |
| UpdraftPlus | `updraftplus` | not started |
| Contact Form 7 | `contact-form-7` | not started |
| Akismet Anti-Spam | `akismet` | not started |
| Elementor Website Builder | `elementor` | not started |
| All in One SEO | `all-in-one-seo-pack` | not started |
| WPForms Lite | `wpforms-lite` | not started |
| Classic Editor | `classic-editor` | not started |
| Really Simple Security | `really-simple-ssl` | not started |
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
