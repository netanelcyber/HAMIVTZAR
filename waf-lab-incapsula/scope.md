# Scope & Rules of Engagement

- **Target:** this lab only — a self-hosted, locally-run stand-in for an
  Incapsula/Imperva-style WAF (`waf-proxy/`) fronting a trivial origin app
  (`backend/`). Both run on `localhost` (or inside the lab's own Docker
  network) and are owned/created by the requester for this exercise. There
  is no external target and no third-party infrastructure involved.
- **Authorization:** implicit and total — you own every host involved. This
  differs from `pentest-booknet/` and `pentest-milatova/` in this repo,
  which target real third-party sites under a signed engagement; this
  folder never sends a request anywhere but the lab's own containers/ports.
- **Rules:** none beyond "don't point these scripts at a host you don't
  own." The `tools/` scripts default to `http://localhost:8080`; if you
  repoint them at any other host, the usual rules from the other
  `pentest-*/` folders apply (written authorization required before active
  testing).
