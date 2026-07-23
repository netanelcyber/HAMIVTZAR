# Obfuscation Analysis & Deobfuscation Techniques

This document covers analysis of obfuscated JavaScript sensor scripts commonly found in WAF bot-detection systems like Imperva/Incapsula, Cloudflare, etc.

## Common Obfuscation Patterns

### 1. **String Array Encoding**

**Pattern:** Large arrays of hex or base64-encoded strings with index-based lookups.

```javascript
var _0x1234 = ['\x41\x42\x43', '\x44\x45\x46', /* ... lots more ... */];
var _0x5678 = function(_0xIndex) {
    return _0x1234[_0xIndex];
};

var msg = _0x5678(0) + _0x5678(1); // "ABCDEF"
```

**How to bypass:**
- Extract all strings from the array
- Decode hex escapes (`\x**`) to ASCII
- Replace function calls with actual strings
- The resulting code is much simpler to analyze

### 2. **Variable Renaming**

**Pattern:** All meaningful names replaced with short hex identifiers.

```javascript
// Before obfuscation
function checkForAutomation() {
    return navigator.webdriver === true;
}

// After obfuscation
var _0x7a9b = function() {
    return navigator[_0x1234(45)] === !![];
};
```

**How to bypass:**
- Use deobfuscator tools to extract and decode strings
- Look at what properties/methods are accessed
- Infer the original logic from context

### 3. **Control Flow Obfuscation**

**Pattern:** Complex switch statements, IIFE wrapping, and meaningless operations.

```javascript
(function() {
    var _0x1234 = function(_0x5678) {
        while (--_0x5678) {
            // rotate array elements
        }
    };
    _0x1234(0x12c);
})();
```

**How to bypass:**
- Simplify switch statements by extracting cases
- Remove IIFE wrapping when not needed
- Identify and remove dummy operations
- Use browser dev tools to step through code

### 4. **Anti-Debugging Techniques**

**Patterns Found:**
- `console.log = function() {}`  — disables logging
- Regex checks for "function" in strings
- `eval()` detection
- Timeout loops that detect breakpoints
- `navigator.webdriver` checks

**How to bypass:**

```javascript
// Restore console
delete window.console;
window.console = {log: console_log_backup};

// Disable timeout detection
clearTimeout = function() {};
setInterval = function() {};

// Patch navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});
```

### 5. **RC4 Encryption**

**Pattern:** Binary payloads encrypted with RC4, decrypted on runtime.

```javascript
var key = 'secretkey123';
var encrypted = atob('base64_payload_here==');
var decrypted = rc4Decrypt(encrypted, key);
eval(decrypted);  // execute the decrypted code
```

**How to bypass:**
- Extract the key and encrypted payload
- Use RC4 decryption (provided tool: `rc4_decryptor.py`)
- Decode the resulting payload
- Analyze the decrypted code

### 6. **Cookie-Based Challenges**

**Pattern:** JS challenge that writes cookie, then reloads page.

```javascript
var nonce = document.querySelector('[data-nonce]').value;
var token = complexAlgorithm(nonce);
document.cookie = 'incap_ses_' + token;
location.reload();
```

**How to bypass:**
- Extract the nonce from page source
- Reverse-engineer the algorithm (look for patterns)
- Compute the token in Python/Node.js
- Set the cookie and proceed (no reload needed)

## Tool Usage

### 1. **Deobfuscator Tool**

Extract and analyze string arrays:

```bash
python3 tools/deobfuscator.py obfuscated_code.js
```

**Output:**
- Number of hex-encoded strings
- Extracted string arrays
- Function accessor mappings
- Detected suspicious patterns (debugger, console disable, etc.)
- Base64 payloads found

### 2. **RC4 Decryptor Tool**

Analyze RC4 encryption patterns and attempt decryption:

```bash
python3 tools/rc4_decryptor.py obfuscated_code.js

# With known key:
python3 tools/rc4_decryptor.py obfuscated_code.js "your_rc4_key"
```

**Output:**
- RC4 indicators found (KSA, PRGA, etc.)
- Base64 payloads
- Hex strings
- Possible RC4 keys
- Decrypted payloads (if key provided)

## Advanced Bypass Techniques

### Technique 1: Static Analysis

1. **Copy the obfuscated code to a file**
2. **Run deobfuscator:**
   ```bash
   python3 tools/deobfuscator.py code.js > analysis.txt
   ```
