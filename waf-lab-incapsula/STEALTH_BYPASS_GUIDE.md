# Stealth Browser Bypass Guide

Complete guide to using `stealth_browser_bypass.py` for defeating Incapsula/Imperva WAF sensors.

## Installation

### Prerequisites
```bash
# Python 3.7+
python3 --version

# Install Playwright
pip install playwright

# Install Chromium browser
playwright install chromium
```

## Quick Start

### Basic Usage
```bash
python3 tools/stealth_browser_bypass.py https://target.com
```

### With Options
```bash
# Visible browser (not headless)
python3 tools/stealth_browser_bypass.py https://target.com --headless false

# Save HTML output
python3 tools/stealth_browser_bypass.py https://target.com --output result.html

# Save results as JSON
python3 tools/stealth_browser_bypass.py https://target.com --json-output results.json

# Use proxy
python3 tools/stealth_browser_bypass.py https://target.com --proxy socks5://localhost:9050

# All options
python3 tools/stealth_browser_bypass.py https://target.com \
  --headless false \
  --output page.html \
  --json-output results.json \
  --proxy socks5://localhost:9050
```

## How It Works

### 12 Stealth Patches Applied

The script applies comprehensive stealth patches to bypass detection:

1. **Hide WebDriver API**
   - Removes `navigator.webdriver` property
   - Prevents automation detection

2. **Hide Automation Markers**
   - Removes Puppeteer/Playwright/Selenium markers
   - Spoof browser plugins array

3. **Spoof Chrome Extensions**
   - Create fake `window.chrome.runtime` object
   - Hide extension context detection

4. **Restore Console**
   - Re-enable console.log if disabled
   - Prevents anti-debugging from working

5. **Override Timing Functions**
   - Add realistic jitter to `performance.now()`
   - Defeat debugger detection via timing

6. **Hide Headless Markers**
   - Spoof User-Agent if it says "HeadlessChrome"
   - Return realistic browser signature

7. **Mock Screen Properties**
   - Set realistic display dimensions (1920x1080)
   - Mock color depth and pixel ratio

8. **Mock Storage APIs**
   - Replace localStorage/sessionStorage with fake implementations
   - Prevent storage-based detection

9. **Disable Debugger Detection**
   - Override `Function.prototype.toString()`
   - Return "[native code]" for all functions

10. **Mock Permissions API**
    - Return "denied" for all permission queries
    - Prevent permission-based detection

11. **Mock Battery/Device APIs**
    - Fake battery status
    - Pretend device is fully charged

12. **Mock Geolocation**
    - Provide fake geolocation coordinates
    - Prevent geo-based blocking

### Browser Context Spoofing

```python
# User-Agent
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# Viewport
1920x1080

# Timezone
America/New_York

# Language
en-US

# Geolocation
40.7128, -74.0060 (New York)
```

## Examples

### Example 1: Simple Bypass

```bash
python3 tools/stealth_browser_bypass.py https://example.com/protected
```

**Output:**
```
2026-07-23 10:15:32,123 - INFO - Initialized bypass for: https://example.com/protected
2026-07-23 10:15:32,234 - INFO - Launching browser...
2026-07-23 10:15:35,456 - INFO - ✓ Stealth patches applied
2026-07-23 10:15:35,567 - INFO - Navigating to: https://example.com/protected
2026-07-23 10:15:38,789 - INFO - ✓ Status: 200
2026-07-23 10:15:38,890 - INFO - ✓ Title: Protected Page
2026-07-23 10:15:38,891 - INFO - ✓ Content: 45230 bytes
2026-07-23 10:15:39,012 - INFO - Browser closed

================================================================================
BYPASS RESULTS
================================================================================

URL: https://example.com/protected
Status: 200
Title: Protected Page
Content: 45230 bytes
Success: True
```

### Example 2: Save Content

```bash
python3 tools/stealth_browser_bypass.py https://example.com/protected \
  --output content.html \
  --json-output metadata.json
```

**Creates:**
- `content.html` - Complete page content
- `metadata.json` - Results metadata (status, cookies, headers)

### Example 3: Debug with Visible Browser

```bash
python3 tools/stealth_browser_bypass.py https://example.com/protected \
  --headless false
```

**Result:** Browser window opens, you can see what's happening in real-time.

### Example 4: Use Proxy

```bash
# SOCKS5 proxy
python3 tools/stealth_browser_bypass.py https://example.com/protected \
  --proxy socks5://localhost:9050

# HTTP proxy
python3 tools/stealth_browser_bypass.py https://example.com/protected \
  --proxy http://proxy.example.com:8080
```

