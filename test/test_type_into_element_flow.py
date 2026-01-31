#!/usr/bin/env python3
"""
Test script to verify the full type_into_element flow through BrowserIntegration.
Tests both direct ChromeMcpClient and the BrowserIntegration wrapper.
"""

import sys
import os
import time
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

from helper.ChromeMcpClient import MCPChromeClient
from browser_integration import BrowserIntegration


def test_direct_chrome_client():
    """Test type_into_element directly via ChromeMcpClient"""
    print("\n" + "=" * 60)
    print("TEST 1: Direct ChromeMcpClient.type_into_element")
    print("=" * 60)

    mcp_command = [
        "npx", "node",
        "/home/zhenkai/personal/Projects/UnifiedReader/mcp-chrome/app/native-server/dist/mcp/mcp-server-stdio.js"
    ]

    client = MCPChromeClient(
        mcp_server_path="/home/zhenkai/personal/Projects/UnifiedReader/mcp-chrome/app/native-server/dist/mcp/mcp-server-stdio.js",
        mcp_command=mcp_command
    )

    try:
        # Navigate to Google
        print("\n1. Navigating to google.com...")
        nav_result = client.chrome_navigate(url="https://www.google.com")
        print(f"   Navigation: {nav_result.get('status')}")
        time.sleep(2)

        # Type using standard selector
        print("\n2. Typing 'direct_test' using standard selector...")
        selector = 'textarea[name="q"], input[name="q"]'
        type_result = client.type_into_element(
            selector=selector,
            text="direct_test",
            clear_first=True
        )
        print(f"   Type result status: {type_result.get('status')}")

        # Parse the nested result to get actual value
        if type_result.get("status") == "success":
            result_data = type_result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content = result_data.get("content", [])
                if content:
                    inner_text = content[0].get("text", "{}")
                    inner_data = json.loads(inner_text)
                    element_info = inner_data.get("elementInfo", {})
                    actual_value = element_info.get("value", "N/A")
                    print(f"   ✓ Actual value in input: '{actual_value}'")

                    if actual_value == "direct_test":
                        print("   ✅ TEST PASSED: Direct ChromeMcpClient works!")
                    else:
                        print(f"   ❌ TEST FAILED: Expected 'direct_test', got '{actual_value}'")
        else:
            print(f"   ❌ TEST FAILED: {type_result}")

    finally:
        client.close()


def test_browser_integration():
    """Test type_into_element via BrowserIntegration"""
    print("\n" + "=" * 60)
    print("TEST 2: BrowserIntegration.type_into_element")
    print("=" * 60)

    browser = BrowserIntegration(client_type="chrome")

    try:
        # Navigate to Google
        print("\n1. Navigating to google.com...")
        nav_result = browser.playwright_client.browser_navigate("https://www.google.com")
        print(f"   Navigation: {nav_result.get('status')}")
        time.sleep(2)

        # First, inject a data-web-agent-id attribute manually for testing
        print("\n2. Injecting data-web-agent-id attribute...")
        inject_script = """
        (function() {
            var el = document.querySelector('textarea[name="q"], input[name="q"]');
            if (el) {
                el.setAttribute('data-web-agent-id', 'wa-test');
                return {success: true, found: true};
            }
            return {success: false, found: false};
        })()
        """
        inject_result = browser.playwright_client.chrome_inject_script(
            js_script=inject_script,
            script_type="MAIN"
        )
        print(f"   Injection: {inject_result.get('status')}")
        time.sleep(0.5)

        # Type using data-web-agent-id selector (simulating interactive-web-agent flow)
        print("\n3. Typing 'browser_integration_test' using [data-web-agent-id] selector...")
        selector = '[data-web-agent-id="wa-test"]'
        type_result = browser.type_into_element(
            css_selector=selector,
            text="browser_integration_test"
        )
        print(f"   Type result status: {type_result.get('status')}")

        # Verify using direct chrome_fill_or_select to read value
        print("\n4. Verifying actual value in input...")
        verify_result = browser.playwright_client.chrome_fill_or_select(
            selector=selector,
            value="verify_value"
        )

        if verify_result.get("status") == "success":
            result_data = verify_result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content = result_data.get("content", [])
                if content:
                    inner_text = content[0].get("text", "{}")
                    inner_data = json.loads(inner_text)
                    element_info = inner_data.get("elementInfo", {})
                    # Note: This shows the NEW value after our verify call, not the previous value
                    print(f"   (After verification call, value is now: '{element_info.get('value', 'N/A')}')")

        if type_result.get("status") == "success":
            print("   ✅ TEST PASSED: BrowserIntegration.type_into_element works!")
        else:
            print(f"   ❌ TEST FAILED: {type_result}")

    finally:
        browser.close()


def test_with_response_parsing():
    """Test and analyze the response structure"""
    print("\n" + "=" * 60)
    print("TEST 3: Response Structure Analysis")
    print("=" * 60)

    mcp_command = [
        "npx", "node",
        "/home/zhenkai/personal/Projects/UnifiedReader/mcp-chrome/app/native-server/dist/mcp/mcp-server-stdio.js"
    ]

    client = MCPChromeClient(
        mcp_server_path="/home/zhenkai/personal/Projects/UnifiedReader/mcp-chrome/app/native-server/dist/mcp/mcp-server-stdio.js",
        mcp_command=mcp_command
    )

    try:
        # Navigate
        client.chrome_navigate(url="https://www.google.com")
        time.sleep(2)

        # Type and capture full response
        print("\n1. Calling type_into_element and analyzing response...")
        selector = 'textarea[name="q"]'
        result = client.type_into_element(
            selector=selector,
            text="response_test",
            clear_first=True
        )

        print("\n   Full response structure:")
        print(f"   {json.dumps(result, indent=4, default=str)[:1000]}...")

        print("\n2. Key fields:")
        print(f"   - status: {result.get('status')}")
        print(f"   - has 'result' key: {'result' in result}")
        print(f"   - has 'error' key: {'error' in result}")
        print(f"   - has 'message' key: {'message' in result}")

        # Check the nested structure
        if "result" in result:
            result_inner = result["result"]
            print(f"\n3. Inner 'result' structure:")
            print(f"   - type: {type(result_inner)}")
            if isinstance(result_inner, dict):
                print(f"   - keys: {list(result_inner.keys())}")
                if "content" in result_inner:
                    content = result_inner["content"]
                    print(f"   - content type: {type(content)}")
                    if isinstance(content, list) and content:
                        print(f"   - content[0] keys: {list(content[0].keys()) if isinstance(content[0], dict) else 'N/A'}")

    finally:
        client.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Type Into Element - Full Flow Test Suite")
    print("=" * 60)

    test_direct_chrome_client()
    test_browser_integration()
    test_with_response_parsing()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
