# `security_classifier` run against the Hebrew calendar fixtures

**Date:** 2026-07-09
**Command:**
```
python3 -m security_classifier.train
python3 -m security_classifier.classify hebrew-calendar-vuln-fixture.php --explain
python3 -m security_classifier.classify hebrew-calendar-fixed.php --explain
```

## Raw output

```
=== Vulnerable plugin ===
 0.10  benign     hebrew-calendar-vuln-fixture.php
        looks benign to the classifier, with strong signal (score 0.10). No
        individual high-risk indicator was triggered; the score comes mostly
        from the file's overall size and import profile rather than any one
        dangerous call. It imports 0 module(s) (0 from the watched list)
        across 0 function(s) and 158 lines.

=== Fixed plugin ===
 0.10  benign     hebrew-calendar-fixed.php
        looks benign to the classifier, with strong signal (score 0.10). No
        individual high-risk indicator was triggered; the score comes mostly
        from the file's overall size and import profile rather than any one
        dangerous call. It imports 0 module(s) (0 from the watched list)
        across 0 function(s) and 195 lines.
```

Both files score **identically** (0.10, benign, 0 imports, 0 functions
detected). The classifier does not distinguish the SQL-injection/XSS file
from the patched one at all.

## Root cause: this is a tool mismatch, not a scanner miss

`security_classifier/features.py` extracts features by calling Python's
`ast.parse()` on the source and walking the resulting syntax tree. It never
executes the code, and by design it degrades safely: **when parsing fails,
it returns a near-empty feature vector instead of raising** (see
`extract_features()`, `except SyntaxError: return features`).

PHP is not Python. Confirmed directly:

```
>>> ast.parse(open('hebrew-calendar-vuln-fixture.php').read())
SyntaxError: unterminated string literal (detected at line 28)
```

So both files hit that fallback path — the classifier saw 0 functions and 0
imports in *both* files because it never actually parsed either one. The
identical 0.10 score is an artifact of that fallback, not an assessment of
the code.

There's a second, independent mismatch even setting language aside: this
classifier is trained to flag **malware-style behavioral indicators**
(suspicious imports, `eval`/`exec`, `subprocess(shell=True)`, base64/obfuscation,
network/persistence hints — see the top-features list from training below).
It has no feature for "string-concatenated SQL query" or "unescaped output,"
so even a hypothetical Python port of these same two files would likely score
similarly on *this* feature set — SQLi/XSS-via-missing-escaping isn't the
threat model this tool targets. It's built to answer "does this file look
like malware," not "does this file contain an injection vulnerability."

A third factor, disclosed in the project's own `README.md`/`train.py`
output: with no `--benign-dir`/`--malicious-dir` supplied, training falls
back to a synthetic 3-sample placeholder set (2 benign, 1 malicious). The
model behind these scores was never fit on real code of any kind, let alone
PHP or WordPress plugins — the README is explicit that this is "a pipeline
demo, not an accurate classifier."

## Conclusion

`security_classifier` is not an applicable tool for this test-fixture pair.
It's a Python-source malware-behavior classifier; these fixtures are
PHP files exercising a SQL-injection/XSS vulnerability class. Neither the
input language nor the vulnerability class is inside what the tool measures,
and it fails safe (near-empty features) rather than failing loud, so running
it silently produces a matched "both benign" result that looks like a
scanner miss but is actually "wrong tool for the job."

## Recommendation

To actually validate a scanner against `hebrew-calendar-vuln-fixture.php` /
`hebrew-calendar-fixed.php`, use PHP-aware static analysis instead, e.g.:

- **Semgrep** with the `p/php` and/or WordPress-specific rule packs — has
  rules for exactly this pattern (`$wpdb` string concatenation, unescaped
  echo of request data).
- **PHPCS + `wp-coding-standards/wpcs`** (`WordPress-Extra`/`WordPress-VIP-Go`
  sniffs) — flags missing `esc_html()`/`$wpdb->prepare()` directly.
- A dedicated WordPress vulnerability scanner (e.g. WPScan) if testing a
  running instance rather than source.

None of these were available in this environment at the time of this run
(no `semgrep`/`phpcs` binary found). Say the word if you'd like me to install
one and re-run against both fixtures.
