#!/usr/bin/env python3
"""
Stealth Browser Bypass for Incapsula/Imperva WAF Sensors

Implements browser-based bypass using Playwright with comprehensive
stealth patches to defeat bot-detection mechanisms.

Usage:
    python3 stealth_browser_bypass.py <url>
    python3 stealth_browser_bypass.py https://target.com/
    python3 stealth_browser_bypass.py https://target.com/ --headless=false
    python3 stealth_browser_bypass.py https://target.com/ --proxy socks5://localhost:9050

Features:
    - Headless browser detection bypass
    - Browser automation detection bypass
    - Console disabling bypass
    - Timing-based detection bypass
    - WebDriver detection bypass
    - Real browser fingerprinting
    - Proxy support
    - Result export (HTML + JSON)
"""

import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from argparse import ArgumentParser
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

# Try to import Playwright, provide helpful error if missing
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    print("❌ Playwright not installed. Install with:")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StealthBrowserBypass:
    """
    Browser-based WAF bypass using stealth techniques.
    
    Defeats:
    - Headless browser detection
    - Browser automation detection
    - Console disabling
    - Timing-based detection
    - WebDriver API checks
    """

    # Comprehensive stealth JavaScript patches
    STEALTH_PATCHES = """
    // ====================================================================
    // STEALTH PATCH 1: Hide WebDriver API
    // ====================================================================
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        set: () => {}
    });
    
    // ====================================================================
    // STEALTH PATCH 2: Hide Automation Tool Markers
    // ====================================================================
    // Hide Playwright/Puppeteer/Selenium markers
    delete Object.getPrototypeOf(navigator).webdriver;
    
    // Hide Puppeteer specific markers
    Object.defineProperty(navigator, 'plugins', {
        get: () => [],
        set: () => {}
    });
    
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
        set: () => {}
    });
    
    // ====================================================================
    // STEALTH PATCH 3: Spoof Chrome Extensions API
    // ====================================================================
    window.chrome = {
        runtime: {}
    };
    
    // Hide extension-related markers
    if (!navigator.chrome) {
        Object.defineProperty(navigator, 'chrome', {
            get: () => ({ runtime: {} }),
            set: () => {}
        });
    }
    
    // ====================================================================
    // STEALTH PATCH 4: Restore Console (Anti-Debugging Defense)
    // ====================================================================
    const originalLog = console.log;
    const originalError = console.error;
    const originalWarn = console.warn;
    const originalDebug = console.debug;
    
    Object.defineProperty(window, 'console', {
        value: {
            log: originalLog,
            error: originalError,
            warn: originalWarn,
            debug: originalDebug,
            info: originalLog,
            trace: originalLog,
            clear: () => {},
            assert: () => {},
            count: () => {},
            group: () => {},
            groupEnd: () => {},
            time: () => {},
            timeEnd: () => {},
            profile: () => {},
            profileEnd: () => {},
            dir: () => {},
            table: () => {}
        },
        writable: false,
        configurable: false
    });
    
    // ====================================================================
    // STEALTH PATCH 5: Override Timing Functions (Anti-Debugger)
    // ====================================================================
    const t0 = performance.now();
    const startTime = Date.now();
    
    Object.defineProperty(window.performance, 'now', {
        value: function() {
            return t0 + Math.random() * 10;  // Realistic timing jitter
        }
    });
    
    Object.defineProperty(Date, 'now', {
        value: function() {
            return startTime + Math.random() * 100;
        }
    });
    
    // ====================================================================
    // STEALTH PATCH 6: Hide Headless Chrome Markers
    // ====================================================================
    // Override User-Agent if still says "HeadlessChrome"
    Object.defineProperty(navigator, 'userAgent', {
        get: function() {
            return this._userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';
        },
        set: function(ua) {
            this._userAgent = ua;
        }
    });
    
    // ====================================================================
    // STEALTH PATCH 7: Mock Screen/Display Properties
    // ====================================================================
    Object.defineProperty(window.screen, 'width', {
        get: () => 1920,
        set: () => {}
    });
    
    Object.defineProperty(window.screen, 'height', {
        get: () => 1080,
        set: () => {}
    });
    
    Object.defineProperty(window.screen, 'availWidth', {
        get: () => 1920,
        set: () => {}
    });
    
    Object.defineProperty(window.screen, 'availHeight', {
        get: () => 1040,
        set: () => {}
    });
    
    Object.defineProperty(window.screen, 'colorDepth', {
        get: () => 24,
        set: () => {}
    });
    
    Object.defineProperty(window.screen, 'pixelDepth', {
        get: () => 24,
        set: () => {}
    });
    
    Object.defineProperty(window, 'devicePixelRatio', {
        get: () => 1,
        set: () => {}
    });
    
    // ====================================================================
    // STEALTH PATCH 8: Mock Storage APIs
    // ====================================================================
    Object.defineProperty(window, 'localStorage', {
        value: {
            getItem: () => null,
            setItem: () => {},
            removeItem: () => {},
            clear: () => {},
            length: 0
        }
    });
    
    Object.defineProperty(window, 'sessionStorage', {
        value: {
            getItem: () => null,
            setItem: () => {},
            removeItem: () => {},
            clear: () => {},
            length: 0
        }
    });
    
    // ====================================================================
    // STEALTH PATCH 9: Disable Debugger Detection
    // ====================================================================
    // Prevent debugger from triggering detection
    const origFunctionProto = Function.prototype;
    const origToString = origFunctionProto.toString;
    
    origFunctionProto.toString = function() {
        if (this === origFunctionProto) {
            return origToString.call(this);
        }
        return 'function() { [native code] }';
    };
    
    // ====================================================================
    // STEALTH PATCH 10: Mock Permissions API
    // ====================================================================
    Object.defineProperty(navigator, 'permissions', {
        value: {
            query: async () => ({ state: 'denied' })
        }
    });
    
    // ====================================================================
    // STEALTH PATCH 11: Mock Battery/Device APIs
    // ====================================================================
    Object.defineProperty(navigator, 'getBattery', {
        value: async () => ({
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: 0.8
        })
    });
    
    // ====================================================================
    // STEALTH PATCH 12: Mock Geolocation
    // ====================================================================
    Object.defineProperty(navigator, 'geolocation', {
        value: {
            getCurrentPosition: (success) => {
                success({
                    coords: {
                        latitude: 40.7128,
                        longitude: -74.0060,
                        accuracy: 10
                    }
                });
            },
            watchPosition: (success) => {
                success({
                    coords: {
                        latitude: 40.7128,
                        longitude: -74.0060,
                        accuracy: 10
                    }
                });
            }
        }
    });
    
    // ====================================================================
    // Log that patches are active (for debugging)
    // ====================================================================
    console.log('[STEALTH] All stealth patches applied successfully');
    """

    def __init__(self, url: str, headless: bool = True, proxy: Optional[str] = None):
        """
        Initialize bypass instance.
        
        Args:
            url: Target URL to access
            headless: Run browser in headless mode (True) or visible (False)
            proxy: Proxy URL (e.g., socks5://localhost:9050)
        """
        self.url = url
        self.headless = headless
        self.proxy = proxy
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.results: Dict = {}
        
        logger.info(f"Initialized bypass for: {url}")
        logger.info(f"Headless: {headless}, Proxy: {proxy or 'none'}")

    async def launch_browser(self, playwright) -> Tuple[Browser, BrowserContext]:
        """Launch Playwright browser with stealth configuration."""
        logger.info("Launching browser...")
        
        # Launch browser
        launch_args = {
            'headless': self.headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        }
        
        if self.proxy:
            launch_args['proxy'] = {'server': self.proxy}
            logger.info(f"Using proxy: {self.proxy}")
        
        browser = await playwright.chromium.launch(**launch_args)
        
        # Create context with stealth config
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            permissions=['geolocation'],
        )
        
        # Apply stealth patches
        await context.add_init_script(self.STEALTH_PATCHES)
        logger.info("✓ Stealth patches applied")
        
        return browser, context

    async def bypass(self) -> Dict:
        """
        Execute the bypass and retrieve content.
        
        Returns:
            Dict with:
            - status: HTTP status code
            - url: Final URL (after redirects)
            - content: HTML content
            - title: Page title
            - cookies: Set cookies
            - headers: Response headers
            - success: Whether bypass succeeded
        """
        async with async_playwright() as playwright:
            try:
                self.browser, self.context = await self.launch_browser(playwright)
                self.page = await self.context.new_page()
                
                logger.info(f"Navigating to: {self.url}")
                
                # Navigate to target
                response = await self.page.goto(self.url, wait_until='networkidle')
                
                # Collect results
                self.results = {
                    'url': self.url,
                    'status': response.status if response else 0,
                    'final_url': self.page.url,
                    'title': await self.page.title(),
                    'content_length': len(await self.page.content()),
                    'cookies': await self.context.cookies(),
                    'timestamp': datetime.now().isoformat(),
                    'success': True,
                    'error': None
                }
                
                logger.info(f"✓ Status: {self.results['status']}")
                logger.info(f"✓ Title: {self.results['title']}")
                logger.info(f"✓ Content: {self.results['content_length']} bytes")
                
                # Extract headers
                if response:
                    self.results['headers'] = dict(response.headers)
                
                return self.results
                
            except Exception as e:
                logger.error(f"❌ Bypass failed: {e}")
                self.results = {
                    'url': self.url,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                return self.results
                
            finally:
                # Cleanup
                if self.page:
                    await self.page.close()
                if self.context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()
                logger.info("Browser closed")

    async def bypass_and_save_content(self, output_file: Optional[str] = None) -> Tuple[bool, str]:
        """
        Bypass WAF and save page content.
        
        Args:
            output_file: File to save HTML content to
            
        Returns:
            Tuple of (success, message)
        """
        async with async_playwright() as playwright:
            try:
                self.browser, self.context = await self.launch_browser(playwright)
                self.page = await self.context.new_page()
                
                logger.info(f"Navigating to: {self.url}")
                response = await self.page.goto(self.url, wait_until='networkidle')
                
                if response.status == 200:
                    content = await self.page.content()
                    
                    if output_file:
                        output_path = Path(output_file)
                        output_path.write_text(content)
                        logger.info(f"✓ Saved to: {output_file}")
                        return True, f"Successfully saved {len(content)} bytes to {output_file}"
                    else:
                        return True, f"Successfully retrieved {len(content)} bytes"
                else:
                    return False, f"Request failed with status {response.status}"
                    
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                return False, str(e)
                
            finally:
                if self.page:
                    await self.page.close()
                if self.context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()


async def main():
    """Command-line interface."""
    parser = ArgumentParser(
        description='Stealth browser bypass for Incapsula/Imperva WAF sensors'
    )
    parser.add_argument('url', help='Target URL')
    parser.add_argument('--headless', default='true', help='Run headless (true/false)')
    parser.add_argument('--proxy', help='Proxy URL (e.g., socks5://localhost:9050)')
    parser.add_argument('--output', help='Save HTML content to file')
    parser.add_argument('--json-output', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    # Validate URL
    parsed = urlparse(args.url)
    if not parsed.scheme:
        args.url = 'https://' + args.url
    
    headless = args.headless.lower() != 'false'
    
    # Run bypass
    bypass = StealthBrowserBypass(args.url, headless=headless, proxy=args.proxy)
    results = await bypass.bypass()
    
    # Print results
    print("\n" + "="*80)
    print("BYPASS RESULTS")
    print("="*80)
    print(f"\nURL: {results['url']}")
    print(f"Status: {results.get('status', 'N/A')}")
    print(f"Title: {results.get('title', 'N/A')}")
    print(f"Content: {results.get('content_length', 0)} bytes")
    print(f"Success: {results['success']}")
    
    if results['error']:
        print(f"Error: {results['error']}")
    
    # Show cookies
    if results.get('cookies'):
        print(f"\nCookies ({len(results['cookies'])}):")
        for cookie in results['cookies'][:5]:
            print(f"  - {cookie['name']}: {cookie['value'][:50]}")
        if len(results['cookies']) > 5:
            print(f"  ... and {len(results['cookies']) - 5} more")
    
    # Save JSON if requested
    if args.json_output:
        with open(args.json_output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Results saved to: {args.json_output}")
    
    # Save content if requested
    if args.output and results['success']:
        content = await bypass.bypass_and_save_content(args.output)
        logger.info(content[1])
    
    print("\n" + "="*80)
    
    return 0 if results['success'] else 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
