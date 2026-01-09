"""
Browser Integration for Web Extraction MCP
Interfaces with Playwright MCP or Chrome MCP to extract page content
"""

import json
import re
from typing import Dict, Optional
from helper.PlaywrightMcpClient import MCPPlaywrightClient
from helper.ChromeMcpClient import MCPChromeClient
from util import detect_host_os


LINUX_CHROME_MCP_SERVER = "/home/zhenkai/personal/Projects/UnifiedReader/mcp-chrome/app/native-server/dist/mcp/mcp-server-stdio.js"
MACOS_CHROME_MCP_SERVER = "/Users/zhenkai/.nvm/versions/node/v22.16.0/lib/node_modules/mcp-chrome-bridge/dist/mcp/mcp-server-stdio.js"


class BrowserIntegration:
    """Integration with Playwright MCP or Chrome MCP for HTML extraction"""

    def __init__(
        self,
        client_type: str = "playwright",
        mcp_server_path: Optional[str] = None,
        mcp_command: Optional[list] = None,
        extension_token: Optional[str] = None
    ):
        """
        Initialize browser integration.

        Args:
            client_type: Type of MCP client to use ("playwright" or "chrome")
            mcp_server_path: Path to custom MCP server
            mcp_command: Full command to start MCP server
            extension_token: Extension token for Playwright MCP (ignored for Chrome)
        """
        self.client_type = client_type.lower()

        if self.client_type == "chrome":
            # Only pass parameters if they're not None to avoid overriding defaults
            chrome_params = {}
            host_os = detect_host_os()
            default_server_path = (
                MACOS_CHROME_MCP_SERVER if host_os == "macos" else LINUX_CHROME_MCP_SERVER
            )
            resolved_server_path = mcp_server_path or default_server_path
            chrome_params["mcp_server_path"] = resolved_server_path
            resolved_command = mcp_command or ["npx", "node", resolved_server_path]
            chrome_params["mcp_command"] = resolved_command
            self.playwright_client = MCPChromeClient(**chrome_params)
        elif self.client_type == "playwright":
            # Only pass parameters if they're not None to avoid overriding defaults
            playwright_params = {}
            if mcp_server_path is not None:
                playwright_params["mcp_server_path"] = mcp_server_path
            if mcp_command is not None:
                playwright_params["mcp_command"] = mcp_command
            if extension_token is not None:
                playwright_params["extension_token"] = extension_token
            self.playwright_client = MCPPlaywrightClient(**playwright_params)
        else:
            raise ValueError(f"Unknown client_type: {client_type}. Must be 'playwright' or 'chrome'")

    def get_current_page_html(self) -> str:
        """
        Get HTML of current browser page.

        Returns:
            Full HTML content of current page
        """
        if self.client_type == "chrome":
            # Use Chrome's native get_html_content method
            result = self.playwright_client.get_html_content()
            return str(self.handle_chrome_content_response(result, "htmlContent"))
        else:
            # Use Playwright's browser_evaluate method
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

    def handle_chrome_content_response(self, result: dict, content_key: str) -> str:
        """
        Handle Chrome MCP response format with nested JSON.
        Chrome MCP returns a double-nested JSON structure that needs to be parsed twice.

        Args:
            result: The result dictionary from Chrome MCP
            content_key: The key to extract from the inner JSON ("htmlContent" or "textContent")

        Returns:
            Extracted content string
        """
        if isinstance(result, dict):
            if result.get("status") != "success":
                raise RuntimeError(f"Failed to get page content: {result.get('message', 'Unknown error')}")

            # Extract content from nested structure
            # Try "result" first (Playwright MCP), then "data" (Chrome MCP)
            result_data = result.get("result") or result.get("data", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data["content"]
                if isinstance(content_list, list) and len(content_list) > 0:
                    # First parse: get outer wrapper
                    outer_data = json.loads(content_list[0].get("text", "{}"))
                    # Second parse: get actual content from nested JSON
                    inner_text = outer_data.get("data", {}).get("content", [{}])[0].get("text", "{}")
                    if inner_text:
                        inner_data = json.loads(inner_text)
                        # Extract the requested content (htmlContent or textContent)
                        content = inner_data.get(content_key, "")
                        return content

        raise RuntimeError(f"Failed to extract {content_key} from Chrome MCP response")

    def get_current_url(self) -> str:
        """
        Get current page URL.

        Returns:
            Current page URL
        """
        # For Chrome MCP, use get_windows_and_tabs to get URL
        if self.client_type == "chrome":
            result = self.playwright_client.get_windows_and_tabs()
            if result.get("status") == "success":
                import json
                # Chrome MCP has triple-nested JSON structure
                # Level 1: result.content[0].text
                result_data = result.get("result") or result.get("data", {})
                content_list = result_data.get("content", [])
                if content_list:
                    level1_text = content_list[0].get("text", "{}")
                    level1_data = json.loads(level1_text)
                    # Level 2: data.content[0].text
                    level2_data = level1_data.get("data", {})
                    level2_content = level2_data.get("content", [])
                    if level2_content:
                        level2_text = level2_content[0].get("text", "{}")
                        # Level 3: actual tabs data
                        tabs_data = json.loads(level2_text)
                        # Get active tab
                        for window in tabs_data.get("windows", []):
                            for tab in window.get("tabs", []):
                                if tab.get("active"):
                                    return tab.get("url", "")
                        # Fallback: return first tab URL
                        if tabs_data.get("windows") and tabs_data["windows"][0].get("tabs"):
                            return tabs_data["windows"][0]["tabs"][0].get("url", "")
            return ""

        # For Playwright MCP, use browser_evaluate
        result = self.playwright_client.browser_evaluate(
            function="() => window.location.href"
        )

        # Handle MCP response format: {'status': 'success', 'result': {'content': [{'type': 'text', 'text': '...'}]}}
        if isinstance(result, dict):
            if result.get("status") != "success":
                raise RuntimeError(f"Failed to get page URL: {result.get('message', 'Unknown error')}")

            # Extract content from nested structure
            # Try "result" first (Playwright MCP), then "data" (Chrome MCP)
            result_data = result.get("result") or result.get("data", {})
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
        # For Chrome MCP, use get_windows_and_tabs to get title
        if self.client_type == "chrome":
            result = self.playwright_client.get_windows_and_tabs()
            if result.get("status") == "success":
                import json
                # Chrome MCP has triple-nested JSON structure
                # Level 1: result.content[0].text
                result_data = result.get("result") or result.get("data", {})
                content_list = result_data.get("content", [])
                if content_list:
                    level1_text = content_list[0].get("text", "{}")
                    level1_data = json.loads(level1_text)
                    # Level 2: data.content[0].text
                    level2_data = level1_data.get("data", {})
                    level2_content = level2_data.get("content", [])
                    if level2_content:
                        level2_text = level2_content[0].get("text", "{}")
                        # Level 3: actual tabs data
                        tabs_data = json.loads(level2_text)
                        # Get active tab
                        for window in tabs_data.get("windows", []):
                            for tab in window.get("tabs", []):
                                if tab.get("active"):
                                    return tab.get("title", "")
                        # Fallback: return first tab title
                        if tabs_data.get("windows") and tabs_data["windows"][0].get("tabs"):
                            return tabs_data["windows"][0]["tabs"][0].get("title", "")
            return ""

        # For Playwright MCP, use browser_evaluate
        result = self.playwright_client.browser_evaluate(
            function="() => document.title"
        )

        # Handle MCP response format: {'status': 'success', 'result': {'content': [{'type': 'text', 'text': '...'}]}}
        if isinstance(result, dict):
            if result.get("status") != "success":
                return ""

            # Extract content from nested structure
            # Try "result" first (Playwright MCP), then "data" (Chrome MCP)
            result_data = result.get("result") or result.get("data", {})
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

    def click_element(self, css_selector: str, wait_for_navigation: bool = False, timeout: int = 5000) -> Dict:
        """
        Click on an element using the appropriate client method.

        Args:
            css_selector: CSS selector for the element (e.g., '[data-web-agent-id="wa-5"]')
            wait_for_navigation: Whether to wait for navigation after click (Chrome only)
            timeout: Timeout in milliseconds for waiting (Chrome only, default: 5000)

        Returns:
            Result dictionary with status
        """
        if self.client_type == "chrome":
            # Use Chrome's native click with auto-scroll
            result = self.playwright_client.chrome_click_element(
                selector=css_selector,
                wait_for_navigation=wait_for_navigation,
                timeout=timeout,
                scroll_into_view=True  # Use the new auto-scroll feature
            )

            # Handle Chrome MCP response format
            if isinstance(result, dict):
                if result.get("status") == "success":
                    return result
                else:
                    # Return error in consistent format
                    return {
                        "status": "error",
                        "message": result.get("message", "Click failed")
                    }
            return result
        else:
            # Use JavaScript evaluation for Playwright
            click_js = f"""
            () => {{
                const element = document.querySelector('{css_selector}');
                if (element) {{
                    element.click();
                    return {{success: true, clicked: true}};
                }} else {{
                    return {{success: false, error: 'Element not found in DOM'}};
                }}
            }}
            """
            result = self.playwright_client.browser_evaluate(function=click_js)

            # Normalize result format to match Chrome response
            if isinstance(result, dict) and result.get("status") == "success":
                return result
            else:
                return {
                    "status": "error",
                    "message": result.get("message", "Click failed")
                }

    def type_into_element(self, css_selector: str, text: str) -> Dict:
        """
        Type text into an input element using the appropriate client method.

        For Chrome, this uses JavaScript to simulate proper input events that
        work with React/Vue/Angular controlled inputs.

        Args:
            css_selector: CSS selector for the input element
            text: Text to type into the element

        Returns:
            Result dictionary with status
        """
        if self.client_type == "chrome":
            # Use JavaScript injection to type text with proper React-compatible events
            # This approach uses execCommand('insertText') which triggers proper input events
            import json as json_module
            escaped_text = json_module.dumps(text)

            type_js = f"""
            (function() {{
                var selector = {json_module.dumps(css_selector)};
                var text = {escaped_text};
                var element = document.querySelector(selector);

                if (!element) {{
                    return {{ success: false, error: 'Element not found: ' + selector }};
                }}

                // Focus the element
                element.focus();

                // Clear existing content
                element.select();

                // For input/textarea elements
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {{
                    // Set native value setter to bypass React's controlled input
                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    ).set;
                    var nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;

                    if (element.tagName === 'INPUT') {{
                        nativeInputValueSetter.call(element, text);
                    }} else {{
                        nativeTextAreaValueSetter.call(element, text);
                    }}

                    // Dispatch input event to trigger React state update
                    var inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
                    element.dispatchEvent(inputEvent);

                    // Also dispatch change event
                    var changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
                    element.dispatchEvent(changeEvent);

                    return {{ success: true, method: 'native_setter' }};
                }}

                // For contenteditable elements
                if (element.isContentEditable) {{
                    document.execCommand('selectAll', false, null);
                    document.execCommand('insertText', false, text);
                    return {{ success: true, method: 'execCommand' }};
                }}

                return {{ success: false, error: 'Unsupported element type' }};
            }})()
            """

            result = self.playwright_client.chrome_inject_script(
                js_script=type_js,
                script_type="MAIN"
            )

            # Handle Chrome MCP response format
            if isinstance(result, dict):
                if result.get("status") == "success":
                    return result
                else:
                    return {
                        "status": "error",
                        "message": result.get("message", "Type failed")
                    }
            return result
        else:
            # Use JavaScript evaluation for Playwright
            import json as json_module
            type_js = f"""
            () => {{
                const element = document.querySelector('{css_selector}');
                if (element) {{
                    element.value = {json_module.dumps(text)};
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return {{success: true}};
                }} else {{
                    return {{success: false, error: 'Element not found in DOM'}};
                }}
            }}
            """
            result = self.playwright_client.browser_evaluate(function=type_js)

            # Normalize result format
            if isinstance(result, dict) and result.get("status") == "success":
                return result
            else:
                return {
                    "status": "error",
                    "message": result.get("message", "Type failed")
                }

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
