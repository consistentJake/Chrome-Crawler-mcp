# Browser Integration Update - Chrome HTML Content Extraction

## Summary

Updated `browser_integration.py` to use Chrome MCP's native `get_html_content()` method instead of `browser_evaluate()` for HTML extraction when using the Chrome client.

## Changes Made

### 1. Updated `get_current_page_html()` Method

**Before:**
```python
def get_current_page_html(self) -> str:
    result = self.playwright_client.browser_evaluate(
        function="() => document.documentElement.outerHTML"
    )
    return str(self.handle_mcp_response(result))
```

**After:**
```python
def get_current_page_html(self) -> str:
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
```

### 2. Added `handle_chrome_content_response()` Method

New method to handle Chrome MCP's nested JSON response structure:

```python
def handle_chrome_content_response(self, result: dict, content_key: str) -> str:
    """
    Handle Chrome MCP response format with nested JSON.
    Chrome MCP returns a double-nested JSON structure that needs to be parsed twice.
    """
    # First parse: get outer wrapper
    outer_data = json.loads(content_list[0].get("text", "{}"))
    # Second parse: get actual content from nested JSON
    inner_text = outer_data.get("data", {}).get("content", [{}])[0].get("text", "{}")
    inner_data = json.loads(inner_text)
    # Extract the requested content
    content = inner_data.get(content_key, "")
    return content
```

## Why This Change?

1. **Uses Native Functionality**: Chrome MCP has a dedicated `chrome_get_web_content` method that's designed specifically for extracting HTML/text content
2. **More Efficient**: Avoids injecting and evaluating JavaScript when a native method exists
3. **Consistent with Best Practices**: Uses the appropriate client method for each client type
4. **Maintains Compatibility**: Playwright client continues to use `browser_evaluate` as before

## Response Structure Differences

### Chrome MCP Response (Double-Nested JSON):
```
result.content[0].text (JSON string #1)
  ↓ parse
  {status, message, data}
    ↓
    data.content[0].text (JSON string #2)
      ↓ parse
      {success, htmlContent, url, title, ...}
```

### Playwright MCP Response (Markdown Format):
```
result.content[0].text
  ↓
  "### Result\n\"<html>...</html>\""
```

## Test Results

Test with Chrome client on example.com:
- ✅ HTML retrieved: 392 characters
- ✅ Valid HTML structure with `<html>` tag
- ✅ Contains proper content

## Files Changed

- `src/browser_integration.py`: Updated `get_current_page_html()` and added `handle_chrome_content_response()`
- `test_browser_integration_html.py`: Created test to verify Chrome HTML extraction
