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
        timeout: int = 5000,
        scroll_into_view: bool = True
    ) -> Dict[str, Any]:
        """
        Click on an element in the current page or at specific coordinates.

        Args:
            selector: CSS selector for the element to click
            coordinates: Coordinates to click at (relative to viewport), e.g., {"x": 100, "y": 200}
            wait_for_navigation: Wait for page navigation to complete after click
            timeout: Timeout in milliseconds for waiting (default: 5000)
            scroll_into_view: Automatically scroll element into view before clicking (default: True)
        """
        # If a selector is provided and scroll_into_view is enabled,
        # scroll the element into view first to ensure it's visible
        if selector and scroll_into_view:
            scroll_script = f"""
            (function() {{
                var el = document.querySelector({json.dumps(selector)});
                if (el) {{
                    el.scrollIntoView({{behavior: 'instant', block: 'center'}});
                    return true;
                }}
                return false;
            }})()
            """
            scroll_result = self.chrome_inject_script(
                js_script=scroll_script,
                script_type="MAIN"
            )
            # Small delay to let the scroll settle
            time.sleep(0.2)

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

    # ========================================================================
    # Playwright Compatibility Methods
    # These methods provide compatibility with PlaywrightMcpClient interface
    # ========================================================================

    def browser_navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigate to a URL (Playwright compatibility method).

        Args:
            url: URL to navigate to

        Returns:
            Result dictionary with status
        """
        return self.chrome_navigate(url=url)

    def browser_evaluate(self, function: str, element: str = None, ref: str = None) -> Dict[str, Any]:
        """
        Evaluate JavaScript expression on page or element (Playwright compatibility method).

        Args:
            function: JavaScript function as string (e.g., "() => { return document.title; }")
            element: Human-readable element description (optional)
            ref: Exact target element reference (optional)

        Returns:
            Result dictionary with evaluation result
        """
        # Extract the function body from the arrow function syntax
        # Handle formats like: "() => expression" or "() => { statements }"
        js_code = function.strip()

        # Remove arrow function wrapper if present
        if "=>" in js_code:
            # Extract code after =>
            parts = js_code.split("=>", 1)
            if len(parts) == 2:
                body = parts[1].strip()
                # Check if body has braces
                if body.startswith("{") and body.endswith("}"):
                    # Remove surrounding braces
                    body = body[1:-1].strip()
                    js_code = body
                else:
                    # Body is just an expression, need to add return
                    js_code = f"return {body}"

        # Generate a unique ID to store the result
        import uuid
        result_id = f"__mcp_result_{uuid.uuid4().hex[:8]}__"

        # Wrap the script to store result in a hidden element
        # chrome_inject_script doesn't return JS results, so we store them in DOM
        wrapped_script = f"""
        (function() {{
            try {{
                var result = (function() {{ {js_code} }})();
                // Store result in a hidden element
                var el = document.createElement('script');
                el.id = '{result_id}';
                el.type = 'application/json';
                el.textContent = JSON.stringify(result);
                document.head.appendChild(el);
            }} catch (e) {{
                var el = document.createElement('script');
                el.id = '{result_id}';
                el.type = 'application/json';
                el.textContent = JSON.stringify({{__error__: e.message, __stack__: e.stack}});
                document.head.appendChild(el);
            }}
        }})()
        """

        # Inject the script
        inject_result = self.chrome_inject_script(
            js_script=wrapped_script,
            script_type="MAIN"
        )

        if inject_result.get("status") != "success":
            return inject_result

        # Small delay to ensure script execution completes
        time.sleep(0.1)

        # Retrieve the result using a second script injection
        retrieve_script = f"""
        (function() {{
            var el = document.getElementById('{result_id}');
            if (el) {{
                var result = el.textContent;
                el.remove();  // Clean up
                return result;
            }}
            return null;
        }})()
        """

        # We need to use a different approach to get the result
        # Use chrome_get_web_content with a selector to read the element content
        # But first, let's check if the element exists
        check_result = self.chrome_get_web_content(
            selector=f'script#{result_id}',
            text_content=True,
            html_content=False
        )

        # Parse the nested Chrome MCP response
        try:
            result_data = check_result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data.get("content", [])
                if isinstance(content_list, list) and len(content_list) > 0:
                    outer_text = content_list[0].get("text", "{}")
                    outer_data = json.loads(outer_text)

                    if outer_data.get("status") == "success":
                        inner_data = outer_data.get("data", {})
                        inner_content = inner_data.get("content", [])
                        if isinstance(inner_content, list) and len(inner_content) > 0:
                            inner_text = inner_content[0].get("text", "{}")
                            inner_parsed = json.loads(inner_text)
                            text_content = inner_parsed.get("textContent", "")

                            # The textContent is the JSON-stringified result
                            if text_content:
                                try:
                                    actual_result = json.loads(text_content)

                                    # Check for error
                                    if isinstance(actual_result, dict) and "__error__" in actual_result:
                                        return {
                                            "status": "error",
                                            "message": actual_result["__error__"],
                                            "stack": actual_result.get("__stack__")
                                        }

                                    # Return in Playwright-compatible format
                                    return {
                                        "status": "success",
                                        "result": {
                                            "content": [{
                                                "type": "text",
                                                "text": f"### Result\n{json.dumps(actual_result, ensure_ascii=False)}"
                                            }]
                                        }
                                    }
                                except json.JSONDecodeError:
                                    # Return raw text if not valid JSON
                                    return {
                                        "status": "success",
                                        "result": {
                                            "content": [{
                                                "type": "text",
                                                "text": f"### Result\n\"{text_content}\""
                                            }]
                                        }
                                    }

        except Exception as e:
            pass

        # Clean up the result element if retrieval failed
        cleanup_script = f"""
        (function() {{
            var el = document.getElementById('{result_id}');
            if (el) el.remove();
        }})()
        """
        self.chrome_inject_script(js_script=cleanup_script, script_type="MAIN")

        # Fallback: return the original inject result (which just says injected: true)
        return {
            "status": "error",
            "message": "Failed to retrieve JavaScript evaluation result"
        }

    def browser_wait_for(
        self,
        text: str = None,
        text_gone: str = None,
        time_seconds: float = None
    ) -> Dict[str, Any]:
        """
        Wait for text to appear/disappear or a specified time to pass (Playwright compatibility method).

        Args:
            text: Text to wait for to appear
            text_gone: Text to wait for to disappear
            time_seconds: Time to wait in seconds

        Returns:
            Result dictionary with status
        """
        if time_seconds is not None:
            # Just sleep for the specified time
            time.sleep(time_seconds)
            return {
                "status": "success",
                "result": {
                    "content": [{
                        "type": "text",
                        "text": f"Waited for {time_seconds}"
                    }]
                }
            }

        if text or text_gone:
            # Chrome MCP doesn't have direct wait-for-text support
            # We'll implement a simple polling mechanism
            max_wait = 30  # Maximum 30 seconds
            poll_interval = 0.5  # Check every 500ms
            elapsed = 0

            while elapsed < max_wait:
                # Get page content
                content_result = self.chrome_get_web_content(text_content=True)

                if content_result.get("status") == "success":
                    # Extract text content from the nested response
                    result_data = content_result.get("result", {})
                    if isinstance(result_data, dict):
                        content = result_data.get("content", [])
                        if isinstance(content, list) and len(content) > 0:
                            text_content = str(content[0].get("text", ""))

                            if text and text in text_content:
                                return {
                                    "status": "success",
                                    "result": {
                                        "content": [{
                                            "type": "text",
                                            "text": f"Text found: {text}"
                                        }]
                                    }
                                }
                            elif text_gone and text_gone not in text_content:
                                return {
                                    "status": "success",
                                    "result": {
                                        "content": [{
                                            "type": "text",
                                            "text": f"Text gone: {text_gone}"
                                        }]
                                    }
                                }

                time.sleep(poll_interval)
                elapsed += poll_interval

            # Timeout
            return {
                "status": "error",
                "message": f"Timeout waiting for text: {text or text_gone}"
            }

        return {"status": "error", "message": "Must specify either text, text_gone, or time_seconds"}

    def scroll_down(self, times: int = 1, amount: int = None) -> Dict[str, Any]:
        """
        Scroll down the page using JavaScript (Playwright compatibility method).

        Args:
            times: Number of times to scroll down
            amount: Number of pixels to scroll per action (default: 300)

        Returns:
            Result dictionary with status and results
        """
        scroll_pixels = amount if amount is not None else 300
        results = []

        try:
            for i in range(times):
                # Scroll down by the specified number of pixels
                scroll_code = f"window.scrollBy(0, {scroll_pixels});"
                result = self.chrome_inject_script(
                    js_script=scroll_code,
                    script_type="MAIN"
                )

                results.append({
                    "status": result.get("status", "success"),
                    "action": "scroll_down",
                    "iteration": i + 1,
                    "scroll_amount": scroll_pixels
                })

                if result.get("status") != "success":
                    break

                # Pause between scrolls
                if i < times - 1:
                    time.sleep(0.1)

            # Return in standard MCP format
            return {
                "status": "success",
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "message": f"Scrolled down {times} time(s)",
                            "results": results
                        })
                    }]
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to scroll down: {str(e)}"
            }

    def scroll_up(self, times: int = 1, amount: int = None) -> Dict[str, Any]:
        """
        Scroll up the page using JavaScript (Playwright compatibility method).

        Args:
            times: Number of times to scroll up
            amount: Number of pixels to scroll per action (default: 300)

        Returns:
            Result dictionary with status and results
        """
        scroll_pixels = amount if amount is not None else 300
        results = []

        try:
            for i in range(times):
                # Scroll up by the specified number of pixels (negative value)
                scroll_code = f"window.scrollBy(0, -{scroll_pixels});"
                result = self.chrome_inject_script(
                    js_script=scroll_code,
                    script_type="MAIN"
                )

                results.append({
                    "status": result.get("status", "success"),
                    "action": "scroll_up",
                    "iteration": i + 1,
                    "scroll_amount": scroll_pixels
                })

                if result.get("status") != "success":
                    break

                # Pause between scrolls
                if i < times - 1:
                    time.sleep(0.1)

            # Return in standard MCP format
            return {
                "status": "success",
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "message": f"Scrolled up {times} time(s)",
                            "results": results
                        })
                    }]
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to scroll up: {str(e)}"
            }

    def browser_close(self) -> Dict[str, Any]:
        """
        Close the current browser page/tab (Playwright compatibility method).

        Returns:
            Result dictionary with status
        """
        # Close the active tab
        return self.chrome_close_tabs()

    def browser_tabs(self, action: str, index: int = None) -> Dict[str, Any]:
        """
        Manage browser tabs - list, create, close, or select (Playwright compatibility method).

        Args:
            action: Operation to perform (list, new, close, select)
            index: Tab index for close/select operations

        Returns:
            Result dictionary with tabs information
        """
        if action == "list":
            # Get all windows and tabs
            result = self.get_windows_and_tabs()

            if result.get("status") == "success":
                # Parse the response to extract tabs
                result_data = result.get("result", {})
                content = result_data.get("content", [])

                if isinstance(content, list) and len(content) > 0:
                    text_data = content[0].get("text", "")

                    # Parse the JSON data
                    try:
                        data = json.loads(text_data)
                        if data.get("status") == "success":
                            inner_data = data.get("data", {})
                            inner_content = inner_data.get("content", [])

                            if isinstance(inner_content, list) and len(inner_content) > 0:
                                tabs_json = inner_content[0].get("text", "{}")
                                tabs_data = json.loads(tabs_json)

                                # Extract tabs from windows
                                tabs_list = []
                                current_index = -1
                                tab_index = 0

                                for window in tabs_data.get("windows", []):
                                    for tab in window.get("tabs", []):
                                        tabs_list.append({
                                            "index": tab_index,
                                            "title": tab.get("title", ""),
                                            "url": tab.get("url", ""),
                                            "active": tab.get("active", False)
                                        })

                                        if tab.get("active"):
                                            current_index = tab_index

                                        tab_index += 1

                                # Format as markdown text for Playwright compatibility
                                markdown_lines = ["### Open tabs"]
                                for tab in tabs_list:
                                    current_marker = " (current)" if tab["index"] == current_index else ""
                                    markdown_lines.append(
                                        f"- {tab['index']}:{current_marker} [{tab['title']}] ({tab['url']})"
                                    )

                                markdown_text = "\n".join(markdown_lines)

                                return {
                                    "status": "success",
                                    "result": {
                                        "content": [{
                                            "type": "text",
                                            "text": markdown_text
                                        }]
                                    }
                                }
                    except Exception as e:
                        return {
                            "status": "error",
                            "message": f"Failed to parse tabs data: {str(e)}"
                        }

            return result

        elif action == "new":
            # Chrome MCP doesn't have a direct "new tab" method
            # We can navigate to a blank page in a new window
            result = self.chrome_navigate(url="about:blank", new_window=False)
            return result

        elif action == "close":
            if index is None:
                return {"status": "error", "message": "index required for close action"}

            # Get all tabs to find the tab ID
            tabs_result = self.get_windows_and_tabs()

            if tabs_result.get("status") == "success":
                # Parse to get tab IDs
                try:
                    result_data = tabs_result.get("result", {})
                    content = result_data.get("content", [])
                    text_data = content[0].get("text", "")
                    data = json.loads(text_data)

                    if data.get("status") == "success":
                        inner_data = data.get("data", {})
                        inner_content = inner_data.get("content", [])
                        tabs_json = inner_content[0].get("text", "{}")
                        tabs_data = json.loads(tabs_json)

                        # Find tab at index
                        tab_index = 0
                        for window in tabs_data.get("windows", []):
                            for tab in window.get("tabs", []):
                                if tab_index == index:
                                    tab_id = tab.get("tabId")
                                    return self.chrome_close_tabs(tab_ids=[tab_id])
                                tab_index += 1

                        return {"status": "error", "message": f"Tab at index {index} not found"}
                except Exception as e:
                    return {"status": "error", "message": f"Failed to close tab: {str(e)}"}

            return tabs_result

        elif action == "select":
            if index is None:
                return {"status": "error", "message": "index required for select action"}

            # Get all tabs to find the tab URL
            tabs_result = self.get_windows_and_tabs()

            if tabs_result.get("status") == "success":
                # Parse to get tab URLs
                try:
                    result_data = tabs_result.get("result", {})
                    content = result_data.get("content", [])
                    text_data = content[0].get("text", "")
                    data = json.loads(text_data)

                    if data.get("status") == "success":
                        inner_data = data.get("data", {})
                        inner_content = inner_data.get("content", [])
                        tabs_json = inner_content[0].get("text", "{}")
                        tabs_data = json.loads(tabs_json)

                        # Find tab at index
                        tab_index = 0
                        for window in tabs_data.get("windows", []):
                            for tab in window.get("tabs", []):
                                if tab_index == index:
                                    tab_url = tab.get("url")
                                    # Navigate to the tab's URL to activate it
                                    return self.chrome_navigate(url=tab_url)
                                tab_index += 1

                        return {"status": "error", "message": f"Tab at index {index} not found"}
                except Exception as e:
                    return {"status": "error", "message": f"Failed to select tab: {str(e)}"}

            return tabs_result

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def browser_take_screenshot(
        self,
        filename: str = None,
        element: str = None,
        ref: str = None,
        full_page: bool = False,
        screenshot_type: str = "png"
    ) -> Dict[str, Any]:
        """
        Take a screenshot of the current page (Playwright compatibility method).

        Args:
            filename: File name to save screenshot to
            element: Human-readable element description (for element screenshots)
            ref: Exact target element reference (for element screenshots)
            full_page: Take screenshot of full scrollable page
            screenshot_type: Image format (png or jpeg)

        Returns:
            Result dictionary with screenshot info
        """
        params = {}
        if filename:
            params["name"] = filename
        if full_page:
            params["full_page"] = full_page
        if element:
            # Chrome MCP uses CSS selector instead of element description
            # We'll use the element as a selector
            params["selector"] = element

        params["save_png"] = True
        params["store_base64"] = False

        return self.chrome_screenshot(**params)

    # =======================================================================
    # Content Extraction Methods
    # These methods provide different ways to extract content from pages
    # =======================================================================

    def get_text_content(self, url: str = None) -> Dict[str, Any]:
        """
        Get the visible text content of the page.

        Args:
            url: URL to get content from. If not provided, uses current active tab

        Returns:
            Dictionary with text content and metadata
        """
        return self.chrome_get_web_content(url=url, text_content=True, html_content=False)

    def get_html_content(self, url: str = None) -> Dict[str, Any]:
        """
        Get the HTML content of the page.

        Args:
            url: URL to get content from. If not provided, uses current active tab

        Returns:
            Dictionary with HTML content
        """
        return self.chrome_get_web_content(url=url, text_content=False, html_content=True)

    def get_selector_content(self, selector: str, url: str = None, html: bool = True) -> Dict[str, Any]:
        """
        Get content from a specific element using CSS selector.

        Args:
            selector: CSS selector to target specific element
            url: URL to get content from. If not provided, uses current active tab
            html: If True, returns HTML content. If False, returns text content

        Returns:
            Dictionary with content from the selected element
        """
        return self.chrome_get_web_content(
            url=url,
            text_content=not html,
            html_content=html,
            selector=selector
        )

    def get_content_by_script(self, script: str = None, url: str = None) -> Dict[str, Any]:
        """
        Get content by injecting and executing JavaScript.

        Args:
            script: JavaScript code to execute. If not provided, returns full page HTML
            url: URL to inject script into. If not provided, uses current active tab

        Returns:
            Dictionary with script execution results
        """
        if script is None:
            # Default script to get full page HTML
            script = """
            (function() {
                // Get the full HTML including doctype
                var doctype = document.doctype ?
                    '<!DOCTYPE ' + document.doctype.name + '>' : '';
                return doctype + document.documentElement.outerHTML;
            })()
            """

        # Use browser_evaluate which handles the script injection and result return
        result = self.browser_evaluate(f"() => {{ {script} }}")

        # Format the result to match other content extraction methods
        if result.get("status") == "success":
            # Extract the actual result from the nested structure
            result_data = result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data["content"]
                if isinstance(content_list, list) and len(content_list) > 0:
                    text_content = content_list[0].get("text", "")
                    return {
                        "status": "success",
                        "result": {
                            "scriptResult": text_content,
                            "url": url or "current_tab",
                            "method": "script_injection"
                        }
                    }

        return result
