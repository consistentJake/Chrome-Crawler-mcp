#!/usr/bin/env python3
"""
Debug version to see raw responses
"""

import json
import sys
import time

sys.path.append('/Users/zhenkai/Documents/personal/Projects/WebAgent/helper')
from ChromeMcpClient import MCPChromeClient

def main():
    client = MCPChromeClient()

    try:
        # Navigate
        print("Navigating...")
        result = client.chrome_navigate("https://www.1point3acres.com/bbs/tag/openai-9407-1.html")
        print(f"Navigation result: {json.dumps(result, indent=2)}\n")

        # Wait for page to load
        time.sleep(3)

        # Test 1: Get text content
        print("=== Test 1: Getting text content ===")
        text_result = client.get_text_content()
        print(f"Raw text result: {json.dumps(text_result, indent=2)}\n")

        # Extract and print
        if text_result.get("status") == "success":
            result_data = text_result.get("result", {})
            print(f"Result data type: {type(result_data)}")
            print(f"Result data keys: {result_data.keys() if isinstance(result_data, dict) else 'N/A'}")

            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data["content"]
                print(f"Content list length: {len(content_list)}")
                if len(content_list) > 0:
                    first_item = content_list[0]
                    print(f"First item type: {first_item.get('type')}")
                    print(f"First item text preview: {first_item.get('text', '')[:500]}...")

                    # Try to parse as JSON
                    try:
                        text_data = json.loads(first_item.get("text", "{}"))
                        print(f"Parsed JSON keys: {text_data.keys()}")
                        print(f"textContent present: {'textContent' in text_data}")
                        if 'textContent' in text_data:
                            print(f"textContent length: {len(text_data.get('textContent', ''))}")
                            print(f"textContent preview: {text_data.get('textContent', '')[:200]}...")
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse JSON: {e}")

        # Test 2: Get HTML content
        print("\n=== Test 2: Getting HTML content ===")
        html_result = client.get_html_content()
        print(f"Raw HTML result: {json.dumps(html_result, indent=2)}\n")

        if html_result.get("status") == "success":
            result_data = html_result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data["content"]
                if len(content_list) > 0:
                    first_item = content_list[0]
                    print(f"First item text preview: {first_item.get('text', '')[:500]}...")

                    try:
                        html_data = json.loads(first_item.get("text", "{}"))
                        print(f"Parsed JSON keys: {html_data.keys()}")
                        print(f"htmlContent present: {'htmlContent' in html_data}")
                        if 'htmlContent' in html_data:
                            print(f"htmlContent length: {len(html_data.get('htmlContent', ''))}")
                            print(f"htmlContent preview: {html_data.get('htmlContent', '')[:200]}...")
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse JSON: {e}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
