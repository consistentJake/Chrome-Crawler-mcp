#!/usr/bin/env python3
"""
Test script for ChromeMcpClient
Demonstrates basic usage of the Chrome MCP client
"""

import json
from helper.ChromeMcpClient import MCPChromeClient


def main():
    # Initialize the Chrome MCP client
    print("Initializing Chrome MCP client...")
    client = MCPChromeClient()

    try:
        # Test 1: Get current windows and tabs
        print("\n=== Test 1: Get Windows and Tabs ===")
        result = client.get_windows_and_tabs()
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'success':
            data = result.get('result', {})
            print(f"Response: {json.dumps(data, indent=2)}")

        # Test 2: Navigate to an existing X.com tab
        print("\n=== Test 2: Navigate to X.com ===")
        result = client.chrome_navigate(url="https://x.com/search?q=gold")
        print(f"Status: {result.get('status')}")
        print(f"Response: {json.dumps(result, indent=2)}")

        # Test 3: Get web content from current page
        print("\n=== Test 3: Get Web Content ===")
        result = client.chrome_get_web_content(text_content=True)
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'success':
            # Print first 500 characters of content
            content = str(result.get('result', ''))[:500]
            print(f"Content preview: {content}...")

        # Test 4: Take a screenshot
        print("\n=== Test 4: Take Screenshot ===")
        result = client.chrome_screenshot(
            name="test_screenshot",
            save_png=True,
            store_base64=False,
            full_page=False
        )
        print(f"Status: {result.get('status')}")
        print(f"Response: {json.dumps(result, indent=2)}")

        # Test 5: Get interactive elements
        print("\n=== Test 5: Get Interactive Elements ===")
        result = client.chrome_get_interactive_elements()
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'success':
            elements = result.get('result', {})
            print(f"Found interactive elements: {json.dumps(elements, indent=2)[:500]}...")

        # Test 6: Search browser history
        print("\n=== Test 6: Search History ===")
        result = client.chrome_history(text="x.com", max_results=5)
        print(f"Status: {result.get('status')}")
        print(f"Response: {json.dumps(result, indent=2)}")

        print("\n=== All tests completed successfully! ===")

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Close the client
        print("\nClosing Chrome MCP client...")
        client.close()


if __name__ == "__main__":
    main()
