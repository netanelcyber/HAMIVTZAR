# Script analysis — deobfuscating client-side JS

Reverse-engineering JavaScript that a page served to your browser is ordinary
**static analysis**: you already received the bytes, you're just making them
readable. This file explains the two obfuscation/packing patterns you commonly
see on ad-heavy news portals, and how to undo them. Practise on the lab's own
`/static/hb-loader.js` (and on scripts from sites you're authorized to test).

---

## 1. String-array rotation  (the `_0x…` header-bidding pattern)

### What it looks like
```js
var _0x1a2c=['cmd','pubads','disableInitialLoad','push', ... ];
(function(_0x1ef135,_0x1a2cd4){
   var _0x5ef062=function(_0x5582e7){
      while(--_0x5582e7){ _0x1ef135['push'](_0x1ef135['shift']()); }
   };
   _0x5ef062(++_0x1a2cd4);
}(_0x1a2c,0x6c));
var _0x5ef0=function(_0x1ef135,_0x1a2cd4){
   _0x1ef135=_0x1ef135-0x0; return _0x1a2c[_0x1ef135];
};
// ...later...
_0x3bce02[_0x5ef0('0x11')] = _0x5ef0('0x8');   // e.g. el.type = 'text/javascript'
```

### How it works
1. **String array** — all the interesting identifiers/strings are pulled out
   into one array so the code reads as `_0xACC('0x11')` instead of `'type'`.
2. **Rotation IIFE** — `arr.push(arr.shift())` run N times permutes the array.
   This is purely to make the numeric indexes not line up with the literal
   order, so you can't eyeball the mapping.
3. **Accessor** — `_0xACC(i)` returns `arr[i]`.

### How to undo it (no need to execute the page)
- Parse the array literal.
- Replay the rotation: `for _ in range(N): arr.append(arr.pop(0))`.
- Replace every `_0xACC('0xNN')` with `arr[NN]`.

That's exactly what **`deobfuscate.py`** in this folder does:
```
python3 deobfuscate.py                                  # bundled lab sample
curl -s http://127.0.0.1:8099/static/hb-loader.js | python3 deobfuscate.py -
python3 deobfuscate.py path/to/collected/hb-snippet.js  # any file
```
It prints the rotated index→string table and the code with strings resolved, e.g.
```
console['log']('[HaMivtzar loader] init for publisher n-lab')
```
so you can see the script just registers a publisher and logs — no magic.

### Doing it with off-the-shelf tools
- **Prettier / js-beautify** first, to reflow minified code:
  `npx js-beautify hb-snippet.js` or https://beautifier.io (offline: the npm pkg).
- **de4js** (offline, open-source) handles array-rotation automatically.
- **Babel** AST transforms for the more stubborn variants.
- A JS engine sandbox (`node --experimental-vm-modules`, or a `vm` context with a
  stubbed `document`/`window`) if you'd rather *evaluate* the accessor than
  statically resolve it — do this only for code you're authorized to run.

### What to actually look for once it's readable
- Endpoints/URLs it builds (`resourceBasePath`, `csmBasePath`, `/eudaapi/...`).
- What it injects (`createElement('script')`, `src = …`), and under which flags.
- Data it reads/writes (`localStorage` keys, cookies, `postMessage` types).
- Any `eval(xhr.responseText)` / `new Function(...)` — remote-code execution
  surface worth flagging in a report.

---

## 2. Webpack-style bundle  (the `__webpack_modules__` / service-worker loader)

### What it looks like
```js
(function(){ "use strict";
  var __webpack_modules__ = { 348: function(e,t,r){ r.d(t,{ IP:function(){return i}, ... }); ... },
                              405: function(e,t,r){ ... } };
  var __webpack_module_cache__ = {};
  function __webpack_require__(e){ ... __webpack_modules__[e](...); ... }
  // entry code: registers a service worker, polls a /version endpoint, may eval()
})();
```
This isn't really *obfuscation* — it's a **bundler output**. The module bodies
are plain (if minified) functions keyed by number; `__webpack_require__(id)` runs
one and memoizes its exports. `r.d(exports,{name:getter})` defines named exports.

### How to read it
1. **Beautify** the minified bundle (Prettier/js-beautify).
2. Find `__webpack_modules__` and list the module ids and their exports
   (`r.d(t,{...})`). Those export names (e.g. `eudaEnableAgent`, `eudaSyncLoad`)
   are your map of behaviour.
3. Find the **entry** (the IIFE body after the require plumbing) and read it
   top-down: what config it fetches (`fetch('/…/version', {method:'POST'})`),
   what it registers (`navigator.serviceWorker.register(...)`), and any dynamic
   code paths (`eval(xhr.responseText)` in a sync loader is the interesting one).
4. If a **`sourceMappingURL`** comment is present and the `.map` is reachable,
   fetch it and use `source-map` to recover original filenames/variable names —
   the cleanest path of all.

### Note on the service-worker loader specifically
A pattern like "download script over XHR, then `eval()` it, register a service
worker scoped to `/`, poll a version endpoint and `location.reload()` on a
push message" is worth understanding because:
- the **service worker** can intercept every request under its scope, and
- the **`eval` of a network response** means whoever controls that endpoint
  controls the page.
In a report you'd flag the trust placed in those endpoints and the SW scope.
(In this lab, the analogous behaviour is deliberately reduced to a harmless
`console.log` so there's nothing risky to run.)

---

## Rules of engagement for this exercise
- Deobfuscate/beautify freely — it's static analysis of code you received.
- **Executing** recovered code, or hitting the endpoints it references, is only
  OK against your own lab or a system you're authorized to test. See `../SCOPE.md`.
