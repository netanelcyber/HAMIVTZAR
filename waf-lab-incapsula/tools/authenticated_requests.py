#!/usr/bin/env python3
"""
Authenticated Requests with Incapsula Cookies

Once you have valid Incapsula cookies (from stealth_browser_bypass.py),
use this script to make authenticated requests to protected sites.

Usage:
    python3 authenticated_requests.py <url> <visid_cookie> <incap_ses_cookie>
    python3 authenticated_requests.py https://target.com "ej+FBook..." "89t5NrUh..."
"""

import sys
import json
import requests
from argparse import ArgumentParser
from typing import Dict, Optional
from urllib.parse import urlparse


class AuthenticatedRequests:
    """Make authenticated requests with Incapsula cookies."""
    
    def __init__(self, url: str, visid_cookie: str, incap_ses_cookie: str):
        """
        Initialize with target URL and cookies.
        
        Args:
            url: Target URL
            visid_cookie: visid_incap_* cookie value
            incap_ses_cookie: incap_ses_* cookie value
        """
        self.url = url
        self.visid_cookie = visid_cookie
        self.incap_ses_cookie = incap_ses_cookie
        
        # Extract cookie domain/ID from visid cookie (format: visid_incap_XXXX)
        self.cookie_domain = self._extract_domain()
        
        # Build session
        self.session = requests.Session()
        self._setup_session()
    
    def _extract_domain(self) -> str:
        """Extract domain/ID from URL."""
        parsed = urlparse(self.url)
        return parsed.netloc
    
    def _setup_session(self):
        """Setup session with headers and cookies."""
        
        # Headers that look like real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        self.session.headers.update(headers)
        
        # Add cookies
        # Try to extract the cookie ID (e.g., 2160523 from visid_incap_2160523)
        try:
            cookie_id = self.visid_cookie.split('_')[-1] if '_' in self.visid_cookie else '0'
        except:
            cookie_id = '0'
        
        # Set cookies
        self.session.cookies.set(f'visid_incap_{cookie_id}', self.visid_cookie)
        self.session.cookies.set(f'incap_ses_{cookie_id}', self.incap_ses_cookie)
        
        print(f"✓ Cookies set:")
        print(f"  - visid_incap_{cookie_id}: {self.visid_cookie[:30]}...")
        print(f"  - incap_ses_{cookie_id}: {self.incap_ses_cookie[:30]}...\n")
    
    def request(self, method: str = 'GET', path: str = '/', **kwargs) -> Dict:
        """
        Make authenticated request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path (e.g., '/api/data')
            **kwargs: Additional requests parameters
            
        Returns:
            Dict with status, content, headers
        """
        # Build full URL
        if not path.startswith('/'):
            path = '/' + path
        full_url = self.url.rstrip('/') + path
        
        print(f"📨 {method} {full_url}")
        
        try:
            # Make request
            if method.upper() == 'GET':
                response = self.session.get(full_url, **kwargs)
            elif method.upper() == 'POST':
                response = self.session.post(full_url, **kwargs)
            else:
                response = self.session.request(method, full_url, **kwargs)
            
            # Extract info
            result = {
                'status': response.status_code,
                'url': response.url,
                'headers': dict(response.headers),
                'content_length': len(response.content),
                'is_text': 'text' in response.headers.get('content-type', ''),
                'content': response.text[:1000] if 'text' in response.headers.get('content-type', '') else None,
                'success': response.status_code == 200
            }
            
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Size: {len(response.content):,} bytes")
            
            if response.status_code == 200:
                print("✓ SUCCESS - Got through!")
            else:
                print(f"⚠️ Status {response.status_code}")

            if result['is_text']:
                print(f"  Content preview: {response.text[:300]!r}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                'status': 0,
                'error': str(e),
                'success': False
            }
    
    def get(self, path: str = '/', **kwargs) -> Dict:
        """GET request."""
        return self.request('GET', path, **kwargs)
    
    def post(self, path: str = '/', data: Optional[Dict] = None, **kwargs) -> Dict:
        """POST request."""
        if data:
            kwargs['json'] = data
        return self.request('POST', path, **kwargs)


def main():
    """CLI interface."""
    parser = ArgumentParser(
        description='Make authenticated requests with Incapsula cookies'
    )
    parser.add_argument('url', help='Target URL')
    parser.add_argument('visid', help='visid_incap_* cookie value')
    parser.add_argument('incap_ses', help='incap_ses_* cookie value')
    parser.add_argument('--path', default='/', help='URL path (default: /)')
    parser.add_argument('--method', default='GET', help='HTTP method (GET, POST, etc.)')
    parser.add_argument('--output', help='Save response to file')
    parser.add_argument('--json-output', help='Save result metadata to JSON')
    
    args = parser.parse_args()
    
    print("="*80)
    print("AUTHENTICATED REQUEST WITH INCAPSULA COOKIES")
    print("="*80 + "\n")
    
    # Create session
    auth = AuthenticatedRequests(args.url, args.visid, args.incap_ses)
    
    # Make request
    result = auth.request(args.method, args.path)
    
    # Save output if requested
    if args.output and result.get('content'):
        with open(args.output, 'w') as f:
            f.write(result['content'])
        print(f"\n✓ Content saved to: {args.output}")
    
    if args.json_output:
        # Remove large content from JSON
        json_result = {k: v for k, v in result.items() if k != 'content'}
        with open(args.json_output, 'w') as f:
            json.dump(json_result, f, indent=2, default=str)
        print(f"✓ Metadata saved to: {args.json_output}")
    
    print("\n" + "="*80)
    
    return 0 if result['success'] else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
