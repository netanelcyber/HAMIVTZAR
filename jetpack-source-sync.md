# Jetpack source sync

`jetpack/` in this repo is a vendored, files-only snapshot of
[Automattic/jetpack](https://github.com/Automattic/jetpack) `trunk`
(no `.git`, no history — just the tree as it existed at sync time).

A daily Routine re-clones upstream `trunk` and mirrors it into `jetpack/`
(commit + push only happens when something actually changed). Don't hand-edit
files under `jetpack/` — the next sync will overwrite them. Analysis, reports,
and anything else derived from the Jetpack source belongs in a sibling
directory (e.g. `jetpack-security-review/`) so it survives the sync.
