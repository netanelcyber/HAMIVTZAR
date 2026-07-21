# Scope & Rules of Engagement — VUE PACS ISO 27799 Audit

Mirrors the pattern in `pentest-milatova/scope.md`: named target, confirmed
authorization, explicit rules of engagement, before any tooling runs against
real data.

- **Target:** the requester's VUE PACS deployment (hospital patient
  imaging/PACS environment). No hostnames, IP ranges, or other identifying
  infrastructure details are recorded in this repo.
- **Authorization:** stated by the requester to be a contract/engagement
  letter with the hospital / system owner. **This repo does not hold that
  document.** Keep the actual signed agreement on file outside this repo
  (it will contain identifying/sensitive details) — this file only records
  that an authorization basis was asserted and what kind.
- **Current scope — config-based assessment only:**
  - Run `pacs_iso27799_audit/audit.py` and `pacs_iso27799_audit/risk_model.py`
    against a configuration file describing the real deployment, supplied by
    the requester (as an authorized assessor) from their own knowledge of
    the environment.
  - **No network connection of any kind** to the real system is made as
    part of this scope — these tools only ever read a local JSON file.
- **Explicitly out of scope right now:** active network reconnaissance,
  endpoint enumeration, brute-force/lockout testing, authentication-bypass
  attempts, or any other live testing against the real system. The
  `pacs_iso27799_audit/lab/` rehearsal tooling stays pointed at
  `127.0.0.1` only. Expanding to active testing would need this file
  updated first with explicit rules of engagement for that (testing
  window, named contact, what's authorized vs. not — same bar as
  `pentest-milatova/scope.md`), not just a restated claim of authorization.
- **Handling of real configuration data:** the real deployment's
  configuration values (and any resulting audit/risk report) are treated as
  sensitive information about a real hospital's security posture. They are
  not committed to this repository. Reports are generated locally and
  handed to the requester directly.

Update this file before expanding scope.
