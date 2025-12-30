# ChromeMcpClient Usage Guide

A Python utility library for interacting with the Chrome MCP server, similar to the PlaywrightMcpClient.

## Installation

No additional dependencies required beyond what's already in the project. The client uses the Chrome MCP server configured in your MCP settings.

## Basic Usage

```python
from helper.ChromeMcpClient import MCPChromeClient

# Initialize the client
client = MCPChromeClient()

try:
    # Your automation code here
    result = client.get_windows_and_tabs()
    print(result)
finally:
    # Always close the client when done
    client.close()
```

## Configuration

### Default Configuration
By default, the client uses the Chrome MCP server at:
```
/Users/zhenkai/.nvm/versions/node/v22.16.0/lib/node_modules/mcp-chrome-bridge/dist/mcp/mcp-server-stdio.js
```

### Custom Configuration
```python
# Custom server path
client = MCPChromeClient(
    mcp_server_path="/path/to/your/mcp-server.js"
)

# Custom command
client = MCPChromeClient(
    mcp_command=["npx", "node", "/custom/path/mcp-server.js"]
)

# Custom environment variables
client = MCPChromeClient(
    env={"CUSTOM_VAR": "value"}
)
```

## Available Methods

### Window and Tab Management

```python
# Get all open windows and tabs
result = client.get_windows_and_tabs()

# Navigate to a URL
result = client.chrome_navigate(url="https://example.com")

# Refresh current page
result = client.chrome_navigate(refresh=True)

# Open URL in new window
result = client.chrome_navigate(url="https://example.com", new_window=True)

# Close tabs
result = client.chrome_close_tabs(tab_ids=[123, 456])
result = client.chrome_close_tabs(url="https://example.com")

# Navigate back/forward
result = client.chrome_go_back_or_forward(is_forward=False)  # Go back
result = client.chrome_go_back_or_forward(is_forward=True)   # Go forward
```

### Page Content and Screenshots

```python
# Get text content from current page
result = client.chrome_get_web_content(text_content=True)

# Get HTML content
result = client.chrome_get_web_content(html_content=True)

# Get content from specific element
result = client.chrome_get_web_content(selector="#main-content")

# Take screenshot of current page
result = client.chrome_screenshot(
    name="my_screenshot",
    full_page=True,
    save_png=True
)

# Take screenshot of specific element
result = client.chrome_screenshot(
    name="element_screenshot",
    selector="#target-element",
    save_png=True
)

# Get screenshot as base64
result = client.chrome_screenshot(
    save_png=False,
    store_base64=True
)
```

### Element Interaction

```python
# Click element by CSS selector
result = client.chrome_click_element(selector="button.submit")

# Click at specific coordinates
result = client.chrome_click_element(
    coordinates={"x": 100, "y": 200}
)

# Click and wait for navigation
result = client.chrome_click_element(
    selector="a.link",
    wait_for_navigation=True
)

# Fill form field
result = client.chrome_fill_or_select(
    selector="input[name='username']",
    value="myusername"
)

# Get interactive elements
result = client.chrome_get_interactive_elements()

# Filter by selector
result = client.chrome_get_interactive_elements(selector="button")

# Search by text
result = client.chrome_get_interactive_elements(text_query="Submit")

# Keyboard input
result = client.chrome_keyboard(keys="Enter")
result = client.chrome_keyboard(keys="Ctrl+C")
result = client.chrome_keyboard(keys="H,e,l,l,o")  # Type sequence
```

### Network Requests

```python
# Send GET request with browser context
result = client.chrome_network_request(url="https://api.example.com/data")

# Send POST request
result = client.chrome_network_request(
    url="https://api.example.com/submit",
    method="POST",
    headers={"Content-Type": "application/json"},
    body='{"key": "value"}'
)

# Capture network traffic (with response bodies)
result = client.chrome_network_debugger_start()
# ... perform actions ...
result = client.chrome_network_debugger_stop()

# Capture network traffic (without response bodies)
result = client.chrome_network_capture_start()
# ... perform actions ...
result = client.chrome_network_capture_stop()
```

### History and Bookmarks

```python
# Search browser history
result = client.chrome_history(
    text="github",
    max_results=10
)

# Search with time range
result = client.chrome_history(
    text="python",
    start_time="1 week ago",
    end_time="now",
    max_results=20
)

# Exclude currently open tabs
result = client.chrome_history(
    exclude_current_tabs=True
)

# Search bookmarks
result = client.chrome_bookmark_search(query="python")

# Search in specific folder
result = client.chrome_bookmark_search(
    query="tutorial",
    folder_path="Work/Projects"
)

# Add bookmark
result = client.chrome_bookmark_add(
    url="https://example.com",
    title="Example Site"
)

# Delete bookmark
result = client.chrome_bookmark_delete(bookmark_id="123")
result = client.chrome_bookmark_delete(url="https://example.com")
```

### Console and Debugging

```python
# Get console messages from current page
result = client.chrome_console()

# Get console with options
result = client.chrome_console(
    max_messages=50,
    include_exceptions=True
)

# Navigate to URL and capture console
result = client.chrome_console(url="https://example.com")
```

### Advanced Features

```python
# Search in currently open tabs
result = client.search_tabs_content(query="machine learning")

# Inject custom JavaScript
result = client.chrome_inject_script(
    js_script="console.log('Hello from injected script');",
    script_type="ISOLATED"  # or "MAIN"
)

# Send command to injected script
result = client.chrome_send_command_to_inject_script(
    event_name="customEvent",
    payload='{"action": "update", "value": 42}'
)
```

## Response Format

All methods return a dictionary with the following structure:

```python
{
    "status": "success" | "error",
    "result": {
        "content": [...],  # The actual response data
        "isError": false
    }
}
```

In case of errors:
```python
{
    "status": "error",
    "message": "Error description"
}
```

## Example: Complete Workflow

```python
from helper.ChromeMcpClient import MCPChromeClient
import json

def scrape_website():
    client = MCPChromeClient()

    try:
        # 1. Navigate to website
        client.chrome_navigate(url="https://example.com")

        # 2. Get page content
        content_result = client.chrome_get_web_content(text_content=True)
        print("Page content:", content_result)

        # 3. Find interactive elements
        elements = client.chrome_get_interactive_elements(text_query="Search")
        print("Interactive elements:", json.dumps(elements, indent=2))

        # 4. Click on search button
        client.chrome_click_element(selector="button#search")

        # 5. Fill search field
        client.chrome_fill_or_select(
            selector="input[name='q']",
            value="Python programming"
        )

        # 6. Submit search
        client.chrome_keyboard(keys="Enter")

        # 7. Take screenshot of results
        client.chrome_screenshot(
            name="search_results",
            full_page=True
        )

        # 8. Get search results
        results = client.chrome_get_web_content(text_content=True)
        return results

    finally:
        client.close()

if __name__ == "__main__":
    results = scrape_website()
    print("Search results:", results)
```

## Notes

- The client automatically starts and manages the Chrome MCP server subprocess
- Always call `client.close()` when done to properly clean up resources
- Use a try/finally block to ensure the client is closed even if errors occur
- The Chrome MCP server must be installed and accessible at the configured path
- The client communicates with the server via JSON-RPC over STDIO
