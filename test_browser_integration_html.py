#!/usr/bin/env python3
"""
Test browser_integration.py get_current_page_html with Chrome client
"""

import sys
import time
sys.path.append('/Users/zhenkai/Documents/personal/Projects/WebAgent')

from src.browser_integration import BrowserIntegration

def test_chrome_html():
    """Test getting HTML content with Chrome MCP client"""
    print("=== Testing Chrome MCP Client ===\n")

    try:
        # Initialize with Chrome client
        browser = BrowserIntegration(client_type="chrome")
        print("✅ Chrome browser integration initialized")

        # Navigate to a test page
        print("\nNavigating to example.com...")
        result = browser.playwright_client.chrome_navigate("https://example.com")
        print(f"Navigation status: {result.get('status')}")

        # Wait for page to load
        time.sleep(2)

        # Get HTML using the updated method
        print("\nGetting HTML content using get_current_page_html()...")
        html = browser.get_current_page_html()

        # Verify we got actual HTML
        print(f"✅ HTML retrieved successfully!")
        print(f"   - Length: {len(html)} characters")
        print(f"   - Starts with: {html[:100]}...")
        print(f"   - Contains <!DOCTYPE>: {html.startswith('<!DOCTYPE') or '<!doctype' in html.lower()[:100]}")
        print(f"   - Contains <html>: {'<html' in html[:200].lower()}")

        if len(html) > 0 and '<html' in html.lower():
            print("\n✅ Chrome HTML extraction test PASSED!")
            return True
        else:
            print("\n❌ Chrome HTML extraction test FAILED - HTML appears invalid")
            return False

    except Exception as e:
        print(f"\n❌ Chrome test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        browser.close()

if __name__ == "__main__":
    success = test_chrome_html()
    sys.exit(0 if success else 1)
