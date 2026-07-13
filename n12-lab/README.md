# HaMivtzar News Lab

A small, self-contained **intentionally vulnerable** mock news portal for
**legal** security-testing practice on infrastructure you own — the same idea as
[DVWA](https://github.com/digininja/DVWA) or
[OWASP Juice Shop](https://owasp.org/www-project-juice-shop/), but shaped like an
Israeli news site so the attack surface feels realistic.

It mimics the **architecture** of a news portal (news lobby, live "writers chat"
feed, weather feed loader, search, a recommendation proxy, an admin panel, and an
obfuscated header-bidding-style loader) — with generic branding and fictional
content, and a loud banner marking it as a training lab. **It is not a clone of
any real outlet** and must never be used to impersonate one or attack a real site.

> ⚠️ This app is deliberately insecure. Run it locally only. Do not expose it to
> the internet, and never point these techniques at a system you don't own or
> aren't authorized (in writing) to test. See [`SCOPE.md`](SCOPE.md).

## Run it

No third-party dependencies — Python 3 standard library only.

```bash
python3 app.py                 # http://127.0.0.1:8099
# or choose host/port:
HOST=127.0.0.1 PORT=8099 python3 app.py
```

Or with Docker (bound to localhost):

```bash
docker compose up --build      # http://127.0.0.1:8099
```

## What's inside

| Path | Mimics | Intentional weakness |
|------|--------|----------------------|
| `/` | news lobby + writers chat | renders chat messages unescaped |
| `/newssearch?q=` | site search | **reflected XSS** (VULN-01) |
| `/article?id=` | article page | **IDOR** to unpublished drafts (VULN-02) |
| `/AjaxPage?jspName=` | the `/AjaxPage?jspName=…` feed loader | **path traversal / LFI** (VULN-03) |
| `/proxy/multivac?url=` | Outbrain-Multivac-style rec proxy | **SSRF** (VULN-04) |
| `POST /api/chat` | reporters posting to the live chat | **stored XSS** (VULN-05) |
| all responses | — | **missing security headers** (VULN-06) |
| `/config/version` | inline stormcaster/euda config | **info disclosure** (VULN-07) |
| `/admin` | admin panel | **default creds, no lockout** (VULN-08) |
| `/go?url=` | `?partner=` redirect logic | **open redirect** (VULN-09) |
| `/.env` | — | **sensitive file exposure** (VULN-10) |
| `/static/hb-loader.js` | obfuscated header-bidding loader | **reverse-engineering challenge** |

Each weakness is tagged `# [VULN-xx]` in [`app.py`](app.py).

## Exercises

- **Find & exploit the bugs** — try first, then check
  [`attacks/SOLUTIONS.md`](attacks/SOLUTIONS.md). Point Burp/ZAP/ffuf/nikto at
  `127.0.0.1:8099`.
- **Deobfuscate the scripts** — [`attacks/SCRIPT_ANALYSIS.md`](attacks/SCRIPT_ANALYSIS.md)
  explains the two common patterns (the `_0x…` string-array rotation and the
  `__webpack_modules__` service-worker loader). Run the included decoder:
  ```bash
  python3 attacks/deobfuscate.py
  curl -s http://127.0.0.1:8099/static/hb-loader.js | python3 attacks/deobfuscate.py -
  ```

## Files

```
n12-lab/
├── app.py                     # the lab server (stdlib http.server)
├── seed.py                    # fictional articles / chat / config
├── feeds/
│   ├── weather.json           # the legit feed
│   └── SECRET_internal.json   # the LFI/path-traversal target
├── attacks/
│   ├── SOLUTIONS.md           # findings walkthrough + fixes
│   ├── SCRIPT_ANALYSIS.md     # JS deobfuscation writeup
│   └── deobfuscate.py         # string-array-rotation decoder
├── SCOPE.md                   # rules of engagement
├── Dockerfile
└── docker-compose.yml
```

## Legal / ethical note

Built for education and authorized testing only. Attacking systems you don't own
without permission is illegal. This lab exists precisely so you never have to.
