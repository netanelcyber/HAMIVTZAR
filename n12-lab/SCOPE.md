# Scope & rules of engagement — HaMivtzar News Lab

## What you may attack
- **Only** this lab, running on **your own machine / a host you own**
  (default `http://127.0.0.1:8099`), or a copy you deployed to an isolated
  network you control.

On that target, anything goes: injection, brute force, fuzzing, DoS, exploit
development, automated scanners — this is a throwaway target built to be broken.

## What is out of scope
- Any real website, third-party service, or host you do not own and are not
  explicitly authorized (in writing) to test. This lab is a **stand-in** so you
  never need to point tools at someone else's production system.
- Do **not** expose this lab to the public internet. It is intentionally
  vulnerable; leaving it reachable is itself a security incident.

## Why a lab instead of a live site
Testing systems you don't own — even "just recon" or "just a scan" — without
written authorization is illegal in most jurisdictions and against this
project's rules. A local lab gives you an identical *kind* of target
(news lobby, feeds, chat, search, admin, obfuscated JS) with none of the legal
or ethical problems.

## If you have a real, authorized engagement
Keep the signed authorization / scope document on file **outside this repo**,
mirror the structure of `../pentest-milatova/` (scope.md, rules of engagement,
findings/, evidence/), and stay strictly within the assets and time window the
authorization covers.
