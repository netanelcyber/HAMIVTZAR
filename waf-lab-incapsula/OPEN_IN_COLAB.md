# Open WAF Analysis in Google Colab

## 🚀 One-Click Launch

Click the button below to open the interactive notebook in Google Colab:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/netanelcyber/HAMIVTZAR/blob/claude/waf-imperva-bypass-testing-dwg5b9/waf-lab-incapsula/WAF_Sensor_Analysis.ipynb)

## Manual Launch

1. Go to [Google Colab](https://colab.research.google.com)
2. Click **File** → **Open notebook**
3. Select **GitHub** tab
4. Paste: `netanelcyber/HAMIVTZAR`
5. Branch: `claude/waf-imperva-bypass-testing-dwg5b9`
6. Path: `waf-lab-incapsula/WAF_Sensor_Analysis.ipynb`

## What's Inside

### 📊 Analysis Tools (Pre-loaded)
- **Anti-Detection Analyzer**: Detects headless browser, automation, Node.js, timing, console, eval
- **JavaScript Deobfuscator**: Extracts hex strings, identifies patterns, finds Base64 payloads
- **Helper Functions**: URL download, file upload, result export

### 🎯 Three Usage Modes

**Option A: Sample Code**
```python
sample_code = "var _0x123 = ['\\x63\\x6f\\x6f\\x6b\\x69\\x65']; ..."
analyze_code(sample_code)
```

**Option B: Download from URL**
```python
analyze_sensor_url('https://target.com/sensor.js')
```

**Option C: Upload File**
```
Click "Choose Files" → Select .js file → Analyze
```

### 📈 Output

For each analysis:
- ✅ Detected detection mechanisms (with bypass strategies)
- ✅ Deobfuscated strings and arrays
- ✅ Suspicious pattern counts (eval, RC4, base64, etc.)
- ✅ Exportable JSON results

## Examples

### Analyze Sample Imperva Sensor
```python
sample_code = r'''
var _0x6911 = ['\\x63\\x6f\\x6f\\x6b\\x69\\x65', '\\x74\\x6f\\x6b\\x65\\x6e'];
console.log = function() {};
if (navigator.webdriver) alert('detected');
eval(atob('base64payload'));
'''
results = analyze_code(sample_code)
```

Output:
```
================================================================================
ANTI-DETECTION ANALYSIS
================================================================================

⚠️  Found 3 detection mechanism(s):

1. CONSOLE DISABLE
   Patterns: console.log =
   Bypass:   Restore console before code runs

2. HEADLESS BROWSER
   Patterns: navigator.webdriver
   Bypass:   Override User-Agent, patch navigator.webdriver

3. EVAL DETECTION
   Patterns: eval(
   Bypass:   Analyze eval'd code separately or patch eval

...
```

### Analyze Real Sensor URL
```python
# Real Incapsula sensor example
sensor_url = "https://events-new.mepha.ch/_Incapsula_Resource?SWJIYLWA=..."
results = analyze_sensor_url(sensor_url)
```

### Export Results
```python
import json
with open('results.json', 'w') as f:
    json.dump(results, f, indent=2)
files.download('results.json')
```

## Next Steps After Analysis

### Browser-Based Bypass (With Playwright)
```python
from playwright.async_api import async_playwright

async def bypass():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        await context.add_init_script('''
            Object.defineProperty(navigator, "webdriver", {get: () => undefined});
        ''')
        page = await context.new_page()
        await page.goto('https://target.com')
        await browser.close()
```

### Algorithm-Based Bypass (Pure Python)
```python
# From analysis, extract the challenge algorithm
# Implement in Python using hashlib, base64, etc.
# Forge cookies without running JavaScript

def compute_token(nonce):
    # Algorithm reverse-engineered from deobfuscated code
    reversed_nonce = nonce[::-1]
    token = reversed_nonce + hashlib.sha256(nonce.encode()).hexdigest()
    return base64.b64encode(token.encode()).decode()

cookies = {'incap_ses_': compute_token(nonce)}
response = requests.get(url, cookies=cookies)
```

## Requirements (Pre-installed in Colab)

- Python 3.9+
- `re` (regex - built-in)
- `base64` (built-in)
- `json` (built-in)
- `requests` (installed in first cell)
- `beautifulsoup4` (optional, installed in first cell)

## Features

✅ No installation required (runs in browser)
✅ No local setup needed
✅ Real-time analysis and results
✅ File upload and download support
✅ JSON export for programmatic use
✅ Interactive cell-by-cell execution
✅ Educational walkthroughs included

## Tips

1. **Save your work**: Colab auto-saves, but download results frequently
2. **Rate limiting**: If analyzing multiple URLs, add delays
3. **Large files**: Colab has memory limits (~12GB), split very large files
4. **Code inspection**: All analysis code visible - inspect for understanding
5. **Modify as needed**: Edit cells to customize analysis

## Troubleshooting

**"404 Not Found" when downloading sensor**
- Check URL accessibility
- Some servers block requests, try different headers
- May need authentication

**"No strings decoded"**
- Code might use different obfuscation (XOR, AES instead of hex)
- Very modern obfuscation might not be detected
- Check suspicious patterns for algorithm hints

**"Connection timeout"**
- Network issue or server blocked requests
- Retry with different User-Agent
- Try with different URL

## Legal & Ethical

This notebook is for:
✅ Learning about bot-detection
✅ Authorized security testing
✅ CTF challenges
✅ Academic research

Not for:
❌ Unauthorized scraping
❌ Bypassing security on targets you don't own
❌ Malicious purposes

See `scope.md` for full legal guidelines.

---

**Questions?** See `COLAB_USAGE.md`, `OBFUSCATION_ANALYSIS.md`, or `ANALYSIS_WORKFLOW.md` for detailed documentation.
