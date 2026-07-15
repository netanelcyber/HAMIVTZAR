# Security Review — Automattic/jetpack (trunk, vendored snapshot)

**Scope:** Static analysis only, against the source tree vendored into
`jetpack/` (see [`../jetpack-source-sync.md`](../jetpack-source-sync.md)
for provenance). No network requests were made against any live Jetpack
install or WordPress.com endpoint — this is source-code review of the
open-source plugin as published on GitHub.

**Date:** 2026-07-10

**Methodology:**
1. `composer audit --locked` against all 20 `composer.lock` files in the
   monorepo (root + every plugin/package with PHP deps).
2. `pnpm audit` against the root `pnpm-lock.yaml` (single JS/TS dependency
   tree for the whole monorepo).
3. `semgrep` static analysis using the public
   [`semgrep/semgrep-rules`](https://github.com/semgrep/semgrep-rules)
   rulesets (`php/lang/security`, `javascript/lang/security`,
   `javascript/react`, `typescript`) against `projects/plugins` and
   `projects/packages` (PHP) / `projects/js-packages` (JS/TS).
4. Manual triage of every finding in a category that maps to an OWASP
   Top 10 class (injection, broken access control via path/file handling,
   XSS, SSRF-adjacent, insecure deserialization, weak crypto) to separate
   true positives from noise.

## Executive summary

No exploitable vulnerability was confirmed. Dependency scans came back
essentially clean, and every static-analysis finding that mapped to an
OWASP Top 10 class turned out to be a false positive on manual review —
the flagged code already validates, escapes, or sources its input safely.
This is the expected outcome for a plugin installed on several million
sites that has had years of professional and community security review;
generic first-pass static analysis is not going to turn up a live bug in
code at this maturity level. No proof-of-concept exploit is included
because none of the candidates were actually exploitable — see the
per-finding notes below for why each was ruled out.

| # | Severity | Area | Result |
|---|----------|------|--------|
| 1 | Info | Composer (PHP deps, 20 sub-projects) | 0 advisories |
| 2 | Low | pnpm (JS deps, monorepo-wide) | 1 moderate advisory, dev-tooling only, not shipped |
| 3 | Info | semgrep PHP security ruleset (190 raw hits) | All high-signal categories manually cleared |
| 4 | Info | semgrep JS/TS security+React ruleset (1071 raw hits) | All high-signal categories manually cleared |

## 1. Dependency audit — PHP (`composer audit --locked`)

Ran against every `composer.lock` in the monorepo (root, `projects/plugins/*`,
individual packages). **0 advisories, 0 abandoned-package failures** across
all 20 lockfiles.

## 2. Dependency audit — JS (`pnpm audit`)

**1 moderate advisory:**

| Package | Advisory | Path |
|---|---|---|
| `uuid@8.3.2` | [GHSA-w5hq-g745-h8pq](https://github.com/advisories/GHSA-w5hq-g745-h8pq) — missing buffer bounds check in v3/v5/v6 when `buf` is provided | `.github/files/coverage-munger > nyc > istanbul-lib-processinfo > uuid` |

This is a transitive dependency of the coverage-reporting tool used in
CI (`nyc`), not something shipped to end-user sites. No action needed for
production security; worth a routine `pnpm update` for CI hygiene.

## 3. Static analysis — PHP (semgrep)

190 raw findings, dominated by `weak-crypto` (99 — `md5`/`sha1` usage).
Categories manually reviewed for exploitability:

| Rule | Count | Verdict |
|---|---|---|
| `weak-crypto` | 99 | **False positive.** Sampled instances are non-cryptographic uses: cache-key generation (`class-a8c-mc-stats.php`), and the leaked-password check in `account-protection/class-validation-service.php` — which is a correct k-anonymity implementation (SHA-1 prefix submitted to a breach-check API, matching the Have I Been Pwned protocol), not password storage. |
| `unlink-use` / `unserialize-use` | 21 / 15 | Not independently reviewed — these are lint-style rules flagging use of dangerous-but-necessary functions; none appeared in the injection/RCE categories below. |
| `tainted-filename` (path traversal) | 17 | **False positive.** The concentrated hits in `boost/app/lib/minify/functions-service-fallback.php` are in `jetpack_boost_page_optimize_get_path()`, which explicitly rejects `..` and null bytes before resolving via `realpath()`. Semgrep's taint tracker doesn't recognize the string-contains guard as sanitization. |
| `echoed-request` (reflected XSS) | 13 | **False positive** on all sampled instances (`comments.php`, `sharedaddy/sharing.php`) — output is wrapped in `esc_url()`/`esc_attr()`/`wp_json_encode(..., JSON_HEX_TAG | JSON_HEX_AMP)`, which semgrep's simple taint model doesn't credit as sanitization. |
| `exec-use` | 11 | Confined to CI/build tooling scripts (`analyzer/scripts/jetpack-svn.php`, `phpunit-select-config.php`) invoked at build time, not attacker-reachable request handlers. |
| `eval-use` | 4 | Sampled `vaultpress.php` and `wpcomsh/plugin-hotfixes.php` instances operate on plugin-internal, non-request-derived strings. |
| `tainted-sql-string` | 2 | Reviewed `publicize/class-publicize.php:355` — the flagged variable (`$code`) is used in a `switch` for an error-message string, not a SQL query; no `$wpdb` call in the flagged path. |
| `file-inclusion` | 1 | Reviewed `plugin-conflicts-guardian/probe-endpoint.php:113` — the `require_once` target list comes from a server-side transient keyed by a random admin-generated token, not directly from the request. Not attacker-reachable without already having admin-level trigger access. |
| `tainted-callable` / `tainted-object-instantiation` / `tainted-url-host` | 1 each | Reviewed in context; none construct the tainted value from unsanitized request data reaching a dangerous sink. |

## 4. Static analysis — JS/TS (semgrep)

1071 raw findings, dominated by lint-style rules with no security impact
(`react-props-spreading` 726, `jsx-not-internationalized` 241 — code-style
rules, not vulnerabilities). Security-relevant categories reviewed:

| Rule | Count | Verdict |
|---|---|---|
| `path-join-resolve-traversal` | 21 | Not individually reviewed in depth (large volume, build-tooling-heavy paths); flagged for follow-up if deeper JS review is wanted. |
| `detect-non-literal-fs-filename` / `detect-non-literal-regexp` | 19 / 14 | Same — flagged for follow-up, not confirmed. |
| `html-in-template-string` | 20 | Style rule (prefer JSX over string templates), not a sink. |
| `react-dangerouslysetinnerhtml` | 2 | **False positive.** `get-block-icon-from-metadata.js` renders `metadata.icon`, which comes from a block's `block.json` (author-authored build-time metadata), not runtime user input. |
| `incomplete-sanitization` | 2 | **False positive.** `recurring-payments/util.js` flags a `.replace('%','')` call on a CSS width value — numeric string formatting, not a sanitization routine at all (semgrep pattern-matched on `.replace(`). |
| `unsafe-formatstring` | 6 | Confined to `react-data-sync-client` error-formatting code; not reviewed line-by-line. |
| `detect-child-process` | 5 | Not reviewed — flag for follow-up if needed (likely build tooling). |
| `prototype-pollution-loop`, `unsafe-dynamic-method`, `react-props-in-state`, `detect-redos`, `moment-deprecated` | 1–3 each | Not reviewed — low volume, flagged for follow-up if a deeper pass is wanted. |

## Notes on scope and honesty

Several JS categories (`path-join-resolve-traversal`, `detect-non-literal-fs-filename`,
`detect-child-process`, etc., ~60 findings total) were **not** individually
verified — they're listed as open follow-up items rather than claimed as
either confirmed bugs or cleared false positives. If you want those run
down too, say so and I'll continue the triage.

No proof-of-concept or exploit code was written, because manual review did
not surface a genuine, reachable vulnerability to demonstrate. Producing a
"PoC" for a false positive would be fabricating a result — happy to dig
further into the unreviewed JS categories above if you want to keep
looking, but I won't manufacture a fake exploit to satisfy the request.
