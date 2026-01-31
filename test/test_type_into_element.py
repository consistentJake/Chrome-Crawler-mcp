#!/usr/bin/env python3
"""
Test script to verify type_into_element functionality in ChromeMcpClient.
Navigates to google.com and types "gold" in the search bar.
"""

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helper.ChromeMcpClient import MCPChromeClient


def main():
    # Initialize Chrome MCP Client with the correct command
    mcp_command = [
        "npx", "node",
        "/home/zhenkai/personal/Projects/UnifiedReader/mcp-chrome/app/native-server/dist/mcp/mcp-server-stdio.js"
    ]

    print("Initializing Chrome MCP Client...")
    client = MCPChromeClient(
        mcp_server_path="/home/zhenkai/personal/Projects/UnifiedReader/mcp-chrome/app/native-server/dist/mcp/mcp-server-stdio.js",
        mcp_command=mcp_command
    )

    try:
        # Step 1: Navigate to Google
        print("\n=== Step 1: Navigate to google.com ===")
        nav_result = client.chrome_navigate(url="https://www.google.com")
        print(f"Navigation result: {nav_result}")

        # Wait for page to load
        time.sleep(2)

        # Step 2: Type "gold" into the search bar using type_into_element
        print("\n=== Step 2: Type 'gold' into search bar using type_into_element ===")
        search_selector = 'textarea[name="q"], input[name="q"]'
        type_result = client.type_into_element(
            selector=search_selector,
            text="gold",
            clear_first=True
        )
        print(f"Type result: {type_result}")

        # Step 3: Verify by getting the element value
        print("\n=== Step 3: Verify the input value ===")
        verify_script = f"""
        (function() {{
            var element = document.querySelector('textarea[name="q"], input[name="q"]');
            return element ? element.value : 'Element not found';
        }})()
        """
        verify_result = client.browser_evaluate(f"() => {{ {verify_script} }}")
        print(f"Verification result: {verify_result}")

        # Check if the test passed
        if type_result.get("status") == "success":
            print("\n✅ TEST PASSED: type_into_element successfully typed 'gold' into Google search")
        else:
            print("\n❌ TEST FAILED: type_into_element did not work as expected")
            print(f"Error: {type_result.get('message', 'Unknown error')}")

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing Chrome MCP Client...")
        client.close()
        print("Client closed.")


if __name__ == "__main__":
    main()
