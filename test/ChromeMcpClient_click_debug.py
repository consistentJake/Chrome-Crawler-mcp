#!/usr/bin/env python3
"""
Debug why click is not working
"""

import json
import sys
import time

sys.path.append('/Users/zhenkai/Documents/personal/Projects/WebAgent/helper')
from ChromeMcpClient import MCPChromeClient

def main():
    client = MCPChromeClient()

    try:
        # Navigate to page 1
        print("=" * 70)
        print("STEP 1: Navigating to page 1")
        print("=" * 70)
        client.chrome_navigate("https://www.1point3acres.com/bbs/tag-9407-1.html")
        time.sleep(3)

        # Diagnostic 1: Check if selector matches any elements
        print("\n" + "=" * 70)
        print("DIAGNOSTIC 1: Check if selector matches elements")
        print("=" * 70)

        page3_selector = 'a[href*="tag-9407-3.html"]'
        print(f"Selector: {page3_selector}")

        # Use JavaScript to find matching elements
        find_script = f"""
        var elements = document.querySelectorAll('{page3_selector}');
        var results = [];
        for (var i = 0; i < Math.min(elements.length, 5); i++) {{
            var el = elements[i];
            var rect = el.getBoundingClientRect();
            results.push({{
                index: i,
                text: el.textContent.trim(),
                href: el.href,
                visible: rect.width > 0 && rect.height > 0,
                inViewport: rect.top >= 0 && rect.left >= 0 &&
                           rect.bottom <= window.innerHeight &&
                           rect.right <= window.innerWidth,
                offsetTop: el.offsetTop,
                className: el.className,
                computed: window.getComputedStyle(el).display
            }});
        }}
        return JSON.stringify({{
            count: elements.length,
            elements: results
        }});
        """

        result = client.browser_evaluate(f"() => {{ {find_script} }}")
        if result.get("status") == "success":
            content = result.get("result", {}).get("content", [])
            if content:
                text = content[0].get("text", "{}")
                try:
                    data = json.loads(text)
                    print(f"\n✓ Found {data.get('count', 0)} matching elements")

                    elements = data.get('elements', [])
                    for elem in elements:
                        print(f"\n  Element {elem['index']}:")
                        print(f"    Text: {elem['text'][:50]}")
                        print(f"    Href: {elem['href']}")
                        print(f"    Visible: {elem['visible']}")
                        print(f"    In Viewport: {elem['inViewport']}")
                        print(f"    Display: {elem['computed']}")
                except:
                    print(f"Raw result: {text}")

        # Diagnostic 2: Try clicking with JavaScript instead
        print("\n" + "=" * 70)
        print("DIAGNOSTIC 2: Try JavaScript click")
        print("=" * 70)

        js_click_script = f"""
        var element = document.querySelector('{page3_selector}');
        if (element) {{
            console.log('Element found:', element.href);
            console.log('Clicking...');
            element.click();
            return JSON.stringify({{
                clicked: true,
                href: element.href,
                text: element.textContent.trim()
            }});
        }} else {{
            return JSON.stringify({{ clicked: false, error: 'Element not found' }});
        }}
        """

        print("Attempting JavaScript click...")
        js_result = client.browser_evaluate(f"() => {{ {js_click_script} }}")

        if js_result.get("status") == "success":
            content = js_result.get("result", {}).get("content", [])
            if content:
                text = content[0].get("text", "{}")
                try:
                    data = json.loads(text)
                    print(f"JavaScript click result: {data}")

                    if data.get('clicked'):
                        print(f"✓ JavaScript click executed on: {data.get('href')}")
                        print("\nWaiting for navigation...")
                        time.sleep(4)

                        # Check URL after JS click
                        url_result = client.chrome_get_web_content(text_content=True)
                        if url_result.get("status") == "success":
                            result_data = url_result.get("result", {})
                            content = result_data.get("content", [])
                            if content:
                                outer_data = json.loads(content[0].get("text", "{}"))
                                if "data" in outer_data:
                                    data = outer_data["data"]
                                    if "content" in data:
                                        inner_content = data["content"]
                                        if inner_content:
                                            inner_text = inner_content[0].get("text", "{}")
                                            inner_data = json.loads(inner_text)
                                            if "metadata" in inner_data:
                                                url = inner_data["metadata"].get("url", "unknown")
                                                print(f"\nURL after JS click: {url}")

                                                if "tag-9407-3" in url:
                                                    print("✓✓✓ JavaScript click WORKED!")
                                                else:
                                                    print("✗ JavaScript click did NOT navigate")
                except Exception as e:
                    print(f"Error: {e}")

        # Diagnostic 3: Try native Chrome click
        print("\n" + "=" * 70)
        print("DIAGNOSTIC 3: Try native Chrome click (without waitForNavigation)")
        print("=" * 70)

        # First navigate back to page 1
        print("Navigating back to page 1...")
        client.chrome_navigate("https://www.1point3acres.com/bbs/tag-9407-1.html")
        time.sleep(3)

        print(f"Attempting native click with selector: {page3_selector}")
        click_result = client.chrome_click_element(
            selector=page3_selector,
            wait_for_navigation=False,  # Don't wait
            timeout=5000
        )

        print(f"Click status: {click_result.get('status')}")
        print("Waiting 4 seconds for navigation...")
        time.sleep(4)

        # Check URL
        url_result = client.chrome_get_web_content(text_content=True)
        if url_result.get("status") == "success":
            result_data = url_result.get("result", {})
            content = result_data.get("content", [])
            if content:
                outer_data = json.loads(content[0].get("text", "{}"))
                if "data" in outer_data:
                    data = outer_data["data"]
                    if "content" in data:
                        inner_content = data["content"]
                        if inner_content:
                            inner_text = inner_content[0].get("text", "{}")
                            inner_data = json.loads(inner_text)
                            if "metadata" in inner_data:
                                url = inner_data["metadata"].get("url", "unknown")
                                print(f"URL after native click: {url}")

                                if "tag-9407-3" in url:
                                    print("✓✓✓ Native click WORKED!")
                                else:
                                    print("✗ Native click did NOT navigate")

        # Diagnostic 4: Get page 3 link and try clicking it directly by href
        print("\n" + "=" * 70)
        print("DIAGNOSTIC 4: Try navigating directly to page 3")
        print("=" * 70)

        page3_url = "https://www.1point3acres.com/bbs/tag-9407-3.html"
        print(f"Navigating directly to: {page3_url}")
        nav_result = client.chrome_navigate(page3_url)
        print(f"Navigation status: {nav_result.get('status')}")

        time.sleep(3)

        # Verify URL
        url_result = client.chrome_get_web_content(text_content=True)
        if url_result.get("status") == "success":
            result_data = url_result.get("result", {})
            content = result_data.get("content", [])
            if content:
                outer_data = json.loads(content[0].get("text", "{}"))
                if "data" in outer_data:
                    data = outer_data["data"]
                    if "content" in data:
                        inner_content = data["content"]
                        if inner_content:
                            inner_text = inner_content[0].get("text", "{}")
                            inner_data = json.loads(inner_text)
                            if "metadata" in inner_data:
                                url = inner_data["metadata"].get("url", "unknown")
                                print(f"URL after direct navigation: {url}")

                                if "tag-9407-3" in url:
                                    print("✓ Direct navigation works!")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser in 3 seconds...")
        time.sleep(3)
        client.close()

if __name__ == "__main__":
    main()
