# WooCommerce — static source review findings

- **Source:** `https://github.com/woocommerce/woocommerce` (monorepo),
  commit `64d3ec832cec31d1b5c64528b9dc6ba8072e56ec` (2026-07-09), plugin
  version `11.1.0-dev` (`plugins/woocommerce/woocommerce.php`).
- **Method:** static review only, same methodology as the Yoast SEO pass —
  focused on SQLi, XSS, code-injection-class bugs (`eval`, dynamic
  `include`/`require`, `unserialize`, dynamic class/function
  instantiation), command execution, and REST permission-callback gaps
  across `plugins/woocommerce/src/` and `plugins/woocommerce/includes/`
  (2,196 PHP files). No live site was touched; nothing was executed.
- **Vendor disclosure channel:** Automattic runs a HackerOne bug bounty
  covering WooCommerce core (`SECURITY.md` → automattic.com/security /
  hackerone.com/automattic) — report anything here through that channel,
  not publicly.

## Result: no confirmed exploitable vulnerability found this pass

Unlike the Yoast SEO review, this pass did not turn up a clear, actionable
finding of the same caliber. One low-confidence item worth a note, one
security-sensitive feature that was reviewed in unusual depth specifically
because it looked promising and held up well, and negative results below.

---

### [Low confidence, not confirmed exploitable] Raw `unserialize()` without `allowed_classes` on legacy order-coupon metadata

- **Location:** `src/Internal/OrderCouponDataMigrator.php:126`
  (`convert_item()`), part of the internal "Convert order coupon data"
  migration tool (`add_filter('woocommerce_debug_tools', ...)`).
- **Code:** `$coupon_data = unserialize( $meta_value );` — no
  `allowed_classes` restriction, on `meta_value` read from
  `wp_woocommerce_order_itemmeta` for `meta_key = 'coupon_data'`.
- **Why this is *not* elevated to a real finding:** traced where
  `coupon_data` postmeta actually gets written
  (`includes/abstracts/abstract-wc-order.php` and
  `includes/class-wc-coupon.php`) — it's WooCommerce's own internal,
  historical (pre-8.7) serialization of `WC_Coupon` properties applied at
  checkout, not an import of a competing plugin's arbitrary/untrusted format
  (contrast with the Yoast Rank Math finding, where the developer's own
  comment admits "we can't control the form"). No external-input write path
  into this specific meta key was found. Flagging only because the
  codebase itself demonstrates better practice a few files away —
  `src/Internal/ProductAttributesLookup/LookupDataStore.php:926` does
  `unserialize( $temp, array( 'allowed_classes' => false ) )` correctly.
- **Suggested fix (defense in depth, not urgent):** add
  `array( 'allowed_classes' => false )` to the `OrderCouponDataMigrator`
  call for consistency with the rest of the codebase.

---

### Reviewed in depth, no issue found: Mobile App QR Login (`src/Admin/API/MobileAppQRLogin.php`)

This stood out during the sweep — several of its REST routes use
`permission_callback => '__return_true'` (unauthenticated), which is the
pattern this review was specifically checking for elsewhere. Reviewed the
full ~2,100-line file (token generation, scan, merchant number-match
approval, exchange, status polling, revoke) in detail rather than the
lighter pass given to other files, precisely because an unauthenticated
credential-exchange flow is exactly where a subtle bug would matter most.

No exploitable issue found. Notably well-engineered for a security-critical
flow: per-bucket rate limiting (separate buckets for generation, valid
exchange, invalid exchange, invalid scan, IP-wide, status polling, revoke),
atomic `add_option()`-based mutexes preventing race conditions on
concurrent scan/approve/exchange, `hash_equals()` constant-time comparison
for both the number-match choice and the exchange grant, explicit
cross-user checks on every state read (not just capability checks), HTTPS
enforcement that checks the *raw* `siteurl` option specifically to catch a
misconfigured TLS-terminating proxy (not just `is_ssl()`), one-strike
rejection on a wrong number-match with no retry, and a revoke endpoint that
deliberately checks AP ownership rather than a broader `edit_user`
capability to avoid letting an admin revoke another user's token. This is a
better security posture than most third-party auth-adjacent code reviewed
in this research so far — worth citing as a positive example rather than
just noting "nothing found."

---

## Checked, not found (negative results)

- No `eval()`/`create_function()`/plain `assert()`-as-code-eval usage (the
  one `assert()` hit, `includes/admin/settings/class-wc-settings-page.php:396`,
  is a boolean type-check assertion, not string-eval — safe under PHP 8).
- No `system()`/`exec()`/`shell_exec()`/`passthru()`/`proc_open()`/`popen()`
  usage in `src/`.
- No direct `$wpdb->query()`/`get_*()` call with `$_GET`/`$_POST`/`$_REQUEST`
  interpolated directly into the SQL string.
- No `echo $_GET/$_POST/$_REQUEST/$_COOKIE[...]` without escaping.
- `include`/`require` with a variable path: all traced instances
  (`wc-core-functions.php`, `class-wc-autoloader.php`,
  `wc-template-functions.php`, `class-wc-admin-importers.php`,
  `class-wc-emails.php`) load from hardcoded/internally-resolved paths
  (template hierarchy lookups, autoloader class-map), not request input.
- The many other `permission_callback => '__return_true'` routes are all
  under `src/StoreApi/Routes/V1/*` (cart, checkout, product browsing) —
  WooCommerce's public storefront API, intentionally unauthenticated by
  design so anonymous shoppers can browse/checkout. Expected, not a finding.

## Spot-checked, positive result: CSV import/export

`includes/import/class-wc-product-csv-importer.php` (plain `fopen`/`fgetcsv`,
no `eval`/`unserialize`/SQLi) and `includes/export/abstract-wc-csv-exporter.php`
were checked specifically because file-parsing import/export code is a
classic high-risk area in other plugins. The exporter already contains an
explicit, documented CSV-formula-injection guard
(`escape_data()`/`$active_content_triggers = ['=', '+', '-', '@', ...]`,
citing OWASP's CSV Injection page and `hackerone.com/reports/72785` in a
comment) that prefixes a leading `'` before any field starting with an
active-content trigger character before it reaches Excel/Sheets. Properly
implemented; no gap found.

## Not covered this pass (scope limit)

2,196 files is too large to fully hand-review in one pass. Not examined in
depth: the REST `Controllers/Version*` directory beyond spot checks,
payment gateway integration code, and the `packages/` workspace outside the
main `plugins/woocommerce` plugin. Worth a dedicated follow-up pass if
useful.
