# Obfuscation Analysis Tools Summary

Complete toolkit for analyzing real-world obfuscated WAF sensor scripts.

## What's Included

### 3 Analysis Tools

1. **deobfuscator.py** (247 lines)
   - Extracts hex-encoded strings (`\x**` → ASCII)
   - Analyzes string array obfuscation patterns
   - Detects suspicious patterns:
     - RC4 cipher usage
     - `eval()` / `Function()` execution
     - Base64 encoding/decoding
     - Console disabling
     - Anti-debugging checks
   - Maps variable-to-string relationships
   - Identifies Base64 payloads for further analysis

2. **rc4_decryptor.py** (197 lines)
   - Implements RC4 cipher for decryption
   - Finds RC4 indicators (KSA, PRGA, charCodeAt patterns)
   - Extracts Base64-encoded payloads
   - Identifies possible RC4 keys
   - Attempts decryption with known/guessed keys
   - Outputs decrypted JavaScript for analysis

3. **anti_detection_analyzer.py** (355 lines)
   - Maps 14 detection mechanism types:
     - Headless browser detection
     - Browser automation detection
     - Node.js environment checks
     - Geolocation checks
     - Device fingerprinting
     - Timing-based detection
     - Console disabling
     - And 7 more...
   - Provides bypass strategies for each
   - Priority-ranked bypass recommendations
   - JSON output for programmatic use

### 2 Comprehensive Guides

1. **OBFUSCATION_ANALYSIS.md** (368 lines)
   - 6 common obfuscation patterns with code examples
   - How each pattern works
   - Bypass techniques for each
   - Tool usage documentation
   - Real-world examples
   - Legal/ethical guidelines

2. **tools/ANALYSIS_WORKFLOW.md** (358 lines)
   - Step-by-step analysis procedure
   - How to extract obfuscated code from live targets
   - Correct tool sequence to use
   - Static vs. dynamic analysis methods
   - Browser console hooks for runtime analysis
   - Troubleshooting guide
   - Complete worked example

## Quick Start

### Scenario 1: Quick Detection Overview
```bash
python3 tools/anti_detection_analyzer.py sensor.js
```
Output: What detection mechanisms are present, in priority order

### Scenario 2: Full String Extraction
```bash
python3 tools/deobfuscator.py sensor.js > analysis.txt
```
Output: All decoded strings, RC4 indicators, Base64 payloads

### Scenario 3: RC4 Decryption
```bash
python3 tools/rc4_decryptor.py sensor.js "suspected_key"
```
Output: Decrypted payload if key is correct, or hints about RC4 patterns

## Example Output

### Anti-Detection Analysis
```
Found 5 detection mechanism(s):

1. HEADLESS BROWSER
   Description: Detects headless browser execution
   Detected patterns: navigator.webdriver
   Bypass strategy: Override User-Agent, patch navigator.webdriver

2. CONSOLE DISABLE
   Description: Disables console for anti-debugging
   Detected patterns: console.log =
   Bypass strategy: Restore console before code runs
```

### Deobfuscator Analysis
```
[*] Hex-encoded strings found: 847
[*] String arrays detected: 2
[*] Suspicious patterns detected:
    - eval: Found 3 occurrence(s)
    - base64_decode: Found 8 occurrence(s)
    - rc4_ksa: Found 1 occurrence(s)
```

## How It Works

### Analysis Pipeline

```
Obfuscated JavaScript
        ↓
┌───────────────────┐
│ Anti-Detection    │ → Identify: headless, automation, timing checks
│ Analyzer          │           Priority bypass order
└───────────────────┘
        ↓
┌───────────────────┐
│ Deobfuscator      │ → Extract: strings, functions, RC4 indicators
│                   │           Base64 payloads
└───────────────────┘
        ↓
┌───────────────────┐
│ RC4 Decryptor     │ → Decrypt: encrypted payloads (if key found)
│                   │          Analyze decrypted code
└───────────────────┘
        ↓
Actionable Insights
  - What detects me
  - How to bypass it
  - What algorithm(s) to reverse-engineer
```

### Detection Mechanism Categories