3. **Look for suspicious patterns** in the extracted strings
4. **Map out the flow** using the decoded variables

### Technique 2: Dynamic Analysis (Browser Console)

```javascript
// 1. Intercept the deobfuscation function
var originalFunc = _0x1234;
var callLog = [];
window._0x1234 = function(idx) {
    var result = originalFunc(idx);
    callLog.push({index: idx, value: result});
    return result;
};

// 2. Execute a small portion of the code
// 3. Check what strings were actually accessed
console.log(callLog);

// 4. Look at actual property accesses
var propAccess = new Proxy(navigator, {
    get: (target, prop) => {
        console.log('Access:', prop);
        return target[prop];
    }
});
```

### Technique 3: Automated Deobfuscation

For simple cases, you can partially deobfuscate:

```python
import re
import json

code = open('obfuscated.js').read()

# Extract string array
array_match = re.search(r"var\s+(\w+)\s*=\s*\[(.*?)\];", code, re.DOTALL)
if array_match:
    var_name = array_match.group(1)
    strings = re.findall(r"'([^']*)'", array_match.group(2))
    
    # Decode hex escapes
    decoded = []
    for s in strings:
        decoded_s = s.encode().decode('unicode-escape')
        decoded.append(decoded_s)
    
    # Replace in code
    for i, val in enumerate(decoded):
        code = re.sub(f"{var_name}\\(\\s*{i}\\s*\\)", f"'{val}'", code)
    
    print(code)
```

## Red Flags in Obfuscated Code

Look for these patterns indicating detection logic:

| Pattern | Meaning |
|---------|---------|
| `navigator.webdriver` | Headless browser detection |
| `window.chrome` | Chrome automation detection |
| `process.env` or `require('fs')` | Detecting Node.js environment |
| `document.currentScript` | Checking script source |
| `PerformanceObserver` | Timing attack detection |
| `console.clear()` | Anti-debugging |
| `eval()` or `Function()` | Dynamic code execution |
| `atob()` / `btoa()` | Base64 encoding/decoding |
| Cookie operations | Challenge solving |

## Bypass Strategy Workflow

```
1. Obtain obfuscated code
   ↓
2. Run deobfuscator tool
   ↓
3. Extract string array & functions
   ↓
4. Identify key patterns:
   - Challenge algorithm
   - Detection checks
   - Cookie operations
   ↓
5. For challenges:
   - Reverse-engineer algorithm
   - Implement in Python/Node.js
   ↓
6. For detection bypasses:
   - Patch navigator.webdriver
   - Override console
   - Mock process object
   ↓
7. Test bypass client
   - Validate success
```

## Real-World Examples

### Example 1: Simple Nonce-Based Challenge

**Obfuscated code:** Computes `sha256(nonce + salt)`, stores as cookie

**Bypass:**
```python
import hashlib

nonce = "abc123"
salt = "known_salt"
token = hashlib.sha256((nonce + salt).encode()).hexdigest()
# Set cookie and request proceeds
```

### Example 2: Headless Browser Detection

**Obfuscated code:** Checks `navigator.webdriver`

**Bypass:**
```python
# Using Playwright with stealth
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch()
    context = await browser.new_context()
    # Override navigator.webdriver
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page = await context.new_page()
    await page.goto(url)
```

### Example 3: RC4-Encrypted Payload

**Obfuscated code:** Decrypts with `rc4(payload, key)`, execs result

**Bypass:**
```python
import base64

# Extract from code
payload_b64 = "qX28fD..."  # from analysis
key = "imperva_key"

# Decrypt using provided tool
# Then analyze the decrypted JavaScript
```

## Testing Your Bypass

1. **Unit test the algorithm:**
   ```python
   def test_token_generation():
       nonce = "test_nonce"
       token = compute_token(nonce)
       assert token == "expected_value"
   ```

2. **Integration test with the WAF:**
   ```bash
   python3 tools/crack_cipher_client.py http://target-waf:8080/
   ```

3. **Monitor headers and cookies:**
   - Check what headers the real browser sends
   - Replicate in your bypass client
   - Verify cookie format and timing

## Legal & Ethical Notes

⚠️ **Only use these techniques:**
- On systems you own or have explicit permission to test
- In educational lab environments
- During authorized penetration testing engagements
- For defensive security research

**This lab is designed for:**
- Understanding WAF mechanics (educationally)
- Testing your own infrastructure
- Defensive engineering (building better WAFs)

---

For more details, see the main [README.md](README.md) and tool documentation.
