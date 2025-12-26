"""
Browser Integration for Web Extraction MCP
Interfaces with Playwright MCP to extract page content
"""

import json
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

        if result.get("status") != "success":
            raise RuntimeError(f"Failed to get page HTML: {result.get('message', 'Unknown error')}")

        # Extract content from nested result structure
        content = result.get("result", "")

        # Handle list response (sometimes MCP returns list)
        if isinstance(content, list):
            if len(content) > 0:
                content = content[0]
            else:
                return ""

        if isinstance(content, dict):
            # Handle different response formats
            if "content" in content:
                return content["content"]
            elif "result" in content:
                return content["result"]
            # Sometimes the HTML is directly in the result
            return str(content)

        # Handle string or other types
        if isinstance(content, str):
            return content

        return str(content)

    def get_current_url(self) -> str:
        """
        Get current page URL.

        Returns:
            Current page URL
        """
        result = self.playwright_client.browser_evaluate(
            function="() => window.location.href"
        )

        if result.get("status") != "success":
            raise RuntimeError(f"Failed to get page URL: {result.get('message', 'Unknown error')}")

        content = result.get("result", "")

        # Handle list response
        if isinstance(content, list):
            if len(content) > 0:
                content = content[0]
            else:
                return ""

        if isinstance(content, dict):
            if "content" in content:
                return content["content"]
            elif "result" in content:
                return content["result"]
            return str(content)

        if isinstance(content, str):
            return content

        return str(content)

    def get_page_title(self) -> str:
        """
        Get current page title.

        Returns:
            Page title
        """
        result = self.playwright_client.browser_evaluate(
            function="() => document.title"
        )

        if result.get("status") != "success":
            return ""

        content = result.get("result", "")

        # Handle list response
        if isinstance(content, list):
            if len(content) > 0:
                content = content[0]
            else:
                return ""

        if isinstance(content, dict):
            if "content" in content:
                return content["content"]
            elif "result" in content:
                return content["result"]
            return str(content)

        if isinstance(content, str):
            return content

        return str(content)

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

        if result.get("status") != "success":
            return {
                "url": self.get_current_url(),
                "title": self.get_page_title()
            }

        content = result.get("result", {})

        # Handle list response
        if isinstance(content, list):
            if len(content) > 0:
                content = content[0]
            else:
                return {
                    "url": self.get_current_url(),
                    "title": self.get_page_title()
                }

        if isinstance(content, dict):
            if "content" in content:
                # Parse JSON if it's a string
                if isinstance(content["content"], str):
                    try:
                        return json.loads(content["content"])
                    except:
                        return content["content"]
                return content["content"]
            elif "result" in content:
                if isinstance(content["result"], str):
                    try:
                        return json.loads(content["result"])
                    except:
                        return content["result"]
                return content["result"]

        return content if isinstance(content, dict) else {}

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