| Category | Examples | Bypass |
|----------|----------|--------|
| **Browser Environment** | `navigator.webdriver`, `chrome.runtime` | Patch objects, stealth plugins |
| **Code Execution** | `eval()`, `Function()`, dynamic loading | Analyze eval'd code separately |
| **Timing** | `setTimeout`, `performance.timing` | Override timing functions |
| **Storage** | `localStorage`, `indexedDB`, cookies | Clear or mock storage |
| **Device Fingerprint** | Canvas, WebGL, audio context | Use real browser |
| **Geolocation** | IP checks, GPS coordinates | Match location to IP |

## Tool Comparison

| Need | Tool | Output |
|------|------|--------|
| "What detection mechanisms exist?" | `anti_detection_analyzer.py` | JSON, priority list, bypass strategies |
| "Decode all the strings" | `deobfuscator.py` | Hex-decoded strings, pattern analysis |
| "Decrypt the payload" | `rc4_decryptor.py` | Decrypted JavaScript, key suggestions |
| "Full workflow" | `ANALYSIS_WORKFLOW.md` | Step-by-step guide with examples |

## Real-World Usage

### Example: Analyzing Incapsula Sensor

```bash
# 1. Get quick overview of detection mechanisms
$ python3 tools/anti_detection_analyzer.py incap_sensor.js
# → Found: headless detection, RC4 encryption, cookie challenge, timing checks

# 2. Extract all strings to understand algorithm
$ python3 tools/deobfuscator.py incap_sensor.js | grep -i "cookie\|token\|nonce"
# → "incap_ses_", "compute_token", "nonce"

# 3. Try RC4 decryption with guessed key
$ python3 tools/rc4_decryptor.py incap_sensor.js "imperva"
# → If successful: decrypted challenge algorithm

# 4. Implement Python bypass using found algorithm
# → Compute token from nonce
# → Set cookie
# → Request proceeds
```

## Architecture

### Deobfuscator
- Uses regex to extract hex patterns and string arrays
- Maps variable names to their string indices
- Identifies suspicious patterns via keyword search
- Analyzes control flow structure

### RC4 Decryptor
- Implements KSA (Key Scheduling Algorithm)
- Implements PRGA (Pseudo-Random Generation Algorithm)
- Supports Base64 payload extraction
- Attempts multiple key variations

### Anti-Detection Analyzer
- Maps 14 different detection mechanism patterns
- Ranks by bypass priority
- Provides bypass strategies for each
- Outputs structured JSON for automation

## Limitations & Future Work

### Current Limitations
- Cannot deobfuscate if strings use XOR or custom encoding (only hex/base64)
- RC4 key must be guessed or extracted from code
- Some modern obfuscation (webpack, terser) requires additional tools
- Cannot analyze server-side detection logic

### Could Add
- XOR/custom cipher support
- Automatic key brute-forcing for RC4
- AST-based analysis for control flow
- Selenium WebDriver detection bypass
- TLS fingerprint analysis (JA3)

## Files Added

```
waf-lab-incapsula/
├── tools/
│   ├── deobfuscator.py              (247 lines)
│   ├── rc4_decryptor.py             (197 lines)
│   ├── anti_detection_analyzer.py   (355 lines)
│   └── ANALYSIS_WORKFLOW.md         (358 lines)
├── OBFUSCATION_ANALYSIS.md          (368 lines)
├── ANALYSIS_TOOLS_SUMMARY.md        (this file)
└── README.md                         (updated with tool references)
```

Total: ~1,882 lines of analysis code and documentation

## Integration with Lab

These tools complement the existing WAF lab:

- **Lab WAF** (`waf-proxy/proxy.py`): Educational simplified detection
- **Bypass Clients** (`tools/naive_client.py`, etc.): Working around detection
- **Analysis Tools** (new): Understanding real-world obfuscation

Together: Complete educational package for understanding bot-detection bypass techniques.

## References

- [Incapsula Bypass Guide](https://scrapfly.io/blog/bypass-incapsula-waf/)
- [Cloudflare Challenge Analysis](https://blog.cloudflare.com/browser-rendering-api/)
- [JavaScript Obfuscation Techniques](https://github.com/javascript-obfuscator/javascript-obfuscator)
- [RC4 Cipher](https://en.wikipedia.org/wiki/RC4)
- [OWASP - Web Application Firewalls](https://owasp.org/www-community/attacks/Forcing_use_of_cached_pages)

---

For detailed usage, see:
- `ANALYSIS_WORKFLOW.md` → Step-by-step how to use tools
- `OBFUSCATION_ANALYSIS.md` → Technical deep-dive on patterns
- Individual tool `--help` or `-h` flags
