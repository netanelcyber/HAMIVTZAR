# Obfuscated Code Analysis Workflow

Step-by-step guide to analyzing obfuscated WAF sensor scripts.

## Step 1: Obtain the Obfuscated Code

Extract from browser DevTools:
```
1. Open target website in browser
2. Press F12 → Sources tab
3. Look for scripts that get injected (often `cdn/sensor`, `bot-protect`, etc.)
4. Right-click → Save As → Save to file
```

Or extract from HTML source:
```bash
curl -s https://target.com | grep -oP '<script[^>]*src="\K[^"]*sensor[^"]*' | head -1 | xargs curl -s > sensor.js
```

## Step 2: Run Anti-Detection Analyzer (High-Level Overview)

```bash
python3 tools/anti_detection_analyzer.py sensor.js
```

**Sample output:**
```
1. HEADLESS BROWSER
   Description: Detects headless browser execution
   Detected patterns: HeadlessChrome, navigator.webdriver
   Bypass strategy: Override User-Agent, patch navigator.webdriver

2. BROWSER AUTOMATION
   Description: Detects browser automation tools
   Detected patterns: webdriver, chrome.runtime
   Bypass strategy: Use stealth plugins, patch navigator properties

3. RC4 ENCRYPTION
   Description: Uses RC4 to encrypt sensitive code
   Detected patterns: atob, charCodeAt, fromCharCode
```

**What this tells you:**
- Code is protected with RC4 encryption
- Detects headless browsers (need Chromium with UA override)
- Checks for automation APIs (need stealth mode)

## Step 3: Run Deobfuscator (String Extraction)

```bash
python3 tools/deobfuscator.py sensor.js > analysis.txt
```

**What to look for in output:**

1. **Suspicious Patterns Found** section:
   - `console_disable`: Code will disable console logging
   - `eval`: Dynamically executed code (need to analyze separately)
   - `base64_decode`: Base64 payload (might be encrypted)

2. **String Arrays Detected** section:
   - Look for readable strings that give hints about functionality
   - Examples: `"cookie"`, `"token"`, `"verify"`, `"navigator"`

3. **Base64 Payloads** section:
   - These might be RC4-encrypted code or configuration
   - Copy these for RC4 decryption attempt

**Example analysis:**
```
[*] Hex-encoded strings found: 2847
[*] String arrays detected: 3

String Array 1 (first 500 chars):
  cookie
  token
  verify
  navigator.webdriver
  HeadlessChrome
  localStorage
  ...

[*] Suspicious patterns detected:
  - eval: Found 5 occurrence(s)
  - base64_decode: Found 12 occurrence(s)
  - rc4_ksa: Found 2 occurrence(s)
  - unicode_encoding: Found 87 occurrence(s)

[*] Base64 payloads found: 2
  Payload 1: qX28fD7tXzWmNAa3Y...
```

## Step 4: Try RC4 Decryption (If Encrypted)

Look for common RC4 keys in the code or guess based on context:

```bash
# Try common key formats
python3 tools/rc4_decryptor.py sensor.js "sensor_key"
python3 tools/rc4_decryptor.py sensor.js "imperva"
python3 tools/rc4_decryptor.py sensor.js "cloudflare"

# Or extract the key from the code:
grep -oP "atob\(\s*['\"]\K[^'\"]*" sensor.js | head -1
```

If you find the key and successfully decrypt, you get the actual detection code.

## Step 5: Static Analysis (Code Review)

Look for patterns in the decoded strings:

```javascript
// Example extracted patterns to look for:

// Cookie-based challenge
"incap_ses_"        // Cookie name
"token_algorithm"   // How token is computed
"nonce"            // Random value

// Detection checks
"navigator.webdriver"
"chrome.runtime"
"process.env"
"__dirname"

// Callbacks
"onSuccess"
"onDetected"
"blockPage()"
```

## Step 6: Dynamic Analysis (Browser Console)

If you can't fully deobfuscate, hook the functions at runtime:

```javascript
// In browser console

// 1. Log all string accesses
var originalFunc = _0x1234; // from deobfuscator output
window._0x1234 = function(idx) {
    var result = originalFunc(idx);
    if (typeof result === 'string' && result.length < 100) {
        console.log(`String ${idx}: ${result}`);
    }
    return result;
};

// 2. Log navigator accesses
var nav = new Proxy(navigator, {
    get: (target, prop) => {
        if (prop !== 'then') {  // avoid Promise issues
            console.log('Access:', prop);
        }
        return target[prop];
    }
});
window.navigator = nav;

// 3. Log cookie operations
var cookieDesc = Object.getOwnPropertyDescriptor(document, 'cookie');
Object.defineProperty(document, 'cookie', {
    get: function() {
        console.log('Cookie read');
        return cookieDesc.get.call(this);
    },
    set: function(value) {
        console.log('Cookie written:', value);
        return cookieDesc.set.call(this, value);
    }
});

// Now reload page and check console
```

## Step 7: Algorithm Reverse-Engineering

Once you understand the challenge structure:

```python
# Example: Extract nonce from page, compute token

import requests
import re
import hashlib
from bs4 import BeautifulSoup

# 1. Get the page
r = requests.get('https://target.com', headers={...})
html = r.text

# 2. Extract nonce (look for data-nonce, _nonce, etc.)
nonce = re.search(r'data-nonce="([^"]*)"', html).group(1)
print(f"Nonce: {nonce}")

# 3. Reverse-engineer token algorithm
# From analysis, you found it's: reverse(nonce) + sha256(nonce + salt)
token = nonce[::-1] + hashlib.sha256((nonce + 'salt').encode()).hexdigest()

# 4. Set cookie and proceed
headers['Cookie'] = f'incap_ses_{token}'
r = requests.get('https://target.com', headers=headers)

if 'Welcome' in r.text:
    print("Success!")
```

## Step 8: Test & Validate

Create a test client:

```bash
python3 tools/crack_cipher_client.py https://target.com/
```

Or modify the example client to use your discovered token algorithm.

## Complete Example: Real Sensor Analysis

### Input: Obfuscated sensor.js (108KB)

```bash
# Step 1: High-level overview
$ python3 tools/anti_detection_analyzer.py sensor.js
# Output: Detects 5 mechanisms (headless, automation, RC4, cookie-challenge, timing)

# Step 2: Extract strings
$ python3 tools/deobfuscator.py sensor.js > /tmp/analysis.txt
$ head -50 /tmp/analysis.txt
# Found: 1200 decoded strings, 2 RC4 keys, base64 payload

# Step 3: Try RC4 decryption
$ python3 tools/rc4_decryptor.py sensor.js "Bot_Manager"
# Result: Successfully decrypted payload reveals actual challenge algorithm

# Step 4: Implement Python client
# Use: reverse(nonce) + hex(charCodeAt(i) + 7 for each char)
# Base64 encode and set as cookie

# Step 5: Test
$ python3 crack_cipher_client.py https://target.com/
# Output: ✓ Challenge solved, flag retrieved
```

## Troubleshooting

### "No RC4 indicators found"
- Code might use a different cipher (AES, XOR, custom)
- Look for other patterns in deobfuscator output

### "RC4 decryption unsuccessful"
- Wrong key guess
- Code might not be RC4-encrypted, just obfuscated
- Try different key variations (lowercase, reversed, etc.)

### "Can't extract algorithm from code"
- Use dynamic analysis (browser console)
- Trace actual values at runtime
- Check what cookies/headers the real browser sends

### "Anti-detection bypasses not working"
- Make sure to patch BEFORE code runs (add_init_script)
- Test each bypass individually
- Check browser dev tools for errors

## Tools Reference

| Tool | Use Case | Example |
|------|----------|---------|
| `anti_detection_analyzer.py` | Quick overview of detection mechanisms | `python3 tools/anti_detection_analyzer.py code.js` |
| `deobfuscator.py` | Extract and analyze string arrays | `python3 tools/deobfuscator.py code.js \| grep -i cookie` |
| `rc4_decryptor.py` | Analyze RC4 patterns and decrypt | `python3 tools/rc4_decryptor.py code.js "key"` |

## Next Steps

- Implement bypass in your client (Python requests, Playwright, etc.)
- Test against live target
- Document detection mechanisms found for future reference
- Report findings (if authorized)
