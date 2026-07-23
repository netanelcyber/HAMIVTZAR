# WAF lab — Incapsula/Imperva-style bypass techniques

A local, self-contained lab for practicing the bot-detection bypass concepts
described in things like scrapfly.io's Incapsula bypass guide, without
touching any real target. See [`scope.md`](scope.md) — everything here runs
on hosts you own.

**This is not a copy of Incapsula.** Their real detection (TLS/JA3
fingerprinting, the obfuscated `reese84`/`___utmvc` sensor scripts, etc.) is
proprietary and far more sophisticated. This lab reimplements the
publicly-documented *shape* of that model — a cookie-gated JS challenge
(`incap_ses_*` / `visid_incap_*` cookie names), basic User-Agent/header
signature checks, and per-window rate limiting — so the bypass techniques
below have something real and reproducible to defeat.

## Layout

- `backend/` — trivial Flask "origin" app. Never exposed directly; only the
  WAF proxy's port is meant to be reachable.
- `waf-proxy/` — the WAF simulation (`proxy.py`). Gates every request behind
  UA/header checks, rate limiting, and a JS challenge; only forwards to
  `backend` once a request presents a verified challenge cookie.
- `tools/` — three clients showing progressively more sophisticated access:
  - `naive_client.py` — plain `requests.get()`, no evasion. Gets blocked
    immediately (default User-Agent + missing `Accept-Language`).
  - `crack_cipher_client.py` — **cracks the challenge cipher**: sends
    realistic headers to clear the signature checks, then reimplements the
    challenge's token algorithm in pure Python (reverse the nonce, shift +
    hex-encode each byte, base64 the pair — see `compute_token()` in
    `waf-proxy/proxy.py`) to forge a valid `incap_ses_lab` cookie without
    ever running JavaScript or opening a browser.
  - `headless_bypass_client.js` — the alternative approach: render the page
    in real (Playwright) Chromium so the challenge JS just runs normally.
    This build's headless Chromium sends `HeadlessChrome` in its UA, which
    the lab WAF blocks on sight — mirroring a real problem with naive
    headless scraping — so the script also overrides the UA string and
    patches `navigator.webdriver` back to `undefined`, the standard
    stealth-headless fix.
- `evidence/` — JSON output from the tools above (nonce, forged token,
  final status/cookies).
- **Analysis Tools** (see `tools/`):
  - `deobfuscator.py` — Extract and analyze obfuscated JavaScript
  - `rc4_decryptor.py` — Analyze RC4 encryption patterns and decrypt payloads
  - `anti_detection_analyzer.py` — Identify bot-detection mechanisms in code
- **Documentation**:
  - `OBFUSCATION_ANALYSIS.md` — Comprehensive guide to analyzing obfuscated WAF sensors

## Running it

### Quick, no Docker (what was used to validate this lab)

```
pip install flask requests
python3 backend/app.py &                                   # port 5001
BACKEND_URL=http://localhost:5001 python3 waf-proxy/proxy.py &   # port 8080

python3 tools/naive_client.py http://localhost:8080/
python3 tools/crack_cipher_client.py http://localhost:8080/
NODE_PATH=/opt/node22/lib/node_modules node tools/headless_bypass_client.js http://localhost:8080/
```

### Docker

```
docker compose up --build
# in another shell, against http://localhost:8080/
python3 tools/naive_client.py
python3 tools/crack_cipher_client.py
node tools/headless_bypass_client.js
```

(The Docker path wasn't runnable in the sandbox this lab was authored in —
no Docker daemon available there — so it's untested as written; the
no-Docker path above was fully run end-to-end, including both bypasses
reaching `LAB_FLAG{waf_bypass_incapsula_lab}`. Sanity-check
`docker compose up --build` once on your machine before relying on it.)

## What each run demonstrates

| Client | Headers fixed? | Solves JS challenge? | Result |
|---|---|---|---|
| `naive_client.py` | no | no | 403, blocked on header/UA signature |
| `crack_cipher_client.py` | yes | yes, by reimplementing the algorithm in Python | 200, reaches origin, no browser involved |
| `headless_bypass_client.js` | yes (UA override + `navigator.webdriver` patch) | yes, by actually running the real JS | 200, reaches origin, challenge internals never inspected |

The WAF's `compute_token()` (in `waf-proxy/proxy.py`) is intentionally
simple — this lab is about the *mechanics* of a JS-challenge WAF (cookie
gating, nonce-bound tokens, signature/header heuristics, and the two classic
ways around a JS challenge) rather than about cracking something
cryptographically hard.

## Analyzing Obfuscated WAF Sensors

This lab includes tools to deobfuscate and analyze real-world obfuscated bot-detection and anti-automation scripts:

### Deobfuscation Tools

**1. Extract String Arrays & Decode Hex**
```bash
python3 tools/deobfuscator.py sensor.js
```
Extracts and decodes obfuscated string arrays, identifies suspicious patterns (anti-debugging, RC4 usage, etc.)

**2. Analyze RC4 Encryption Patterns**
```bash
python3 tools/rc4_decryptor.py sensor.js
python3 tools/rc4_decryptor.py sensor.js "known_key"  # decrypt with key
```
Identifies RC4 encryption, extracts payloads, attempts decryption.

**3. Identify Detection Mechanisms**
```bash
python3 tools/anti_detection_analyzer.py sensor.js
```
Maps out what anti-automation checks are present and suggests bypass strategies:
- Headless browser detection
- Browser automation detection  
- Node.js environment checks
- Timing-based detection
- Device fingerprinting
- Geolocation checks
- Console/debugger disabling

### Comprehensive Analysis Guide

See `OBFUSCATION_ANALYSIS.md` for:
- Common obfuscation patterns and how to bypass them
- RC4 encryption analysis
- Anti-debugging techniques
- Cookie-based challenge reverse-engineering
- Real-world bypass examples
- Legal/ethical use guidelines
