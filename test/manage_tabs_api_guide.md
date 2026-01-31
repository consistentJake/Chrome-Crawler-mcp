# BrowserIntegration.manage_tabs() API Guide

## Overview

The `manage_tabs()` method provides a unified interface for managing browser tabs across both Chrome MCP and Playwright MCP clients. This method was added to fix the `'BrowserIntegration' object has no attribute 'manage_tabs'` error.

## Method Signature

```python
def manage_tabs(self, action: str, index: Optional[int] = None) -> Dict:
    """
    Manage browser tabs (list, create, close, or select).

    Args:
        action: Action to perform - "list", "new", "close", or "select"
        index: Tab index for close/select operations (0-based)

    Returns:
        Result dictionary with status and action-specific data
    """
```

## Supported Actions

### 1. List All Tabs (`action="list"`)

Lists all open browser tabs with their index, title, and URL.

**Example:**

```python
result = browser.manage_tabs(action="list")

# Response:
{
    "success": True,
    "action": "list",
    "tabs": [
        {
            "index": 0,
            "title": "Example Domain",
            "url": "https://example.com/"
        },
        {
            "index": 1,
            "title": "Google",
            "url": "https://google.com/"
        }
    ],
    "current_index": 0,
    "total_tabs": 2,
    "message": "Found 2 tab(s). Current tab index: 0"
}
```

### 2. Create New Tab (`action="new"`)

Creates a new blank browser tab.

**Example:**

```python
result = browser.manage_tabs(action="new")

# Response:
{
    "success": True,
    "action": "new",
    "message": "New tab created successfully"
}
```

### 3. Close Tab (`action="close"`)

Closes a specific tab by its index.

**Example:**

```python
result = browser.manage_tabs(action="close", index=1)

# Response:
{
    "success": True,
    "action": "close",
    "closed_index": 1,
    "message": "Tab at index 1 closed successfully"
}
```

### 4. Select Tab (`action="select"`)

Switches to a specific tab by its index.

**Example:**

```python
result = browser.manage_tabs(action="select", index=0)

# Response:
{
    "success": True,
    "action": "select",
    "selected_index": 0,
    "message": "Switched to tab at index 0"
}
```

## Complete Example: Close All Tabs Matching URL Pattern

Here's a complete example showing how to close all tabs matching a URL pattern (e.g., "1point3acres.com"):

```python
from browser_integration import BrowserIntegration

# Initialize browser
browser = BrowserIntegration(client_type="chrome")

# Step 1: List all tabs
list_result = browser.manage_tabs(action="list")

if list_result["success"]:
    tabs = list_result["tabs"]
    
    # Step 2: Filter tabs by URL pattern
    matching_tabs = [tab for tab in tabs if "1point3acres.com" in tab["url"]]
    
    # Step 3: Close matching tabs (reverse order to avoid index shifting)
    for tab in sorted(matching_tabs, key=lambda t: t["index"], reverse=True):
        close_result = browser.manage_tabs(action="close", index=tab["index"])
        
        if close_result["success"]:
            print(f"✅ Closed tab {tab['index']}: {tab['title'][:50]}")
        else:
            print(f"❌ Failed to close tab {tab['index']}: {close_result['error']}")
```

## Demo Script

A complete demonstration script is available at:

```bash
python test/cleanup_tabs_demo.py
```

This script demonstrates:
- Listing all open tabs
- Filtering tabs by URL pattern
- Closing matching tabs in the correct order
- Proper error handling and logging

## Important Notes

### Tab Index Shifting

When closing multiple tabs, **always close from highest index to lowest** to prevent index shifting issues:

```python
# ✅ Correct: close from highest to lowest
for tab in sorted(tabs_to_close, key=lambda t: t["index"], reverse=True):
    browser.manage_tabs(action="close", index=tab["index"])

# ❌ Wrong: closing from lowest to highest causes indices to shift
for tab in sorted(tabs_to_close, key=lambda t: t["index"]):
    browser.manage_tabs(action="close", index=tab["index"])  # Indices become invalid!
```

### Error Handling

Always check the `success` field in the response:

```python
result = browser.manage_tabs(action="close", index=5)

if result["success"]:
    print("Tab closed successfully")
else:
    print(f"Error: {result.get('error', 'Unknown error')}")
```

### Cross-Client Compatibility

The `manage_tabs()` method works with both Chrome MCP and Playwright MCP clients. The implementation automatically handles the response format differences between the two clients.

## Usage in Workflows

The method is used in `workflows/onepoint3acres_workflow.py` for automatic cleanup:

```python
try:
    # ... workflow execution ...
finally:
    # Cleanup: close all tabs related to 1point3acres.com
    tabs_result = self.browser.manage_tabs(action="list")
    
    if tabs_result["success"]:
        tabs_to_close = [tab for tab in tabs_result["tabs"] 
                        if "1point3acres.com" in tab["url"]]
        
        for tab in sorted(tabs_to_close, key=lambda t: t["index"], reverse=True):
            self.browser.manage_tabs(action="close", index=tab["index"])
```

## API Implementation Details

### Internal Flow

1. Calls underlying MCP client's `browser_tabs()` method
2. Parses the MCP response format (handles nested content structure)
3. Extracts tab information from markdown-formatted text
4. Returns a normalized, easy-to-use dictionary

### Response Parsing

The method parses markdown-formatted responses like:

```
### Open tabs
- 0: (current) [Example Domain] (https://example.com/)
- 1: [Google] (https://google.com/)
```

And converts them to structured data:

```python
{
    "tabs": [
        {"index": 0, "title": "Example Domain", "url": "https://example.com/"},
        {"index": 1, "title": "Google", "url": "https://google.com/"}
    ]
}
```

## Troubleshooting

### Error: "Action requires an 'index' parameter"

**Cause:** Using `close` or `select` action without providing the `index` parameter.

**Solution:**

```python
# ❌ Wrong
browser.manage_tabs(action="close")

# ✅ Correct
browser.manage_tabs(action="close", index=1)
```

### Error: "Failed to list tabs"

**Cause:** The underlying MCP client might not be properly initialized.

**Solution:** Check that the browser is initialized correctly:

```python
browser = BrowserIntegration(client_type="chrome")
# Make sure to navigate to a page first
result = browser.playwright_client.browser_navigate("https://example.com")
```

## See Also

- [Browser Integration Documentation](browser_integration.md)
- [Workflow Development Guide](workflow_development.md)
- [Chrome MCP Documentation](chrome_mcp.md)
