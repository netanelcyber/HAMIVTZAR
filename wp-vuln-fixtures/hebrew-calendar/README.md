# Hebrew Calendar Widget — Intentionally Vulnerable Test Fixture

A small, real WordPress plugin (Gregorian↔Hebrew date conversion, with a DB
cache) that deliberately contains two classic vulnerability classes, so it
can be used as a **known-vulnerable target** for validating scanners, WAF
rules, or this repo's own security tooling. It is not a real product and
must never be deployed anywhere reachable from the internet.

## ⚠️ Safe usage only

- Run it **only** on a disposable, network-isolated WordPress install: local
  Docker/`wp-env`/VM, no public exposure, throwaway database.
- Do not activate it on any staging or production site.
- Treat everything in this directory as attack-surface, not as example code
  to copy into a real plugin.

## What's intentionally broken

`hebrew-calendar-vuln-fixture.php` has every vulnerable line tagged
`INTENTIONAL VULN (test fixture)`:

1. **SQL injection** (shortcode `[hebrew_calendar date="..."]` and the AJAX
   handler) — the `date` value is concatenated directly into `$wpdb->get_row()`
   / `$wpdb->query()` / `$wpdb->get_results()` instead of using
   `$wpdb->prepare()`.
2. **Reflected XSS** (shortcode output and the AJAX handler's `print_r()`
   dump) — the same `date` value is echoed back into HTML with no
   `esc_html()` / `esc_attr()`.
3. **Missing authorization/rate-limiting** on the AJAX endpoint — registered
   for both `wp_ajax_hamivtzar_hebrew_lookup` and
   `wp_ajax_nopriv_hamivtzar_hebrew_lookup`, so it's reachable by anyone,
   unauthenticated, with no nonce check.

## Example PoC payloads (for scanner/classifier validation only)

Reflected XSS via the shortcode (render a page containing this shortcode,
then visit it, or feed the same value through anything that echoes shortcode
attributes back):

```
[hebrew_calendar date="<script>alert(document.domain)</script>"]
```

SQL injection via the AJAX endpoint (adjust `table_prefix`/column names to
your test install; run only against your own isolated instance):

```
curl -s "http://localhost:8080/wp-admin/admin-ajax.php" \
  --data-urlencode "action=hamivtzar_hebrew_lookup" \
  --data-urlencode "date=%' UNION SELECT user_login,user_pass,3,4,5 FROM wp_users -- -"
```

Boolean-based SQLi probe:

```
curl -s "http://localhost:8080/wp-admin/admin-ajax.php" \
  --data-urlencode "action=hamivtzar_hebrew_lookup" \
  --data-urlencode "date=%' OR '1'='1"
```

A working scanner/WAF/classifier should flag: unprepared `$wpdb` query
construction from request input, unescaped echo of request input, and an
unauthenticated `nopriv` AJAX action with no capability or nonce check.

## Fixed / secure counterpart

`hebrew-calendar-fixed.php` implements the same feature (shortcode + AJAX
lookup + DB cache) with the vulnerabilities patched, for before/after
validation — does your tool correctly tell vulnerable from patched code, not
just "contains SQL keywords" or "has a $wpdb call":

| | Vulnerable (`hebrew-calendar-vuln-fixture.php`) | Fixed (`hebrew-calendar-fixed.php`) |
|---|---|---|
| Shortcode | `[hebrew_calendar date="..."]` | `[hebrew_calendar_fixed date="..."]` |
| AJAX action | `hamivtzar_hebrew_lookup` | `hamivtzar_hebrew_lookup_fixed` |
| DB table | `{prefix}hamivtzar_hebrew_cache` | `{prefix}hamivtzar_hebrew_cache_fixed` |
| Query building | raw string concatenation into SQL | `$wpdb->prepare()` with `%s` placeholders everywhere, `$wpdb->esc_like()` for the `LIKE` pattern |
| Input handling | any string accepted as-is | `hamivtzar_hc_fixed_validate_date()` — strict `Y-m-d` regex + `checkdate()`, reject-by-default |
| Output | raw echo of user input | `esc_html()`/`esc_attr()` on every dynamic value |
| AJAX response | unescaped `print_r()` HTML dump | `wp_send_json_success()` with pre-escaped fields |
| AJAX auth | no nonce, no capability check | `check_ajax_referer()` against a per-action nonce (still intentionally left public/read-only by design, not "fixed" into requiring a capability, since the feature is meant to be public — the nonce still binds calls to a page that actually rendered the shortcode) |

All function names, hook names, and table names in the fixed version are
suffixed `_fixed` and don't collide with the vulnerable fixture, so both
plugins can be activated **at the same time** on the same isolated test
install — point your scanner/classifier at both and confirm it flags the
first and not the second.
