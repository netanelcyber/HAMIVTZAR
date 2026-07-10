# PGP key used to encrypt `hackerone-submission-draft.asc`

- **Recipient identity:** Automattic (owner of Jetpack) `<security@automattic.com>`
- **Key ID:** `3259C4E88FE57888` (encryption subkey `C85A86F627B2BB9E`)
- **Fingerprint:** `60AC B2A4 A47D 5344 46FD 48B6 3259 C4E8 8FE5 7888`
- **Published at:** https://automattic.com/security/pgp-key/ (fingerprint confirmed
  via search-engine index of that page — the page itself is not directly
  fetchable from this environment, see below).
- **Actual key material fetched from:** `keyserver.ubuntu.com` (HKP), by
  fingerprint — not from automattic.com directly, since this environment's
  egress policy blocks that domain at the network level (confirmed: the
  outbound CONNECT tunnel itself returns 403 for `automattic.com`,
  `wpforms.com`, and `really-simple-ssl.com` — the same class of block as
  `wordpress.org`, not a site-side bot-block).
- **Verification performed:** the fingerprint of the key actually downloaded
  from the keyserver was diffed against the fingerprint reported by search
  engines for automattic.com's own published key page — exact match — before
  it was used for anything.

## WPForms / Awesome Motive and Really Simple Security

No PGP key was found for either vendor:
- Their own domains (`wpforms.com`, `really-simple-ssl.com`) are
  network-blocked from this environment the same way as automattic.com, so
  their `security.txt`/PGP pages couldn't be fetched directly.
- Unlike Automattic, no search-engine-indexed page surfaced a key or
  fingerprint for either vendor.
- A direct keyserver search (`keyserver.ubuntu.com`) for
  `security@wpforms.com`, `security@awesomemotive.com`,
  `security@really-simple-ssl.com`, and `security@really-simple-plugins.com`
  returned no results for any of them.

Conclusion: these two vendors do not appear to publish a PGP key at all —
plausible, since both point researchers to Patchstack, which provides its
own encrypted/authenticated submission channel instead of PGP. Their
`patchstack-submission-draft.md` files are left unencrypted; submit them
through Patchstack's own account-authenticated form rather than email.
