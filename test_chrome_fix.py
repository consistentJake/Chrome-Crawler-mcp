#!/usr/bin/env python3
"""Test script to verify ChromeMcpClient initialization fix"""

import sys
sys.path.insert(0, '/Users/zhenkai/Documents/personal/Projects/WebAgent')

from src.browser_integration import BrowserIntegration

print("Testing BrowserIntegration with Chrome client...")
print("=" * 60)

try:
    # Test with no parameters (should use defaults)
    print("\n1. Testing BrowserIntegration(client_type='chrome')...")
    browser = BrowserIntegration(client_type='chrome')
    print("   ✅ SUCCESS: Browser integration created")
    print(f"   Client type: {browser.client_type}")
    print(f"   MCP server path: {browser.playwright_client.mcp_server_path}")

    # Close the browser
    browser.close()
    print("   ✅ Browser closed successfully")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
