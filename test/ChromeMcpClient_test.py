#!/usr/bin/env python3
"""
Navigate to 1point3acres, test all 4 content extraction methods
"""

import json
import os
import sys
import time
from datetime import datetime

sys.path.append('/Users/zhenkai/Documents/personal/Projects/WebAgent/helper')
from ChromeMcpClient import MCPChromeClient

def main():
    # Get current timestamp for folder naming
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Create test run folder
    base_downloads_folder = "/Users/zhenkai/Documents/personal/Projects/WebAgent/downloads"
    test_run_folder = os.path.join(base_downloads_folder, timestamp)
    os.makedirs(test_run_folder, exist_ok=True)
    print(f"Test run folder created: {test_run_folder}\n")

    def save_content_to_file(content, filename):
        """Save content to a file in the test run folder"""
        filepath = os.path.join(test_run_folder, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Content saved to: {filepath}")
        return filepath

    # Initialize Chrome MCP Client
    client = MCPChromeClient()

    try:
        # Navigate to the 1point3acres page
        print("Navigating to 1point3acres OpenAI tag page...")
        result = client.chrome_navigate("https://www.1point3acres.com/bbs/tag/openai-9407-1.html")
        print(f"Navigation result: {result}")

        # Wait for page to load
        time.sleep(3)

        # Test 1: Get text content
        print("\n=== Test 1: Getting text content ===")
        text_result = client.get_text_content()
        if text_result.get("status") == "success":
            # Extract the text content from the nested response
            result_data = text_result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data["content"]
                if isinstance(content_list, list) and len(content_list) > 0:
                    # First parse: get outer wrapper
                    outer_data = json.loads(content_list[0].get("text", "{}"))
                    # Second parse: get actual content
                    inner_text = outer_data.get("data", {}).get("content", [{}])[0].get("text", "{}")
                    inner_data = json.loads(inner_text)
                    text_content = inner_data.get("textContent", "")
                    save_content_to_file(text_content, "1point3acres_text.txt")
                    print(f"Text content preview: {text_content[:200]}...")
        else:
            print(f"Failed to get text content: {text_result.get('message')}")

        # Test 2: Get HTML content
        print("\n=== Test 2: Getting HTML content ===")
        html_result = client.get_html_content()
        if html_result.get("status") == "success":
            # Extract the HTML content from the nested response
            result_data = html_result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data["content"]
                if isinstance(content_list, list) and len(content_list) > 0:
                    # First parse: get outer wrapper
                    outer_data = json.loads(content_list[0].get("text", "{}"))
                    # Second parse: get actual content
                    inner_text = outer_data.get("data", {}).get("content", [{}])[0].get("text", "{}")
                    inner_data = json.loads(inner_text)
                    html_content = inner_data.get("htmlContent", "")
                    save_content_to_file(html_content, "1point3acres_html.html")
                    print(f"HTML content preview: {html_content[:200]}...")
        else:
            print(f"Failed to get HTML content: {html_result.get('message')}")

        # Test 3: Get content by selector (get all post titles)
        print("\n=== Test 3: Getting content by CSS selector (post titles) ===")
        # Try to find post title elements - common selectors for forum posts
        selectors_to_try = [
            "a[href*='thread']",  # Links containing 'thread'
            ".thread_title",      # Class thread_title
            "h3 a",               # Links inside h3 tags
            ".title a",           # Links inside title class
            "tbody tr td a"       # Links in table rows
        ]

        selector_content = ""
        for selector in selectors_to_try:
            print(f"Trying selector: {selector}")
            try:
                selector_result = client.get_selector_content(selector=selector, html=False)
                if selector_result.get("status") == "success":
                    result_data = selector_result.get("result", {})
                    if isinstance(result_data, dict) and "content" in result_data:
                        content_list = result_data["content"]
                        if isinstance(content_list, list) and len(content_list) > 0:
                            # First parse: get outer wrapper
                            outer_data = json.loads(content_list[0].get("text", "{}"))
                            # Second parse: get actual content
                            inner_text = outer_data.get("data", {}).get("content", [{}])[0].get("text", "{}")
                            if inner_text:  # Check if inner_text is not empty
                                inner_data = json.loads(inner_text)
                                selector_text = inner_data.get("textContent", "")
                                if selector_text and len(selector_text.strip()) > 0:
                                    selector_content += f"\n=== Selector: {selector} ===\n{selector_text}\n"
                                    print(f"Found content with selector '{selector}': {selector_text[:100]}...")
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                print(f"Error parsing result for selector '{selector}': {e}")

        if selector_content:
            save_content_to_file(selector_content, "1point3acres_selector.txt")
        else:
            print("No content found with any of the tried selectors")

        # Test 4: Get content by JavaScript injection
        print("\n=== Test 4: Getting content by JavaScript injection ===")
        # Custom script to extract post links and titles
        script = """
        (function() {
            var posts = [];

            // Try multiple selectors to find posts
            var selectors = [
                'a[href*="thread"]',
                'a[href*="forum"]',
                '.thread_title',
                'h3 a',
                '.title a'
            ];

            for (var i = 0; i < selectors.length; i++) {
                var elements = document.querySelectorAll(selectors[i]);
                if (elements.length > 0) {
                    for (var j = 0; j < elements.length; j++) {
                        var el = elements[j];
                        var text = el.textContent || el.innerText || '';
                        var href = el.href || '';
                        if (text.trim().length > 0) {
                            posts.push({
                                title: text.trim(),
                                url: href,
                                selector: selectors[i]
                            });
                        }
                    }
                    if (posts.length > 0) break;
                }
            }

            // Also get page title and URL
            return {
                pageTitle: document.title,
                pageUrl: window.location.href,
                postsFound: posts.length,
                posts: posts.slice(0, 10) // Return first 10 posts
            };
        })()
        """

        script_result = client.get_content_by_script(script=script)
        if script_result.get("status") == "success":
            script_data = script_result.get("result", {}).get("scriptResult", "")
            try:
                # Parse the JSON result
                parsed_result = json.loads(script_data)
                formatted_result = json.dumps(parsed_result, indent=2, ensure_ascii=False)
                save_content_to_file(formatted_result, "1point3acres_script.json")
                print(f"JavaScript extraction found {parsed_result.get('postsFound', 0)} posts")
                print(f"Page title: {parsed_result.get('pageTitle', 'N/A')}")
                print(f"First few posts: {json.dumps(parsed_result.get('posts', [])[:3], indent=2)}")
            except json.JSONDecodeError:
                # If not JSON, save as text
                save_content_to_file(script_data, "1point3acres_script.txt")
                print(f"Script result (non-JSON): {script_data[:200]}...")
        else:
            print(f"Failed to get content by script: {script_result.get('message')}")

        # Take a screenshot for reference
        print("\nTaking screenshot...")
        screenshot = client.chrome_screenshot("1point3acres_screenshot")
        print(f"Screenshot saved: {screenshot}")

        print(f"\n=== All tests completed! Results saved to {test_run_folder} ===")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()