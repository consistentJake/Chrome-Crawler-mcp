#!/usr/bin/env python3
"""
Verify click actually changes the URL
"""

import json
import os
import sys
import time
from datetime import datetime

sys.path.append('/Users/zhenkai/Documents/personal/Projects/WebAgent/helper')
from ChromeMcpClient import MCPChromeClient

def get_current_url(client):
    """Get the current page URL using chrome_get_web_content"""
    # Try method 1: Get text content which should include metadata with URL
    result = client.chrome_get_web_content(text_content=True)

    if result.get("status") == "success":
        result_data = result.get("result", {})
        content = result_data.get("content", [])
        if content:
            try:
                # Parse the nested JSON structure
                outer_data = json.loads(content[0].get("text", "{}"))

                # The URL should be in the metadata
                if "data" in outer_data:
                    data = outer_data["data"]
                    if "content" in data:
                        inner_content = data["content"]
                        if inner_content and len(inner_content) > 0:
                            inner_text = inner_content[0].get("text", "{}")
                            inner_data = json.loads(inner_text)

                            # Look for URL in metadata
                            if "metadata" in inner_data:
                                metadata = inner_data["metadata"]
                                if "url" in metadata:
                                    return metadata["url"]

                            # Also try to find it directly
                            if "url" in inner_data:
                                return inner_data["url"]
            except Exception as e:
                print(f"  Debug: Error parsing URL from content: {e}")

    # Fallback: Try to use browser_evaluate
    try:
        eval_result = client.browser_evaluate("() => window.location.href")
        if eval_result.get("status") == "success":
            content = eval_result.get("result", {}).get("content", [])
            if content:
                text = content[0].get("text", "")
                # The text might be a simple string or JSON
                try:
                    # Try parsing as JSON first
                    parsed = json.loads(text)
                    if isinstance(parsed, str):
                        return parsed
                except:
                    # If not JSON, might be the URL directly
                    if text.startswith("http"):
                        return text
    except Exception as e:
        print(f"  Debug: browser_evaluate failed: {e}")

    return None

def main():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    print(f"Test started at: {timestamp}\n")

    client = MCPChromeClient()

    try:
        # Step 1: Navigate to page 1
        print("=" * 70)
        print("STEP 1: Navigating to page 1")
        print("=" * 70)
        url_page1 = "https://www.1point3acres.com/bbs/tag-9407-1.html"
        result = client.chrome_navigate(url_page1)
        print(f"Navigation status: {result.get('status')}")
        time.sleep(3)

        # Get current URL before click
        print("\nGetting current URL BEFORE click...")
        url_before = get_current_url(client)
        print(f"URL before click: {url_before}")

        if url_before:
            if "tag-9407-1" in url_before:
                print("✓ Confirmed: We are on page 1")
            else:
                print(f"⚠ Warning: Expected page 1, but URL is: {url_before}")
        else:
            print("✗ Failed to get URL before click")

        # Step 2: Click on page 3 link
        print("\n" + "=" * 70)
        print("STEP 2: Clicking on page 3 link")
        print("=" * 70)

        page3_selector = 'a[href*="tag-9407-3.html"]'
        print(f"Using selector: {page3_selector}")

        print("\nExecuting click...")
        click_result = client.chrome_click_element(
            selector=page3_selector,
            wait_for_navigation=True,
            timeout=10000
        )

        print(f"Click status: {click_result.get('status')}")

        if click_result.get('status') != 'success':
            print(f"✗ Click failed: {click_result.get('message', 'Unknown error')}")
            return

        print("✓ Click executed successfully")

        # Wait for navigation
        print("\nWaiting for page to load...")
        time.sleep(4)

        # Step 3: Verify URL changed
        print("\n" + "=" * 70)
        print("STEP 3: Verifying URL changed to page 3")
        print("=" * 70)

        url_after = get_current_url(client)
        print(f"\nURL after click: {url_after}")

        # Expected URL
        expected_url = "https://www.1point3acres.com/bbs/tag-9407-3.html"

        # Verify
        print("\nVerification:")
        print(f"  Expected URL: {expected_url}")
        print(f"  Actual URL:   {url_after}")

        if url_after and expected_url in url_after:
            print("\n" + "=" * 70)
            print("✓✓✓ SUCCESS! URL CHANGED TO PAGE 3! ✓✓✓")
            print("=" * 70)
            print("\nClick navigation verified:")
            print(f"  Before: {url_before}")
            print(f"  After:  {url_after}")
            print("\n✓ The click successfully navigated to a different page!")
        else:
            print("\n" + "=" * 70)
            print("✗✗✗ FAILED! URL DID NOT CHANGE! ✗✗✗")
            print("=" * 70)
            print("\nClick did NOT navigate to page 3:")
            print(f"  Before: {url_before}")
            print(f"  After:  {url_after}")
            print("\n✗ The page URL did not change - click may not have worked")
            print("\nPossible reasons:")
            print("  1. Click didn't trigger navigation")
            print("  2. Page loaded too slowly")
            print("  3. JavaScript intercepted the click")
            print("  4. Element selector didn't match")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser in 3 seconds...")
        time.sleep(3)
        client.close()

if __name__ == "__main__":
    main()
