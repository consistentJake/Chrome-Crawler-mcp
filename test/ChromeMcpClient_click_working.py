#!/usr/bin/env python3
"""
Test click with better waiting and iframe handling
"""

import json
import sys
import time

sys.path.append('/Users/zhenkai/Documents/personal/Projects/WebAgent/helper')
from ChromeMcpClient import MCPChromeClient

def get_current_url(client):
    """Get current URL"""
    result = client.chrome_get_web_content(text_content=True)
    if result.get("status") == "success":
        result_data = result.get("result", {})
        content = result_data.get("content", [])
        if content:
            try:
                outer_data = json.loads(content[0].get("text", "{}"))
                if "data" in outer_data:
                    data = outer_data["data"]
                    if "content" in data:
                        inner_content = data["content"]
                        if inner_content:
                            inner_text = inner_content[0].get("text", "{}")
                            inner_data = json.loads(inner_text)
                            if "metadata" in inner_data:
                                return inner_data["metadata"].get("url")
            except:
                pass
    return None

def main():
    client = MCPChromeClient()

    try:
        print("=" * 70)
        print("STEP 1: Navigate and wait for page to fully load")
        print("=" * 70)
        client.chrome_navigate("https://www.1point3acres.com/bbs/tag-9407-1.html")

        print("Waiting 5 seconds for page to fully load...")
        time.sleep(5)

        url_before = get_current_url(client)
        print(f"URL before click: {url_before}")

        # Try clicking using the exact href we found
        print("\n" + "=" * 70)
        print("STEP 2: Try clicking with simplified selector")
        print("=" * 70)

        # Selector variations to try
        selectors = [
            'a[href="tag-9407-3.html"]',  # Exact match
            'a[href$="-9407-3.html"]',     # Ends with
            'a:contains("3")',              # By text (might not work)
        ]

        for selector in selectors:
            print(f"\nTrying selector: {selector}")

            # Check if it matches
            check_script = f"""
            var el = document.querySelector('{selector}');
            return JSON.stringify({{
                found: el !== null,
                href: el ? el.href : null,
                text: el ? el.textContent.trim() : null
            }});
            """

            check_result = client.browser_evaluate(f"() => {{ {check_script} }}")
            if check_result.get("status") == "success":
                content = check_result.get("result", {}).get("content", [])
                if content:
                    text = content[0].get("text", "{}")
                    try:
                        data = json.loads(text)
                        if data.get('found'):
                            print(f"  ✓ Found element!")
                            print(f"    Href: {data.get('href')}")
                            print(f"    Text: {data.get('text')}")

                            # Try clicking this selector
                            print(f"\n  Attempting click...")
                            click_result = client.chrome_click_element(
                                selector=selector,
                                wait_for_navigation=True,
                                timeout=10000
                            )

                            print(f"  Click status: {click_result.get('status')}")

                            if click_result.get('status') == 'success':
                                print("  Waiting for navigation...")
                                time.sleep(4)

                                url_after = get_current_url(client)
                                print(f"  URL after click: {url_after}")

                                if url_after and "tag-9407-3" in url_after:
                                    print("\n  ✓✓✓ SUCCESS! Navigated to page 3!")
                                    return
                                else:
                                    print(f"  ✗ Still on: {url_after}")
                                    # Navigate back to page 1 for next attempt
                                    client.chrome_navigate("https://www.1point3acres.com/bbs/tag-9407-1.html")
                                    time.sleep(3)
                        else:
                            print(f"  ✗ Selector didn't match any elements")
                    except Exception as e:
                        print(f"  Error: {e}")

        # Last resort: Use JavaScript to click directly
        print("\n" + "=" * 70)
        print("STEP 3: Use JavaScript to click directly")
        print("=" * 70)

        # Navigate back to page 1
        client.chrome_navigate("https://www.1point3acres.com/bbs/tag-9407-1.html")
        time.sleep(5)

        # Find and click using pure JavaScript
        js_click = """
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
            if (links[i].textContent.trim() === '3' &&
                links[i].href && links[i].href.includes('tag-9407-3')) {
                console.log('Found page 3 link:', links[i].href);
                links[i].click();
                return JSON.stringify({ clicked: true, href: links[i].href });
            }
        }
        return JSON.stringify({ clicked: false, error: 'Link not found' });
        """

        print("Attempting JavaScript click on link with text '3'...")
        js_result = client.browser_evaluate(f"() => {{ {js_click} }}")

        if js_result.get("status") == "success":
            content = js_result.get("result", {}).get("content", [])
            if content:
                text = content[0].get("text", "{}")
                try:
                    data = json.loads(text)
                    if data.get('clicked'):
                        print(f"✓ JavaScript clicked: {data.get('href')}")

                        print("Waiting for navigation...")
                        time.sleep(4)

                        url_after = get_current_url(client)
                        print(f"URL after JS click: {url_after}")

                        if url_after and "tag-9407-3" in url_after:
                            print("\n✓✓✓ JavaScript click SUCCESS!")
                        else:
                            print(f"\n✗ JavaScript click did not navigate")
                    else:
                        print(f"✗ JavaScript click failed: {data.get('error')}")
                except Exception as e:
                    print(f"Error: {e}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        client.close()

if __name__ == "__main__":
    main()
