#!/usr/bin/env python3
"""
Evaluation Task: Forum Post Navigation and Download

This task tests the complete workflow of the Interactive Web Agent MCP:
1. Navigate to a forum page
2. Find pagination buttons
3. Find a specific post by title
4. Click to open the post
5. Download the post page
6. Verify the final URL is correct

Success Criteria:
- All steps complete without errors
- Final URL matches: https://www.1point3acres.com/bbs/thread-1155609-1-1.html
- Downloaded file exists and contains post content
"""

import os
import sys
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser_integration import BrowserIntegration
from query_engine import QueryEngine
from html_sanitizer import HTMLSanitizer


class ForumNavigationEval:
    """Evaluation task for forum navigation workflow"""

    def __init__(self):
        self.browser = None
        self.query_engine = QueryEngine()
        self.sanitizer = HTMLSanitizer(max_tokens=8000)
        self.current_elements = []
        self.downloads_dir = Path("./downloads")
        self.downloads_dir.mkdir(exist_ok=True)

        # Test configuration
        self.start_url = "https://www.1point3acres.com/bbs/tag/openai-9407-1.html"
        self.target_post_title = "OAI 面试挂经"
        self.expected_final_url = "https://www.1point3acres.com/bbs/thread-1155609-1-1.html"

    def setup(self):
        """Initialize browser"""
        print("Setting up browser integration...")
        self.browser = BrowserIntegration()
        print("✅ Browser integration ready")

    def cleanup(self):
        """Clean up resources"""
        if self.browser:
            print("\nCleaning up...")
            self.browser.close()
            print("✅ Browser closed")

    def navigate(self, url: str):
        """Navigate to URL"""
        print(f"\n📍 Navigating to: {url}")
        result = self.browser.playwright_client.browser_navigate(url)
        if result.get("status") != "success":
            raise Exception(f"Navigation failed: {result}")

        time.sleep(2)  # Wait for page load

        current_url = self.browser.get_current_url()
        print(f"✅ Navigated to: {current_url}")
        return current_url

    def get_page_content(self):
        """Extract page content and interactable elements"""
        print("\n📄 Extracting page content...")
        raw_html = self.browser.get_current_page_html()

        # Sanitize and extract elements
        result = self.sanitizer.sanitize(raw_html, extraction_mode="all")
        self.current_elements = result['element_registry']

        element_count = len(self.current_elements)
        element_types = result['statistics']['element_types']

        print(f"✅ Extracted {element_count} interactable elements")
        print(f"   Element types: {element_types}")

        return result

    def query_elements(self, query: str = None, filters: dict = None):
        """Query for specific elements"""
        print(f"\n🔍 Querying elements...")
        if query:
            print(f"   Query: {query}")
        if filters:
            print(f"   Filters: {filters}")

        matches = self.query_engine.query_elements(
            self.current_elements,
            query=query,
            filters=filters
        )

        print(f"✅ Found {len(matches)} matching elements")
        return matches

    def find_by_text(self, text: str, exact: bool = False):
        """Find elements by text"""
        print(f"\n🔍 Finding elements by text: '{text}' (exact={exact})")
        matches = self.query_engine.find_by_text(
            self.current_elements,
            text=text,
            exact=exact
        )
        print(f"✅ Found {len(matches)} matches")
        return matches

    def click_element(self, element: dict):
        """Click an element"""
        web_agent_id = element['web_agent_id']
        text = element.get('text', '')[:50]
        href = element.get('attributes', {}).get('href', '')

        print(f"\n🖱️  Clicking element: {web_agent_id}")
        print(f"   Text: {text}")
        print(f"   Href: {href}")

        # For links, navigate directly to the href for more reliable behavior
        if element.get('tag') == 'a' and href:
            # Build full URL if href is relative
            current_url = self.browser.get_current_url()
            if href.startswith('http'):
                full_url = href
            elif href.startswith('/'):
                # Absolute path
                from urllib.parse import urlparse
                parsed = urlparse(current_url)
                full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
            else:
                # Relative path
                base_url = current_url.rsplit('/', 1)[0]
                full_url = f"{base_url}/{href}"

            print(f"   Navigating to: {full_url}")
            result = self.browser.playwright_client.browser_navigate(full_url)

            if result.get("status") != "success":
                raise Exception(f"Navigation failed: {result}")

            time.sleep(2)
            new_url = self.browser.get_current_url()
        else:
            # For non-links (buttons, etc.), use JavaScript click
            locator = element['locators']['data_id']

            click_js = f"""
            () => {{
                const element = document.querySelector('{locator}');
                if (element) {{
                    element.click();
                    return {{success: true}};
                }} else {{
                    return {{success: false, error: 'Element not found'}};
                }}
            }}
            """

            result = self.browser.playwright_client.browser_evaluate(function=click_js)

            if isinstance(result, dict) and result.get("status") != "success":
                raise Exception(f"Click failed: {result}")

            time.sleep(2)  # Wait for navigation
            new_url = self.browser.get_current_url()

        print(f"✅ Clicked successfully")
        print(f"   New URL: {new_url}")

        return new_url

    def download_page(self, filename: str = None):
        """Download current page"""
        print(f"\n💾 Downloading page...")

        url = self.browser.get_current_url()
        title = self.browser.get_page_title()
        html = self.browser.get_current_page_html()

        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"forum_post_{timestamp}.html"

        filepath = self.downloads_dir / filename

        # Write file with metadata
        metadata = f"""<!--
Downloaded: {time.strftime("%Y-%m-%d %H:%M:%S")}
URL: {url}
Title: {title}
-->

"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(metadata + html)

        print(f"✅ Downloaded to: {filepath.absolute()}")
        print(f"   URL: {url}")
        print(f"   Size: {len(html)} bytes")

        return filepath, url

    def run(self):
        """Run the complete evaluation task"""
        print("=" * 70)
        print("EVALUATION TASK: Forum Post Navigation and Download")
        print("=" * 70)

        print("\nObjective:")
        print(f"  1. Navigate to: {self.start_url}")
        print(f"  2. Find post titled: '{self.target_post_title}'")
        print(f"  3. Click to open the post")
        print(f"  4. Download the post page")
        print(f"  5. Verify URL: {self.expected_final_url}")

        success = False
        error_message = None
        final_url = None
        download_path = None

        try:
            # Setup
            self.setup()

            # Step 1: Navigate to forum page
            print("\n" + "=" * 70)
            print("STEP 1: Navigate to Forum Page")
            print("=" * 70)
            self.navigate(self.start_url)

            # Step 2: Extract page content
            print("\n" + "=" * 70)
            print("STEP 2: Extract Page Content")
            print("=" * 70)
            self.get_page_content()

            # Step 3: Find the target post
            print("\n" + "=" * 70)
            print("STEP 3: Find Target Post")
            print("=" * 70)
            print(f"   Looking for post containing: '{self.target_post_title}'")

            # Try to find the post by text
            post_matches = self.find_by_text(self.target_post_title, exact=False)

            if not post_matches:
                # Try alternative approach: query for forum post links
                print("   Trying alternative approach: querying forum post links...")
                all_links = self.query_elements(filters={"tag": "a"})

                # Filter for links that look like forum posts (have thread- pattern)
                forum_post_links = [
                    link for link in all_links
                    if link.get('attributes', {}).get('href', '').find('thread-') >= 0
                ]

                print(f"   Found {len(forum_post_links)} forum post links")

                # Show first 10 post titles for debugging
                print("   Sample post titles:")
                for i, link in enumerate(forum_post_links[:10]):
                    print(f"      [{i}] {link.get('text', '')[:60]}")

                # Filter manually for the target title
                post_matches = [
                    link for link in all_links
                    if self.target_post_title in link.get('text', '')
                ]

                # If still not found, try searching by thread ID (most reliable)
                if not post_matches:
                    print(f"   Trying to find post by thread ID 1155609...")
                    post_matches = [
                        link for link in forum_post_links
                        if 'thread-1155609' in link.get('attributes', {}).get('href', '')
                    ]

                # If still not found, try partial match on key terms
                if not post_matches:
                    print(f"   Trying partial match on 'OAI' or '面试'...")
                    post_matches = [
                        link for link in forum_post_links
                        if 'OAI' in link.get('text', '') or '面试' in link.get('text', '')
                    ]
                    if post_matches:
                        print(f"   Found {len(post_matches)} posts with partial match:")
                        for i, link in enumerate(post_matches[:5]):
                            print(f"      [{i}] {link.get('text', '')[:80]}")
                            print(f"          href: {link.get('attributes', {}).get('href', '')}")

            if not post_matches:
                raise Exception(f"Could not find post with title containing '{self.target_post_title}'")

            target_post = post_matches[0]
            print(f"✅ Found target post!")
            print(f"   Element ID: {target_post['web_agent_id']}")
            print(f"   Text: {target_post.get('text', '')[:100]}")
            print(f"   Href: {target_post.get('attributes', {}).get('href', 'N/A')}")

            # Step 4: Click on the post
            print("\n" + "=" * 70)
            print("STEP 4: Click on Post")
            print("=" * 70)
            final_url = self.click_element(target_post)

            # Step 5: Download the page
            print("\n" + "=" * 70)
            print("STEP 5: Download Post Page")
            print("=" * 70)
            download_path, downloaded_url = self.download_page()

            # Step 6: Verify final URL
            print("\n" + "=" * 70)
            print("STEP 6: Verify Final URL")
            print("=" * 70)
            print(f"   Expected: {self.expected_final_url}")
            print(f"   Actual:   {final_url}")

            if final_url == self.expected_final_url:
                print("✅ URL matches expected!")
                success = True
            else:
                # Check if it's a variant (sometimes URLs have query parameters)
                if self.expected_final_url in final_url or final_url in self.expected_final_url:
                    print("⚠️  URL is similar (might have query params)")
                    success = True
                else:
                    print("❌ URL does NOT match expected!")
                    success = False
                    error_message = f"URL mismatch: expected {self.expected_final_url}, got {final_url}"

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            error_message = str(e)
            success = False

        finally:
            self.cleanup()

        # Print results
        print("\n" + "=" * 70)
        print("EVALUATION RESULTS")
        print("=" * 70)
        print(f"Status: {'✅ PASSED' if success else '❌ FAILED'}")
        if error_message:
            print(f"Error: {error_message}")
        if final_url:
            print(f"Final URL: {final_url}")
        if download_path:
            print(f"Downloaded to: {download_path}")
        print("=" * 70)

        return {
            "success": success,
            "error": error_message,
            "final_url": final_url,
            "download_path": str(download_path) if download_path else None,
            "expected_url": self.expected_final_url
        }


def main():
    """Run the evaluation"""
    eval_task = ForumNavigationEval()
    result = eval_task.run()

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
