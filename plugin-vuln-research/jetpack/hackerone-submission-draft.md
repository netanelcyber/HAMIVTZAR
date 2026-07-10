# HackerOne submission draft — Automattic program (hackerone.com/automattic)

Copy/paste into the HackerOne report form after logging into your own
researcher account. Not submitted automatically — no API/account access
exists for this from here.

---

**Title:** Unsafe deserialization (CWE-502) in Jetpack's theme-install JSON API endpoint via legacy PHP-serialization wordpress.org API

**Weakness:** CWE-502: Deserialization of Untrusted Data

**Asset:** Jetpack (WordPress plugin), `github.com/Automattic/jetpack`

**Severity (suggested, let the triager confirm):** Low–Medium. Requires
`install_themes` capability to reach; the remote host is hardcoded to the
legitimate `api.wordpress.org`, so this is not directly attacker-suppliable
input — exploitation would require the response from that specific
`wordpress.org` endpoint to be tampered with (compromise or MITM),
i.e. a supply-chain/network precondition rather than a direct web
exploit. Reporting because the fix is trivial and the code's own comment
already flags it as overdue.

**Affected version:** `16.0` (commit `3b9717e5e18063c5b7b4d4312da1bf8b27c61580`, 2026-07-09). Please confirm whether later versions have already addressed this.

**Description:**

`json-endpoints/jetpack/class.jetpack-json-api-themes-install-endpoint.php`,
method `validate_themes()` (lines ~150-179), handles
`POST /sites/%s/themes/%s/install`. For any theme slug that isn't
suffixed `-wpcom`, it calls the legacy, PHP-serialization-based
`https://api.wordpress.org/themes/info/1.0/` endpoint and passes the raw
HTTP response body directly into `unserialize()` with no
`allowed_classes` restriction:

```php
$params   = (object) array( 'slug' => $theme );
$url      = 'https://api.wordpress.org/themes/info/1.0/'; // @todo Switch to https://api.wordpress.org/themes/info/1.1/, which uses JSON rather than PHP serialization.
$args     = array( 'body' => array( 'action' => 'theme_information', 'request' => serialize( $params ) ) );
$response = wp_remote_post( $url, $args );
$theme_data = unserialize( $response['body'] ); // no allowed_classes
```

The `@todo` comment shows the team is already aware this specific call
site hasn't been migrated to the JSON `1.1` endpoint that WordPress core
itself moved to years ago, specifically to get away from unserializing
remote responses.

**Steps to Reproduce (illustrative, since exploitation depends on the
external response):**

1. As a user with `install_themes` capability, trigger
   `POST /sites/<site>/themes/<slug>/install` with a `<slug>` that does
   not end in `-wpcom`.
2. Observe that `validate_themes()` calls
   `api.wordpress.org/themes/info/1.0/` and unserializes the raw response
   body without restriction.
3. (Not performed by us) If that specific `api.wordpress.org` response
   could be tampered with — e.g. a MITM position, or a hypothetical
   compromise of that legacy endpoint — a crafted serialized payload
   containing an object could trigger PHP object injection, escalating
   to RCE if a suitable POP gadget chain exists among classes loaded by
   WordPress core, Jetpack, or any other active plugin/theme at request
   time. We did not attempt this against any live system; it's inferred
   from the code path.

**Impact:** PHP object injection / potential RCE if the deserialization
precondition is met, contingent on gadget-chain availability. Bounded by
requiring `install_themes` capability and a network-path/supply-chain
precondition on the wordpress.org legacy API response.

**Remediation:** either migrate to `api.wordpress.org/themes/info/1.1/`
(JSON, as the existing code comment already plans to do), or at minimum
`unserialize( $response['body'], array( 'allowed_classes' => false ) )`
as a low-effort interim fix.

**Supporting material:** static source review only; no live system was
tested. Full research methodology and negative results (other
`unserialize()` call sites traced to internal-only data, no SQLi/XSS/
command-injection found) documented at
`plugin-vuln-research/jetpack/FINDINGS.md` in the researcher's own working
repo, available on request.
