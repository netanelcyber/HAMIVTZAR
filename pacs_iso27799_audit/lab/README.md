# Local rehearsal lab: patient self-service login hardening

A generic, local-only stand-in for testing controls **AC-6**, **AC-7**, and
**OPS-5** in `../controls.py` — rate limiting / lockout / attempt-logging on
a patient self-service login that authenticates with a low-entropy
identifier (date of birth) plus a short secondary code.

This is **not** a copy of any real product's code, UI, or branding — there is
no product name, logo, copyright notice, or page design here, and there
won't be. It matches only the *functional* shape of this class of login
(two form fields, `patient_birth_date` + `user_code`, submitted as a normal
`application/x-www-form-urlencoded` POST) because that shape is what
determines the security properties being tested; a visually convincing
replica of a real login page adds no testing value and is exactly the shape
of a phishing page, so this stays a plain, generic lab server with no UI at
all (it's a raw HTTP endpoint, not an HTML page).

## Safety properties

- `mock_patient_portal.py` only ever binds to `127.0.0.1`. There is no flag
  to bind it elsewhere.
- `rehearse_lockout_check.py` hard-refuses any `--host` other than
  `127.0.0.1`/`localhost` — this is not configurable. It is a rehearsal
  client for this specific local server, not a general-purpose
  credential-guessing tool.
- No real patient data, no real hospital or vendor branding/UI, no network
  calls beyond loopback.

## Try it

Terminal 1 — start the server **unprotected**, to see the failure mode:

```bash
python -m pacs_iso27799_audit.lab.mock_patient_portal --no-rate-limit
```

Terminal 2 — run the rehearsal client:

```bash
python -m pacs_iso27799_audit.lab.rehearse_lockout_check
```

With no rate limiting, it will eventually guess the 3-digit access code
(the code space is small on purpose so the demo finishes in seconds) and
print how many attempts and how long that took — this is exactly the
scenario controls AC-6/AC-7 exist to prevent.

Now stop the server (Ctrl+C) and restart it **with** lockout (the default):

```bash
python -m pacs_iso27799_audit.lab.mock_patient_portal
python -m pacs_iso27799_audit.lab.rehearse_lockout_check
```

This time it should get locked out well before exhausting the code space —
demonstrating that the control, when present, actually stops the attack
class it targets.

## Postback tokens (ASP.NET-style)

This class of app is commonly built on ASP.NET WebForms, which uses a
postback pattern: a GET returns a `__VIEWSTATE`/`__EVENTVALIDATION` pair that
the following POST must include. The lab models the *operationally relevant
behavior* of that (a short-lived, single-use token pair issued by `GET
/login` and required by `POST /instant-access`) — not a reimplementation of
ASP.NET's actual ViewState/EventValidation algorithm (which MACs serialized
page state against a machine key). It's on by default; `rehearse_lockout_check.py`
already does the GET before every attempt. Turn it off on both ends to see the
simpler flow:

```bash
python -m pacs_iso27799_audit.lab.mock_patient_portal --no-postback-tokens
```

The practical lesson: this kind of stateful, single-use token slows down
*naive* brute-force scripts (each guess now costs two requests instead of
one) but does not stop a script written to handle it, same as here — it's a
mild speed bump, not a substitute for AC-6/AC-7's rate limiting/lockout.

## Endpoint discovery / reverse engineering rehearsal

The mock now exposes a small family of endpoints beyond the login flow
(a session-protected "results" endpoint, a couple of commonly-misconfigured
diagnostic/debug endpoints, session invalidation) — see
`mock_patient_portal.py`'s docstring for the full list. `rehearse_endpoint_recon.py`
rehearses discovering and fingerprinting them without reading that list
first, exactly like recon against a real target: it probes a built-in
candidate path list (real hits mixed with plausible-but-absent decoys),
tries GET then POST when a path 404s, and reports which paths responded and
what the status code implies (open, requires auth, wrong method, not found).

```bash
python -m pacs_iso27799_audit.lab.mock_patient_portal
python -m pacs_iso27799_audit.lab.rehearse_endpoint_recon
```

Same safety property as the other lab scripts: hard-refuses any `--host`
other than `127.0.0.1`/`localhost` (it reuses `rehearse_lockout_check.py`'s
guard directly). `/admin/debug` is deliberately undocumented and reachable
without auth — finding it is the point: it's a stand-in for the very common
real-world finding of a debug/diagnostic endpoint left open in production.

## Mapping back to the audit toolkit

Once you've rehearsed the technique here, the corresponding entries in
`pacs_iso27799_audit/sample_config.json` / your own deployment config are:

```json
"access_control": {
  "instant_access_rate_limited": true,
  "instant_access_lockout_threshold": 5
},
"operations": {
  "instant_access_attempts_logged": true
}
```

`AC-8` (access-code entropy/expiry) stays a manual-review control — this lab
uses a deliberately small, fixed-format code for demo speed, which is itself
an example of the kind of weak code design AC-8 asks a real assessor to look
for and replace with longer random tokens or one-time links.
