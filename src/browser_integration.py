"""
Browser Integration for Web Extraction MCP
Interfaces with Playwright MCP to extract page content
"""

import json
import re
from typing import Dict, Optional
from helper.PlaywrightMcpClient import MCPPlaywrightClient


class BrowserIntegration:
    """Integration with Playwright MCP for HTML extraction"""

    def __init__(
        self,
        mcp_server_path: Optional[str] = None,
        mcp_command: Optional[list] = None,
        extension_token: Optional[str] = None
    ):
        """
        Initialize browser integration.

        Args:
            mcp_server_path: Path to custom Playwright MCP server
            mcp_command: Full command to start MCP server
            extension_token: Extension token for Playwright MCP
        """
        self.playwright_client = MCPPlaywrightClient(
            mcp_server_path=mcp_server_path,
            mcp_command=mcp_command,
            extension_token=extension_token
        )

    def get_current_page_html(self) -> str:
        """
        Get HTML of current browser page.

        Returns:
            Full HTML content of current page
        """
        result = self.playwright_client.browser_evaluate(
            function="() => document.documentElement.outerHTML"
        )



        return str(self.handle_mcp_response(result))

    def handle_mcp_response(self, result: dict) -> str:
                # Handle MCP response format: {'status': 'success', 'result': {'content': [{'type': 'text', 'text': '...'}]}}
        if isinstance(result, dict):
            if result.get("status") != "success":
                raise RuntimeError(f"Failed to get page HTML: {result.get('message', 'Unknown error')}")

            # Extract content from nested structure
            result_data = result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data["content"]
                if isinstance(content_list, list) and len(content_list) > 0:
                    first_item = content_list[0]
                    if isinstance(first_item, dict) and "text" in first_item:
                        text = first_item["text"]
                        # Parse the result from markdown format - HTML is quoted and escaped
                        # Look for content after "### Result" - HTML might span multiple lines
                        match = re.search(r'### Result\s*\n"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
                        if match:
                            # Unescape the string
                            html = match.group(1)
                            html = html.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
                            return html
                        # If no match, return the text as-is
                        return text

            # Fallback: try old format
            content = result.get("result", "")
            if isinstance(content, str):
                return content
            if isinstance(content, dict):
                if "content" in content:
                    return str(content["content"])
                elif "result" in content:
                    return str(content["result"])
        return str(result)

    def get_current_url(self) -> str:
        """
        Get current page URL.

        Returns:
            Current page URL
        """
        result = self.playwright_client.browser_evaluate(
            function="() => window.location.href"
        )

        # Handle MCP response format: {'status': 'success', 'result': {'content': [{'type': 'text', 'text': '...'}]}}
        if isinstance(result, dict):
            if result.get("status") != "success":
                raise RuntimeError(f"Failed to get page URL: {result.get('message', 'Unknown error')}")

            # Extract content from nested structure
            result_data = result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data["content"]
                if isinstance(content_list, list) and len(content_list) > 0:
                    first_item = content_list[0]
                    if isinstance(first_item, dict) and "text" in first_item:
                        text = first_item["text"]
                        # Parse the result from markdown format
                        # Look for the URL in quotes after "### Result"
                        match = re.search(r'### Result\s*\n"([^"]+)"', text)
                        if match:
                            return match.group(1)
                        # If no match, return the text as-is
                        return text

            # Fallback: try old format
            content = result.get("result", "")
            if isinstance(content, str):
                return content
            if isinstance(content, dict):
                if "content" in content:
                    return str(content["content"])
                elif "result" in content:
                    return str(content["result"])

        return str(result)

    def get_page_title(self) -> str:
        """
        Get current page title.

        Returns:
            Page title
        """
        result = self.playwright_client.browser_evaluate(
            function="() => document.title"
        )

        # Handle MCP response format: {'status': 'success', 'result': {'content': [{'type': 'text', 'text': '...'}]}}
        if isinstance(result, dict):
            if result.get("status") != "success":
                return ""

            # Extract content from nested structure
            result_data = result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data["content"]
                if isinstance(content_list, list) and len(content_list) > 0:
                    first_item = content_list[0]
                    if isinstance(first_item, dict) and "text" in first_item:
                        text = first_item["text"]
                        # Parse the result from markdown format
                        # Look for the title in quotes after "### Result"
                        match = re.search(r'### Result\s*\n"([^"]*)"', text)
                        if match:
                            return match.group(1)
                        # If no match, return the text as-is
                        return text

            # Fallback: try old format
            content = result.get("result", "")
            if isinstance(content, str):
                return content
            if isinstance(content, dict):
                if "content" in content:
                    return str(content["content"])
                elif "result" in content:
                    return str(content["result"])

        return str(result)

    def get_page_metadata(self) -> Dict[str, str]:
        """
        Get page metadata (title, URL, viewport size).

        Returns:
            Dictionary with page metadata
        """
        # Get multiple pieces of metadata in one call
        result = self.playwright_client.browser_evaluate(
            function="""() => {
                return {
                    url: window.location.href,
                    title: document.title,
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight
                    },
                    scrollPosition: {
                        x: window.scrollX,
                        y: window.scrollY
                    },
                    documentSize: {
                        width: document.documentElement.scrollWidth,
                        height: document.documentElement.scrollHeight
                    }
                };
            }"""
        )

        # Handle MCP response format: {'status': 'success', 'result': {'content': [{'type': 'text', 'text': '...'}]}}
        if isinstance(result, dict):
            if result.get("status") != "success":
                return {
                    "url": self.get_current_url(),
                    "title": self.get_page_title()
                }

            # Extract content from nested structure
            result_data = result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data["content"]
                if isinstance(content_list, list) and len(content_list) > 0:
                    first_item = content_list[0]
                    if isinstance(first_item, dict) and "text" in first_item:
                        text = first_item["text"]
                        # Parse the result from markdown format - extract JSON object
                        # Look for JSON object after "### Result" (may be nested)
                        match = re.search(r'### Result\s*\n(\{.*?\n\})', text, re.DOTALL)
                        if match:
                            try:
                                return json.loads(match.group(1))
                            except Exception as e:
                                print(f"DEBUG: Failed to parse JSON metadata: {e}")
                                pass
                        # If no match, return fallback
                        return {
                            "url": self.get_current_url(),
                            "title": self.get_page_title()
                        }

            # Fallback: try old format
            content = result.get("result", {})
            if isinstance(content, dict):
                if "content" in content:
                    if isinstance(content["content"], str):
                        try:
                            return json.loads(content["content"])
                        except:
                            pass
                    return content["content"]
                elif "result" in content:
                    if isinstance(content["result"], str):
                        try:
                            return json.loads(content["result"])
                        except:
                            pass
                    return content["result"]

        return {
            "url": self.get_current_url(),
            "title": self.get_page_title()
        }

    def scroll_to_bottom(self) -> bool:
        """
        Scroll to the bottom of the page.

        Returns:
            True if successful
        """
        result = self.playwright_client.browser_evaluate(
            function="() => { window.scrollTo(0, document.documentElement.scrollHeight); }"
        )
        return result.get("status") == "success"

    def wait_for_page_load(self, timeout: float = 5.0) -> bool:
        """
        Wait for page to finish loading.

        Args:
            timeout: Timeout in seconds

        Returns:
            True if successful
        """
        result = self.playwright_client.browser_wait_for(time_seconds=timeout)
        return result.get("status") == "success"

    def take_screenshot(self, filename: str, full_page: bool = False) -> bool:
        """
        Take screenshot of current page.

        Args:
            filename: Path to save screenshot
            full_page: Whether to capture full page

        Returns:
            True if successful
        """
        result = self.playwright_client.browser_take_screenshot(
            filename=filename,
            full_page=full_page
        )
        return result.get("status") == "success"

    def close(self):
        """Close the Playwright MCP client"""
        self.playwright_client.close()


if __name__ == "__main__":
    # Test browser integration
    print("Testing Browser Integration...")

    try:
        # Initialize browser integration
        browser = BrowserIntegration()
        print("✅ Browser integration initialized")

        # Navigate to test page
        print("\nNavigating to example.com...")
        result = browser.playwright_client.browser_navigate("https://example.com")
        print(f"Navigation result: {result.get('status')}")

        # Wait for page load
        browser.wait_for_page_load(2.0)

        # Get page metadata
        print("\nGetting page metadata...")
        metadata = browser.get_page_metadata()
        print(f"URL: {metadata.get('url', 'N/A')}")
        print(f"Title: {metadata.get('title', 'N/A')}")

        # Get page HTML
        print("\nGetting page HTML...")
        html = browser.get_current_page_html()
        print(f"HTML length: {len(html)} characters")
        print(f"HTML preview: {html[:200]}...")

        # Close browser
        browser.close()
        print("\n✅ Browser integration test passed!")

    except Exception as e:
        print(f"\n❌ Browser integration test failed: {e}")
        import traceback
        traceback.print_exc()
