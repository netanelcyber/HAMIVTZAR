# Local rehearsal lab: patient self-service login hardening

A generic, local-only stand-in for testing controls **AC-6**, **AC-7**, and
**OPS-5** in `../controls.py` — rate limiting / lockout / attempt-logging on
a patient self-service login that authenticates with a low-entropy
identifier (date of birth) plus a short secondary code.

This is **not** a copy of any real product's code, UI, or branding. It is a
minimal stand-in for one narrow authentication pattern, built so the testing
*technique* (brute-force an access code, observe whether lockout kicks in)
can be rehearsed against something you run yourself — never against a real
hospital system or patient portal.

## Safety properties

- `mock_patient_portal.py` only ever binds to `127.0.0.1`. There is no flag
  to bind it elsewhere.
- `rehearse_lockout_check.py` hard-refuses any `--host` other than
  `127.0.0.1`/`localhost` — this is not configurable. It is a rehearsal
  client for this specific local server, not a general-purpose
  credential-guessing tool.
- No real patient data, no real hospital or vendor branding, no network
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