## Integration into Your Code

### As a Library

```python
import asyncio
from stealth_browser_bypass import StealthBrowserBypass

async def main():
    bypass = StealthBrowserBypass(
        url='https://target.com/',
        headless=True,
        proxy=None
    )
    results = await bypass.bypass()
    
    if results['success']:
        print(f"✓ Status: {results['status']}")
        print(f"✓ Cookies: {len(results['cookies'])}")
    else:
        print(f"❌ Error: {results['error']}")

asyncio.run(main())
```

### Save Content

```python
import asyncio
from stealth_browser_bypass import StealthBrowserBypass

async def main():
    bypass = StealthBrowserBypass('https://target.com/')
    success, message = await bypass.bypass_and_save_content('output.html')
    print(message)

asyncio.run(main())
```

## Troubleshooting

### "Playwright not installed"
```bash
pip install playwright
playwright install chromium
```

### "Connection refused"
- Check if target URL is accessible
- Try with `--headless false` to see errors
- Check if proxy is working (if using proxy)

### "Timeout waiting for selector"
- Increase timeout: Modify script to use `wait_until='load'` instead of `'networkidle'`
- Page might be protected with JavaScript challenges
- Try with `--headless false` to debug

### "403 Forbidden after bypass"
- Stealth patches might not be enough for this WAF
- Try:
  1. Use different User-Agent
  2. Add delays between requests
  3. Use residential proxy
  4. Check if cookies are being set correctly

### "Cookies not being set"
- Check JSON output for Set-Cookie headers
- Verify context.cookies() actually has them
- Some sites set cookies via JavaScript (should work with this script)

## Detection Mechanisms Defeated

| Mechanism | Detection Method | Bypass Method |
|-----------|-----------------|---------------|
| Headless Browser | HeadlessChrome in UA | Spoof real Chrome UA |
| WebDriver API | `navigator.webdriver` | Delete property |
| Automation Tools | Process markers | Remove Playwright markers |
| Debugger | Timing gaps | Override timing functions |
| Console Disable | console is undefined | Restore console object |
| Anti-Debugging | Function.toString() | Return "[native code]" |
| Extension Checks | chrome.runtime missing | Fake chrome object |
| Storage Access | localStorage/sessionStorage | Mock storage APIs |
| Permissions | navigator.permissions | Return "denied" |
| Geolocation | navigator.geolocation | Provide fake coords |

## Performance

- **First run**: ~5-10 seconds (browser launch)
- **Subsequent runs**: ~3-5 seconds (page load)
- **Memory usage**: ~150-200 MB per browser instance
- **CPU usage**: Moderate (Chromium process)

## Advanced Usage

### Custom Stealth Patches

Modify `STEALTH_PATCHES` in the script to add custom patches:

```python
CUSTOM_PATCHES = """
// Your custom JavaScript here
console.log('Custom patch applied');
"""

# Add to browser context
await context.add_init_script(CUSTOM_PATCHES)
```

### Multiple Concurrent Requests

```python
import asyncio

async def bypass_multiple(urls):
    tasks = [
        StealthBrowserBypass(url).bypass()
        for url in urls
    ]
    results = await asyncio.gather(*tasks)
    return results

urls = ['https://site1.com', 'https://site2.com', 'https://site3.com']
results = asyncio.run(bypass_multiple(urls))
```

### Extract Specific Data

```python
bypass = StealthBrowserBypass('https://target.com/')
results = await bypass.bypass()

# Extract cookies
cookies = {c['name']: c['value'] for c in results['cookies']}
print(f"incap_ses: {cookies.get('incap_ses_')}")

# Extract headers
headers = results.get('headers', {})
print(f"Server: {headers.get('server')}")
```

## Legal & Ethical

**Educational Use Only**

This tool is for:
✅ Learning about bot-detection
✅ Authorized security testing
✅ CTF challenges
✅ Your own websites
✅ Academic research

**Not for:**
❌ Unauthorized access to protected sites
❌ Scraping confidential data
❌ Evading security on targets you don't own
❌ Malicious purposes

## References

- [Playwright Documentation](https://playwright.dev/python/)
- [Stealth.js Project](https://github.com/berstend/puppeteer-extra/tree/master/packages/puppeteer-extra-plugin-stealth)
- [WebDriver Detection Methods](https://developer.mozilla.org/en-US/docs/Web/WebDriver)

## Support

For issues:
1. Check troubleshooting section above
2. Try `--headless false` to see errors
3. Check browser console logs
4. Review Playwright documentation

---

**Ready to use!** The script handles all complexity for you. Just point it at your target and it will apply all stealth patches automatically.
