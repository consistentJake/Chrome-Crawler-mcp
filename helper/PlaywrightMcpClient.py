import time
import subprocess
import os
import sys
import json
import random
from typing import Dict, Any, List, Optional


class MCPPlaywrightClient:
    """Client for interacting with MCP Playwright Server via STDIO"""

    def __init__(
        self,
        mcp_server_path: str = None,
        mcp_command: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        extension_token: Optional[str] = None,
        scroll_amount: int = 300,
        scroll_pause: float = 0.1,
        jitter_range: tuple = (0.7, 1.3),
    ):
        """
        Initialize the Playwright MCP client.

        Args:
            mcp_server_path: Path to a custom Playwright MCP server entrypoint.
            mcp_command: Full command to start the MCP server. If None, defaults
                         to the x.com configuration:
                         ["npx", "@playwright/mcp@latest", "--extension"].
            env: Environment variables to pass to the MCP server process.
            extension_token: Token for PLAYWRIGHT_MCP_EXTENSION_TOKEN. If provided,
                             it is added to the server env when not already present.
                             If omitted, falls back to env var or default token.
            scroll_amount: Number of pixels to scroll per action (default: 300)
            scroll_pause: Pause between scroll actions in seconds (default: 0.1)
            jitter_range: Tuple of (min, max) multipliers for random jitter (default: 0.7 to 1.3)
        """
        # default_token = "_dj-nQ5KMNif5TTJln6g1B7HsjfSr8d5-CGokFw9Q3A" # linux token
        default_token = "4Exp11p2Kle_VSCJ5v6UgYksDs2s53Ty2vAe3mzYnqQ" #mac token
        self.mcp_server_path = mcp_server_path
        self.mcp_command = mcp_command
        self.scroll_amount = scroll_amount
        self.scroll_pause = scroll_pause
        self.jitter_range = jitter_range
        self.env = os.environ.copy()
        if env:
            self.env.update(env)
        effective_token = (
            extension_token
            or self.env.get("PLAYWRIGHT_MCP_EXTENSION_TOKEN")
            or default_token
        )
        if effective_token:
            self.env["PLAYWRIGHT_MCP_EXTENSION_TOKEN"] = effective_token
        self.process = None
        self.request_id = 0
        self._start_server()

    def _start_server(self):
        """Start the MCP server subprocess"""
        try:
            if self.mcp_command:
                command = self.mcp_command
            elif self.mcp_server_path:
                command = ["npx", "node", self.mcp_server_path]
            else:
                command = ["npx", "@playwright/mcp@latest", "--extension"]

            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=self.env,
            )
            print("Playwright MCP server started successfully")
        except Exception as e:
            print(f"Failed to start Playwright MCP server: {e}")
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
            print("Playwright MCP server closed")

    # Navigation methods

    def browser_navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigate to a URL.

        Args:
            url: The URL to navigate to
        """
        return self._make_request("browser_navigate", {"url": url})

    def browser_navigate_back(self) -> Dict[str, Any]:
        """Go back to the previous page"""
        return self._make_request("browser_navigate_back", {})

    # Interaction methods

    def browser_click(self, element: str, ref: str, button: str = "left",
                     double_click: bool = False, modifiers: List[str] = None) -> Dict[str, Any]:
        """
        Click on a web page element.

        Args:
            element: Human-readable element description
            ref: Exact target element reference from the page snapshot
            button: Button to click (left, right, middle)
            double_click: Whether to perform a double click
            modifiers: List of modifier keys (Alt, Control, ControlOrMeta, Meta, Shift)
        """
        params = {
            "element": element,
            "ref": ref
        }
        if button != "left":
            params["button"] = button
        if double_click:
            params["doubleClick"] = double_click
        if modifiers:
            params["modifiers"] = modifiers
        return self._make_request("browser_click", params)

    def browser_type(self, element: str, ref: str, text: str,
                    slowly: bool = False, submit: bool = False) -> Dict[str, Any]:
        """
        Type text into an editable element.

        Args:
            element: Human-readable element description
            ref: Exact target element reference from the page snapshot
            text: Text to type
            slowly: Whether to type one character at a time
            submit: Whether to submit (press Enter after)
        """
        params = {
            "element": element,
            "ref": ref,
            "text": text
        }
        if slowly:
            params["slowly"] = slowly
        if submit:
            params["submit"] = submit
        return self._make_request("browser_type", params)

    def browser_press_key(self, key: str) -> Dict[str, Any]:
        """
        Press a key on the keyboard.

        Args:
            key: Name of the key to press (e.g., 'ArrowLeft', 'a', 'Enter', 'PageDown')
        """
        return self._make_request("browser_press_key", {"key": key})

    def browser_hover(self, element: str, ref: str) -> Dict[str, Any]:
        """
        Hover over an element.

        Args:
            element: Human-readable element description
            ref: Exact target element reference from the page snapshot
        """
        return self._make_request("browser_hover", {
            "element": element,
            "ref": ref
        })

    def browser_drag(self, start_element: str, start_ref: str,
                    end_element: str, end_ref: str) -> Dict[str, Any]:
        """
        Perform drag and drop between two elements.

        Args:
            start_element: Human-readable source element description
            start_ref: Exact source element reference
            end_element: Human-readable target element description
            end_ref: Exact target element reference
        """
        return self._make_request("browser_drag", {
            "startElement": start_element,
            "startRef": start_ref,
            "endElement": end_element,
            "endRef": end_ref
        })

    # Form methods

    def browser_fill_form(self, fields: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Fill multiple form fields.

        Args:
            fields: List of fields with name, type, ref, and value
                   Example: [{"name": "username", "type": "textbox", "ref": "e1", "value": "john"}]
        """
        return self._make_request("browser_fill_form", {"fields": fields})

    def browser_select_option(self, element: str, ref: str, values: List[str]) -> Dict[str, Any]:
        """
        Select an option in a dropdown.

        Args:
            element: Human-readable element description
            ref: Exact target element reference
            values: Array of values to select
        """
        return self._make_request("browser_select_option", {
            "element": element,
            "ref": ref,
            "values": values
        })

    def browser_file_upload(self, paths: List[str] = None) -> Dict[str, Any]:
        """
        Upload one or multiple files.

        Args:
            paths: Absolute paths to files to upload. If omitted, file chooser is cancelled.
        """
        params = {}
        if paths:
            params["paths"] = paths
        return self._make_request("browser_file_upload", params)

    # Page inspection methods

    def browser_snapshot(self) -> Dict[str, Any]:
        """Capture accessibility snapshot of the current page"""
        return self._make_request("browser_snapshot", {})

    def browser_take_screenshot(self, filename: str = None, element: str = None,
                               ref: str = None, full_page: bool = False,
                               screenshot_type: str = "png") -> Dict[str, Any]:
        """
        Take a screenshot of the current page.

        Args:
            filename: File name to save screenshot to
            element: Human-readable element description (for element screenshots)
            ref: Exact target element reference (for element screenshots)
            full_page: Take screenshot of full scrollable page
            screenshot_type: Image format (png or jpeg)
        """
        params = {}
        if filename:
            params["filename"] = filename
        if element:
            params["element"] = element
        if ref:
            params["ref"] = ref
        if full_page:
            params["fullPage"] = full_page
        if screenshot_type != "png":
            params["type"] = screenshot_type
        return self._make_request("browser_take_screenshot", params)

    def browser_console_messages(self, only_errors: bool = False) -> Dict[str, Any]:
        """
        Returns all console messages.

        Args:
            only_errors: Only return error messages
        """
        params = {}
        if only_errors:
            params["onlyErrors"] = only_errors
        return self._make_request("browser_console_messages", params)

    def browser_network_requests(self) -> Dict[str, Any]:
        """Returns all network requests since loading the page"""
        return self._make_request("browser_network_requests", {})

    # JavaScript execution

    def browser_evaluate(self, function: str, element: str = None, ref: str = None) -> Dict[str, Any]:
        """
        Evaluate JavaScript expression on page or element.

        Args:
            function: JavaScript function as string (e.g., "() => { return document.title; }")
            element: Human-readable element description (optional)
            ref: Exact target element reference (optional)
        """
        params = {"function": function}
        if element:
            params["element"] = element
        if ref:
            params["ref"] = ref
        return self._make_request("browser_evaluate", params)

    def browser_run_code(self, code: str) -> Dict[str, Any]:
        """
        Run Playwright code snippet.

        Args:
            code: Playwright code snippet to run (e.g., "await page.getByRole('button').click();")
        """
        return self._make_request("browser_run_code", {"code": code})

    # Wait methods

    def browser_wait_for(self, text: str = None, text_gone: str = None,
                        time_seconds: float = None) -> Dict[str, Any]:
        """
        Wait for text to appear/disappear or a specified time to pass.

        Args:
            text: Text to wait for to appear
            text_gone: Text to wait for to disappear
            time_seconds: Time to wait in seconds
        """
        params = {}
        if text:
            params["text"] = text
        if text_gone:
            params["textGone"] = text_gone
        if time_seconds is not None:
            params["time"] = time_seconds
        return self._make_request("browser_wait_for", params)

    # Tab management

    def browser_tabs(self, action: str, index: int = None) -> Dict[str, Any]:
        """
        List, create, close, or select a browser tab.

        Args:
            action: Operation to perform (list, new, close, select)
            index: Tab index for close/select operations
        """
        params = {"action": action}
        if index is not None:
            params["index"] = index
        return self._make_request("browser_tabs", params)

    # Dialog handling

    def browser_handle_dialog(self, accept: bool, prompt_text: str = None) -> Dict[str, Any]:
        """
        Handle a dialog.

        Args:
            accept: Whether to accept the dialog
            prompt_text: Text for prompt dialogs
        """
        params = {"accept": accept}
        if prompt_text:
            params["promptText"] = prompt_text
        return self._make_request("browser_handle_dialog", params)

    # Browser management

    def browser_close(self) -> Dict[str, Any]:
        """Close the page"""
        return self._make_request("browser_close", {})

    def browser_resize(self, width: int, height: int) -> Dict[str, Any]:
        """
        Resize the browser window.

        Args:
            width: Width of the browser window
            height: Height of the browser window
        """
        return self._make_request("browser_resize", {
            "width": width,
            "height": height
        })

    def browser_install(self) -> Dict[str, Any]:
        """Install the browser specified in the config"""
        return self._make_request("browser_install", {})

    # Convenience methods

    def scroll_down(self, times: int = 1, amount: int = None) -> Dict[str, Any]:
        """
        Scroll down the page using JavaScript.

        Args:
            times: Number of times to scroll down
            amount: Number of pixels to scroll per action (overrides default)

        Returns:
            Dict with status and results
        """
        scroll_pixels = amount if amount is not None else self.scroll_amount
        results = []

        try:
            for i in range(times):
                # Scroll down by the specified number of pixels
                scroll_code = f"window.scrollBy(0, {scroll_pixels});"
                result = self.browser_run_code(scroll_code)

                results.append({
                    "status": result.get("status", "success"),
                    "action": "scroll_down",
                    "iteration": i + 1,
                    "scroll_amount": scroll_pixels
                })

                if result.get("status") != "success":
                    break

                # Pause between scrolls with jitter
                if i < times - 1:  # Don't pause after the last scroll
                    jittered_pause = self.scroll_pause * random.uniform(*self.jitter_range)
                    time.sleep(jittered_pause)

            return {
                "status": "success",
                "message": f"Scrolled down {times} time(s)",
                "results": results
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to scroll down: {str(e)}",
                "results": results
            }

    def scroll_up(self, times: int = 1, amount: int = None) -> Dict[str, Any]:
        """
        Scroll up the page using JavaScript.

        Args:
            times: Number of times to scroll up
            amount: Number of pixels to scroll per action (overrides default)

        Returns:
            Dict with status and results
        """
        scroll_pixels = amount if amount is not None else self.scroll_amount
        results = []

        try:
            for i in range(times):
                # Scroll up by the specified number of pixels (negative value)
                scroll_code = f"window.scrollBy(0, -{scroll_pixels});"
                result = self.browser_run_code(scroll_code)

                results.append({
                    "status": result.get("status", "success"),
                    "action": "scroll_up",
                    "iteration": i + 1,
                    "scroll_amount": scroll_pixels
                })

                if result.get("status") != "success":
                    break

                # Pause between scrolls with jitter
                if i < times - 1:  # Don't pause after the last scroll
                    jittered_pause = self.scroll_pause * random.uniform(*self.jitter_range)
                    time.sleep(jittered_pause)

            return {
                "status": "success",
                "message": f"Scrolled up {times} time(s)",
                "results": results
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to scroll up: {str(e)}",
                "results": results
            }

    def wait_seconds(self, seconds: float) -> Dict[str, Any]:
        """
        Wait for a specified number of seconds.

        Args:
            seconds: Number of seconds to wait
        """
        return self.browser_wait_for(time_seconds=seconds)
