# Using WAF Sensor Analysis in Google Colab

Analyze real-world obfuscated WAF sensors (Imperva, Cloudflare, etc.) directly in Google Colab without installing anything locally.

## Quick Start

### 1. Open in Colab

Click to open a new Colab notebook:
[Open in Colab](https://colab.research.google.com/drive/new)

### 2. Copy the Analysis Code

In the first cell, paste:

```python
# Download and import the analysis tools
!wget -q https://raw.githubusercontent.com/netanelcyber/HAMIVTZAR/main/waf-lab-incapsula/tools/colab_analysis.py
from colab_analysis import analyze_code, analyze_sensor_url
```

### 3. Run Analysis

**Option A: Analyze Sample Code**
```python
sample_code = '''
var _0x1234 = ['\\x63\\x6f\\x6f\\x6b\\x69\\x65', '\\x74\\x6f\\x6b\\x65\\x6e'];
console.log = function() {};
if (navigator.webdriver) alert('detected');
'''
analyze_code(sample_code)
```

**Option B: Download from URL**
```python
# Analyze a sensor from a real URL
analyze_sensor_url('https://events-new.mepha.ch/_Incapsula_Resource?SWJIYLWA=...')
```

**Option C: Upload Your Own File**
```python
from google.colab import files
uploaded = files.upload()
filename = list(uploaded.keys())[0]
with open(filename) as f:
    code = f.read()
analyze_code(code)
```

## What It Analyzes

### Anti-Detection Mechanisms (8 types)
- ✓ Headless browser detection (navigator.webdriver)
- ✓ Browser automation detection (Selenium, Puppeteer)
- ✓ Node.js environment checks
- ✓ Timing-based detection (setTimeout, performance)
- ✓ Console disabling (anti-debugging)
- ✓ Dynamic code execution (eval, Function)
- ✓ And 2 more...

### Obfuscation Patterns
- ✓ Hex-encoded string arrays (\x**)
- ✓ String deobfuscation
- ✓ Variable mapping extraction
- ✓ RC4 encryption indicators
- ✓ Base64 payload identification

## Example Output

```
================================================================================
ANTI-DETECTION ANALYSIS
================================================================================

⚠️  Found 6 detection mechanism(s):

1. HEADLESS BROWSER
   Patterns: HeadlessChrome, navigator.webdriver
   Bypass:   Override User-Agent, patch navigator.webdriver

2. BROWSER AUTOMATION
   Patterns: webdriver, automation
   Bypass:   Use stealth plugins, patch navigator properties

3. CONSOLE DISABLE
   Patterns: console.log =
   Bypass:   Restore console before code runs

...

================================================================================
OBFUSCATION ANALYSIS
================================================================================

File size: 45230 bytes
Hex-encoded strings: 847
String arrays detected: 2

📋 Decoded Strings (first array):
  1. cookie
  2. token
  3. verify
  4. navigator
  5. webdriver
  6. HeadlessChrome
  ...

🚨 Suspicious patterns:
  - eval: Found 5 occurrence(s)
  - base64_decode: Found 8 occurrence(s)
  - rc4_ksa: Found 1 occurrence(s)
```

## Analyzing Real Incapsula Sensors

If you have access to a real Incapsula sensor URL:

```python
# Extract the full URL from your target
sensor_url = "https://your-target.com/_Incapsula_Resource?..."

# Analyze it
results = analyze_sensor_url(sensor_url)

# Results contain detection mechanisms and bypass strategies
print("Detected mechanisms:", list(results['detections'].keys()))
```

## Next Steps

After analysis, you have two options:

### 1. Browser-Based Bypass (Playwright)
```python
from playwright.async_api import async_playwright

async def bypass_waf():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Apply bypasses based on detection analysis
        await context.add_init_script('''
            Object.defineProperty(navigator, "webdriver", {get: () => undefined});
            Object.defineProperty(navigator, "plugins", {get: () => []});
        ''')
        
        page = await context.new_page()
        await page.goto('https://target.com/')
        content = await page.content()
        await browser.close()
        
        return content
```

### 2. Algorithm-Based Bypass (Requests)
```python
# Extract algorithm from decoded strings
# Implement token computation in Python
# Forge challenge cookies
# Use regular requests (no browser needed)

import hashlib

def compute_token(nonce):
    # Based on patterns found in analysis
    reversed_nonce = nonce[::-1]
    hash_part = hashlib.sha256(nonce.encode()).hexdigest()
    return reversed_nonce + hash_part

token = compute_token(nonce)
cookies = {'incap_ses_': token}
response = requests.get(url, cookies=cookies)
```

## Limitations

- **Cannot decrypt RC4 without key** (see OBFUSCATION_ANALYSIS.md for key-finding techniques)
- **Some modern obfuscation** (webpack, terser) requires additional decompilation
- **Server-side detection** (TLS fingerprinting, IP reputation) not analyzed here
- **Timing-based detection** requires runtime analysis (use browser approach)

## Educational Use Only

This toolkit is for:
- ✓ Learning about bot-detection techniques
- ✓ Authorized security testing (with permission)
- ✓ CTF challenges and labs
- ✓ Academic research

**Not for:**
- ✗ Unauthorized scraping
- ✗ Bypassing security on targets you don't own
- ✗ Malicious purposes

See `scope.md` for legal/ethical guidelines.

## Tips

1. **Save results to file:**
   ```python
   import json
   with open('analysis_results.json', 'w') as f:
       json.dump(results, f, indent=2)
   
   from google.colab import files
   files.download('analysis_results.json')
   ```

2. **Analyze multiple URLs:**
   ```python
   urls = [
       'https://target1.com/sensor.js',
       'https://target2.com/sensor.js'
   ]
   
   for url in urls:
       print(f"\n{'='*80}")
       print(f"Analyzing {url}")
       print('='*80)
       analyze_sensor_url(url)
   ```

3. **Extract specific information:**
   ```python
   # Get only detection mechanisms
   detector = AntiDetectionAnalyzer(code)
   findings = detector.analyze()
   print("Detections:", list(findings.keys()))
   
   # Get deobfuscated strings
   deobf = JSDeobfuscator(code)
   arrays = deobf.extract_string_arrays()
   print("Decoded strings:", arrays[0][:500])
   ```

## References

- Full documentation: `OBFUSCATION_ANALYSIS.md`
- Step-by-step workflow: `ANALYSIS_WORKFLOW.md`
- Local tools: `tools/deobfuscator.py`, `tools/rc4_decryptor.py`, `tools/anti_detection_analyzer.py`
