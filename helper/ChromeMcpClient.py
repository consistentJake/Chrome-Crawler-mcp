import time
import subprocess
import os
import json
from typing import Dict, Any, List, Optional


class MCPChromeClient:
    """Client for interacting with MCP Chrome Server via STDIO"""

    def __init__(
        self,
        mcp_server_path: str = "/Users/zhenkai/.nvm/versions/node/v22.16.0/lib/node_modules/mcp-chrome-bridge/dist/mcp/mcp-server-stdio.js",
        mcp_command: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the Chrome MCP client.

        Args:
            mcp_server_path: Path to the Chrome MCP server entrypoint.
            mcp_command: Full command to start the MCP server. If None, defaults
                         to ["npx", "node", mcp_server_path].
            env: Environment variables to pass to the MCP server process.
        """
        self.mcp_server_path = mcp_server_path
        self.mcp_command = mcp_command
        self.env = os.environ.copy()
        if env:
            self.env.update(env)
        self.process = None
        self.request_id = 0
        self._start_server()

    def _start_server(self):
        """Start the MCP server subprocess"""
        try:
            if self.mcp_command:
                command = self.mcp_command
            else:
                command = ["npx", "node", self.mcp_server_path]

            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=self.env,
            )
            print("Chrome MCP server started successfully")
        except Exception as e:
            print(f"Failed to start Chrome MCP server: {e}")
            raise

    def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server"""
        if not self.process:
            return {"status": "error", "message": "MCP server not started"}

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }

        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()

            # Read response
            response_line = self.process.stdout.readline()
            if not response_line:
                return {"status": "error", "message": "No response from server"}

            response = json.loads(response_line.strip())

            if "error" in response:
                return {"status": "error", "message": response["error"]}
            elif "result" in response:
                return {"status": "success", "result": response["result"]}
            else:
                return {"status": "success", "result": response}

        except Exception as e:
            print(f"Error communicating with MCP server: {e}")
            return {"status": "error", "message": str(e)}

    def _make_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a tool call request to the MCP server"""
        return self._send_request("tools/call", {
            "name": method,
            "arguments": params or {}
        })

    def close(self):
        """Close the MCP server subprocess"""
        if self.process:
            self.process.stdin.close()
            self.process.stdout.close()
            self.process.stderr.close()
            self.process.terminate()
            self.process.wait()
            print("Chrome MCP server closed")

    # Window and Tab Management

    def get_windows_and_tabs(self) -> Dict[str, Any]:
        """Get all currently open browser windows and tabs"""
        return self._make_request("get_windows_and_tabs", {})

    def chrome_navigate(
        self,
        url: str = None,
        refresh: bool = False,
        new_window: bool = False,
        width: int = 1280,
        height: int = 720
    ) -> Dict[str, Any]:
        """
        Navigate to a URL or refresh the current tab.

        Args:
            url: URL to navigate to
            refresh: Refresh the current active tab instead of navigating to a URL
            new_window: Create a new window to navigate to the URL
            width: Viewport width in pixels (default: 1280)
            height: Viewport height in pixels (default: 720)
        """
        params = {}
        if url:
            params["url"] = url
        if refresh:
            params["refresh"] = refresh
        if new_window:
            params["newWindow"] = new_window
        if width != 1280:
            params["width"] = width
        if height != 720:
            params["height"] = height
        return self._make_request("chrome_navigate", params)

    def chrome_close_tabs(self, tab_ids: List[int] = None, url: str = None) -> Dict[str, Any]:
        """
        Close one or more browser tabs.

        Args:
            tab_ids: Array of tab IDs to close. If not provided, will close the active tab.
            url: Close tabs matching this URL. Can be used instead of tabIds.
        """
        params = {}
        if tab_ids:
            params["tabIds"] = tab_ids
        if url:
            params["url"] = url
        return self._make_request("chrome_close_tabs", params)

    def chrome_go_back_or_forward(self, is_forward: bool = False) -> Dict[str, Any]:
        """
        Navigate back or forward in browser history.

        Args:
            is_forward: Go forward in history if true, go back if false (default: false)
        """
        return self._make_request("chrome_go_back_or_forward", {"isForward": is_forward})

    # Page Content and Screenshots

    def chrome_get_web_content(
        self,
        url: str = None,
        text_content: bool = True,
        html_content: bool = False,
        selector: str = None
    ) -> Dict[str, Any]:
        """
        Fetch content from a web page.

        Args:
            url: URL to fetch content from. If not provided, uses the current active tab
            text_content: Get the visible text content of the page with metadata
            html_content: Get the visible HTML content of the page
            selector: CSS selector to get content from a specific element
        """
        params = {}
        if url:
            params["url"] = url
        if text_content:
            params["textContent"] = text_content
        if html_content:
            params["htmlContent"] = html_content
        if selector:
            params["selector"] = selector
        return self._make_request("chrome_get_web_content", params)

    def chrome_screenshot(
        self,
        name: str = None,
        full_page: bool = True,
        save_png: bool = True,
        store_base64: bool = False,
        selector: str = None,
        width: int = 800,
        height: int = 600
    ) -> Dict[str, Any]:
        """
        Take a screenshot of the current page or a specific element.

        Args:
            name: Name for the screenshot, if saving as PNG
            full_page: Store screenshot of the entire page (default: true)
            save_png: Save screenshot as PNG file (default: true)
            store_base64: Return screenshot in base64 format (default: false)
            selector: CSS selector for element to screenshot
            width: Width in pixels (default: 800)
            height: Height in pixels (default: 600)
        """
        params = {}
        if name:
            params["name"] = name
        if not full_page:
            params["fullPage"] = full_page
        if not save_png:
            params["savePng"] = save_png
        if store_base64:
            params["storeBase64"] = store_base64
        if selector:
            params["selector"] = selector
        if width != 800:
            params["width"] = width
        if height != 600:
            params["height"] = height
        return self._make_request("chrome_screenshot", params)

    # Element Interaction

    def chrome_click_element(
        self,
        selector: str = None,
        coordinates: Dict[str, int] = None,
        wait_for_navigation: bool = False,
        timeout: int = 5000
    ) -> Dict[str, Any]:
        """
        Click on an element in the current page or at specific coordinates.

        Args:
            selector: CSS selector for the element to click
            coordinates: Coordinates to click at (relative to viewport), e.g., {"x": 100, "y": 200}
            wait_for_navigation: Wait for page navigation to complete after click
            timeout: Timeout in milliseconds for waiting (default: 5000)
        """
        params = {}
        if selector:
            params["selector"] = selector
        if coordinates:
            params["coordinates"] = coordinates
        if wait_for_navigation:
            params["waitForNavigation"] = wait_for_navigation
        if timeout != 5000:
            params["timeout"] = timeout
        return self._make_request("chrome_click_element", params)

    def chrome_fill_or_select(self, selector: str, value: str) -> Dict[str, Any]:
        """
        Fill a form element or select an option with the specified value.

        Args:
            selector: CSS selector for the input element to fill or select
            value: Value to fill or select into the element
        """
        return self._make_request("chrome_fill_or_select", {
            "selector": selector,
            "value": value
        })

    def chrome_get_interactive_elements(
        self,
        selector: str = None,
        text_query: str = None,
        include_coordinates: bool = True
    ) -> Dict[str, Any]:
        """
        Get interactive elements from the current page.

        Args:
            selector: CSS selector to filter interactive elements
            text_query: Text to search for within interactive elements (fuzzy search)
            include_coordinates: Include element coordinates in the response (default: true)
        """
        params = {}
        if selector:
            params["selector"] = selector
        if text_query:
            params["textQuery"] = text_query
        if not include_coordinates:
            params["includeCoordinates"] = include_coordinates
        return self._make_request("chrome_get_interactive_elements", params)

    def chrome_keyboard(
        self,
        keys: str,
        selector: str = None,
        delay: int = 0
    ) -> Dict[str, Any]:
        """
        Simulate keyboard events in the browser.

        Args:
            keys: Keys to simulate (e.g., "Enter", "Ctrl+C", "A,B,C" for sequence)
            selector: CSS selector for the element to send keyboard events to (optional)
            delay: Delay between key sequences in milliseconds (default: 0)
        """
        params = {"keys": keys}
        if selector:
            params["selector"] = selector
        if delay > 0:
            params["delay"] = delay
        return self._make_request("chrome_keyboard", params)

    # Network and Requests

    def chrome_network_request(
        self,
        url: str,
        method: str = "GET",
        headers: Dict[str, str] = None,
        body: str = None,
        timeout: int = 30000
    ) -> Dict[str, Any]:
        """
        Send a network request from the browser with cookies and other browser context.

        Args:
            url: URL to send the request to
            method: HTTP method to use (default: GET)
            headers: Headers to include in the request
            body: Body of the request (for POST, PUT, etc.)
            timeout: Timeout in milliseconds (default: 30000)
        """
        params = {"url": url}
        if method != "GET":
            params["method"] = method
        if headers:
            params["headers"] = headers
        if body:
            params["body"] = body
        if timeout != 30000:
            params["timeout"] = timeout
        return self._make_request("chrome_network_request", params)

    def chrome_network_debugger_start(self, url: str = None) -> Dict[str, Any]:
        """
        Start capturing network requests from a web page using Chrome Debugger API (with responseBody).

        Args:
            url: URL to capture network requests from. If not provided, uses the current active tab
        """
        params = {}
        if url:
            params["url"] = url
        return self._make_request("chrome_network_debugger_start", params)

    def chrome_network_debugger_stop(self) -> Dict[str, Any]:
        """Stop capturing network requests using Chrome Debugger API and return the captured data."""
        return self._make_request("chrome_network_debugger_stop", {})

    def chrome_network_capture_start(self, url: str = None) -> Dict[str, Any]:
        """
        Start capturing network requests from a web page using Chrome webRequest API (without responseBody).

        Args:
            url: URL to capture network requests from. If not provided, uses the current active tab
        """
        params = {}
        if url:
            params["url"] = url
        return self._make_request("chrome_network_capture_start", params)

    def chrome_network_capture_stop(self) -> Dict[str, Any]:
        """Stop capturing network requests using webRequest API and return the captured data."""
        return self._make_request("chrome_network_capture_stop", {})

    # History and Bookmarks

    def chrome_history(
        self,
        text: str = None,
        start_time: str = None,
        end_time: str = None,
        max_results: int = 100,
        exclude_current_tabs: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieve and search browsing history from Chrome.

        Args:
            text: Text to search for in history URLs and titles
            start_time: Start time as a date string (e.g., "2023-10-01", "1 day ago", "yesterday")
            end_time: End time as a date string (default: current time)
            max_results: Maximum number of history entries to return (default: 100)
            exclude_current_tabs: Filter out URLs that are currently open (default: false)
        """
        params = {}
        if text:
            params["text"] = text
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        if max_results != 100:
            params["maxResults"] = max_results
        if exclude_current_tabs:
            params["excludeCurrentTabs"] = exclude_current_tabs
        return self._make_request("chrome_history", params)

    def chrome_bookmark_search(
        self,
        query: str = None,
        folder_path: str = None,
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Search Chrome bookmarks by title and URL.

        Args:
            query: Search query to match against bookmark titles and URLs
            folder_path: Optional folder path or ID to limit search to a specific bookmark folder
            max_results: Maximum number of bookmarks to return (default: 50)
        """
        params = {}
        if query:
            params["query"] = query
        if folder_path:
            params["folderPath"] = folder_path
        if max_results != 50:
            params["maxResults"] = max_results
        return self._make_request("chrome_bookmark_search", params)

    def chrome_bookmark_add(
        self,
        url: str = None,
        title: str = None,
        parent_id: str = None,
        create_folder: bool = False
    ) -> Dict[str, Any]:
        """
        Add a new bookmark to Chrome.

        Args:
            url: URL to bookmark. If not provided, uses the current active tab URL
            title: Title for the bookmark. If not provided, uses the page title
            parent_id: Parent folder path or ID to add the bookmark to
            create_folder: Whether to create the parent folder if it does not exist (default: false)
        """
        params = {}
        if url:
            params["url"] = url
        if title:
            params["title"] = title
        if parent_id:
            params["parentId"] = parent_id
        if create_folder:
            params["createFolder"] = create_folder
        return self._make_request("chrome_bookmark_add", params)

    def chrome_bookmark_delete(
        self,
        bookmark_id: str = None,
        url: str = None,
        title: str = None
    ) -> Dict[str, Any]:
        """
        Delete a bookmark from Chrome.

        Args:
            bookmark_id: ID of the bookmark to delete
            url: URL of the bookmark to delete (used if bookmarkId is not provided)
            title: Title of the bookmark to help with matching when deleting by URL
        """
        params = {}
        if bookmark_id:
            params["bookmarkId"] = bookmark_id
        if url:
            params["url"] = url
        if title:
            params["title"] = title
        return self._make_request("chrome_bookmark_delete", params)

    # Console and Debugging

    def chrome_console(
        self,
        url: str = None,
        max_messages: int = 100,
        include_exceptions: bool = True
    ) -> Dict[str, Any]:
        """
        Capture and retrieve all console output from the current active browser tab/page.

        Args:
            url: URL to navigate to and capture console from
            max_messages: Maximum number of console messages to capture (default: 100)
            include_exceptions: Include uncaught exceptions in the output (default: true)
        """
        params = {}
        if url:
            params["url"] = url
        if max_messages != 100:
            params["maxMessages"] = max_messages
        if not include_exceptions:
            params["includeExceptions"] = include_exceptions
        return self._make_request("chrome_console", params)

    # Advanced Features

    def search_tabs_content(self, query: str) -> Dict[str, Any]:
        """
        Search for related content from the currently open tab and return the corresponding web pages.

        Args:
            query: The query to search for related content
        """
        return self._make_request("search_tabs_content", {"query": query})

    def chrome_inject_script(
        self,
        js_script: str,
        script_type: str,
        url: str = None
    ) -> Dict[str, Any]:
        """
        Inject a user-specified content script into the webpage.

        Args:
            js_script: The content script to inject
            script_type: The JavaScript world for a script to execute within (ISOLATED or MAIN)
            url: If a URL is specified, inject the script into the webpage corresponding to the URL
        """
        return self._make_request("chrome_inject_script", {
            "jsScript": js_script,
            "type": script_type,
            "url": url
        })

    def chrome_send_command_to_inject_script(
        self,
        event_name: str,
        payload: str = None,
        tab_id: int = None
    ) -> Dict[str, Any]:
        """
        Trigger events for scripts injected using chrome_inject_script.

        Args:
            event_name: The eventName your injected content script listens for
            payload: The payload passed to event, must be a json string
            tab_id: The tab where you previously injected the script (if not provided, use the currently active tab)
        """
        params = {"eventName": event_name}
        if payload:
            params["payload"] = payload
        if tab_id:
            params["tabId"] = tab_id
        return self._make_request("chrome_send_command_to_inject_script", params)
