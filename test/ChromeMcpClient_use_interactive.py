#!/usr/bin/env python3
"""
Use chrome_get_interactive_elements to find and click
"""

import json
import sys
import time

sys.path.append('/Users/zhenkai/Documents/personal/Projects/WebAgent/helper')
from ChromeMcpClient import MCPChromeClient

def main():
    client = MCPChromeClient()

    try:
        print("=" * 70)
        print("Navigate to page 1")
        print("=" * 70)
        client.chrome_navigate("https://www.1point3acres.com/bbs/tag-9407-1.html")
        time.sleep(5)  # Wait longer for full page load

        print("\n" + "=" * 70)
        print("Get interactive elements with text '3'")
        print("=" * 70)

        # Find interactive elements with text "3"
        result = client.chrome_get_interactive_elements(text_query="3")

        print(f"Result status: {result.get('status')}")
        print(f"\nFull result:")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:1000])

        # Try to parse and find page 3 link
        if result.get("status") == "success":
            result_data = result.get("result", {})
            content = result_data.get("content", [])
            if content:
                text = content[0].get("text", "{}")
                try:
                    data = json.loads(text)
                    # Navigate through nested structure
                    if "data" in data:
                        inner_data = data["data"]
                        if "content" in inner_data:
                            inner_content = inner_data["content"]
                            if inner_content:
                                inner_text = inner_content[0].get("text", "{}")
                                elements_data = json.loads(inner_text)

                                if "elements" in elements_data:
                                    elements = elements_data["elements"]
                                    print(f"\nFound {len(elements)} interactive elements")

                                    for i, elem in enumerate(elements[:10]):  # Show first 10
                                        print(f"\n[{i}] {elem.get('type', 'unknown')}")
                                        print(f"    Selector: {elem.get('selector', 'N/A')[:80]}")
                                        print(f"    Text: {elem.get('text', '')[:50]}")

                                        # Check if this looks like page 3
                                        text = elem.get('text', '').strip()
                                        selector = elem.get('selector', '')

                                        if text == '3' and 'tag' in selector.lower():
                                            print(f"\n    *** THIS MIGHT BE PAGE 3! ***")
                                            print(f"    Trying to click with selector: {selector}")

                                            click_result = client.chrome_click_element(
                                                selector=selector,
                                                wait_for_navigation=True,
                                                timeout=10000
                                            )

                                            print(f"    Click result: {click_result.get('status')}")

                                            if click_result.get('status') == 'success':
                                                time.sleep(4)
                                                print("\n    Checking if navigation succeeded...")
                                                # The URL check would fail due to browser_evaluate issue
                                                # but we can try getting HTML and checking content
                                                return
                except Exception as e:
                    print(f"Error parsing: {e}")
                    import traceback
                    traceback.print_exc()

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        client.close()

if __name__ == "__main__":
    main()
