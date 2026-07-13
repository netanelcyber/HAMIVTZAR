#!/usr/bin/env python3
"""
Deobfuscator for the "string-array rotation" JavaScript obfuscation pattern.

This is the SAME technique used by the header-bidding / VAD snippet you see on
many real ad-heavy pages (the `var _0x1a2c=[...]; (function(a,b){...a.push(a.shift())...})`
dance, plus a `_0x5ef0(idx)` accessor that indexes the rotated array).

The obfuscation has three parts:
  1. A string array:            var _0xARR = ['a','b','c', ...];
  2. A rotation IIFE that calls _0xARR.push(_0xARR.shift()) N times so that the
     numeric indexes used later line up with the (now rotated) array.
  3. An accessor:               var _0xACC = function(i){ i=i-0x0; return _0xARR[i]; }
     and the real code then reads strings as _0xACC('0x3') etc.

To recover the plaintext you don't need to run the page: you just
  (a) parse the array literal,
  (b) replay the rotation to get the final array order, and
  (c) resolve every _0xACC('0xNN') back to its string.

This script does exactly that for the lab's static/hb-loader.js, and can also
take any file/stdin containing the same pattern.

Usage:
    python3 deobfuscate.py                 # decodes the bundled lab sample
    python3 deobfuscate.py path/to/file.js # decodes another file
    curl -s http://127.0.0.1:8099/static/hb-loader.js | python3 deobfuscate.py -
"""
import re
import sys

# The lab's obfuscated loader (same bytes app.py serves at /static/hb-loader.js)
LAB_SAMPLE = r"""
var _0x3f21=['log','ready','init','loader','HaMivtzar','LAB','publisher','n-lab'];
(function(_0x1,_0x2){var _0x3=function(_0x4){while(--_0x4){_0x1['push'](_0x1['shift']());}};
_0x3(++_0x2);}(_0x3f21,0x1a));
var _0x9a=function(_0x1,_0x2){_0x1=_0x1-0x0;return _0x3f21[_0x1];};
(function(){var name=_0x9a('0x2')+' '+_0x9a('0x1');
console[_0x9a('0x6')]('['+name+'] '+_0x9a('0x0')+' for '+_0x9a('0x4')+' '+_0x9a('0x5'));})();
"""


def parse_string_array(js):
    """Return (array_var_name, [strings]) for the first `var _0xNAME=[...]`."""
    m = re.search(r"var\s+(_0x[0-9a-fA-F]+)\s*=\s*\[(.*?)\];", js, re.S)
    if not m:
        raise ValueError("no string array literal found")
    name, body = m.group(1), m.group(2)
    # extract quoted strings (single or double quotes)
    items = re.findall(r"'((?:\\.|[^'\\])*)'|\"((?:\\.|[^\"\\])*)\"", body)
    strings = [a if a != "" or b == "" else b for a, b in items]
    # the tuple trick above keeps whichever group matched
    strings = [a if a else b for a, b in items]
    return name, strings


def find_rotation_count(js, arr_name):
    """Find the N passed to the rotation IIFE:  ...}(_0xARR, 0xNN)); """
    m = re.search(re.escape(arr_name) + r"\s*,\s*(0x[0-9a-fA-F]+|\d+)\s*\)\s*\)", js)
    if not m:
        return 0
    return int(m.group(1), 0)


def replay_rotation(strings, count):
    """The IIFE does `while(--count){ arr.push(arr.shift()) }` after `++count`.

    Net effect: it performs `count` shift/push rotations (the ++ then the
    while(--...) loop body runs `count` times). We reproduce that.
    """
    arr = list(strings)
    for _ in range(count):
        arr.append(arr.pop(0))
    return arr


def find_accessor_name(js, arr_name):
    """Find the accessor function name: var _0xACC = function(...) {... arr[i] }."""
    m = re.search(
        r"var\s+(_0x[0-9a-fA-F]+)\s*=\s*function\([^)]*\)\s*\{[^}]*"
        + re.escape(arr_name) + r"\[",
        js, re.S)
    return m.group(1) if m else None


def resolve(js, acc_name, rotated):
    """Replace every _0xACC('0xNN') / _0xACC(NN) with the resolved string."""
    def repl(mo):
        idx = int(mo.group(1), 0)
        if 0 <= idx < len(rotated):
            s = rotated[idx]
            return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"
        return mo.group(0)
    pat = re.escape(acc_name) + r"\(\s*'?(0x[0-9a-fA-F]+|\d+)'?\s*\)"
    return re.sub(pat, repl, js)


def deobfuscate(js):
    arr_name, strings = parse_string_array(js)
    count = find_rotation_count(js, arr_name)
    rotated = replay_rotation(strings, count)
    acc = find_accessor_name(js, arr_name)
    report = [
        "# string array : %s" % arr_name,
        "# raw order    : %r" % strings,
        "# rotation N   : %d" % count,
        "# rotated order: %r" % rotated,
        "# accessor     : %s" % acc,
        "# --- resolved index table ---",
    ]
    for i, s in enumerate(rotated):
        report.append("#   0x%x -> %r" % (i, s))
    resolved_js = resolve(js, acc, rotated) if acc else js
    report.append("# --- code with strings resolved ---")
    report.append(resolved_js.strip())
    return "\n".join(report)


def main(argv):
    if len(argv) > 1 and argv[1] == "-":
        js = sys.stdin.read()
    elif len(argv) > 1:
        with open(argv[1], "r", encoding="utf-8") as fh:
            js = fh.read()
    else:
        js = LAB_SAMPLE
    print(deobfuscate(js))


if __name__ == "__main__":
    main(sys.argv)
