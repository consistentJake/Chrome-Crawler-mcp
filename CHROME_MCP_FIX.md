# Chrome MCP Client - Empty Content Bug Fix

## Problem

When running `python test/ChromeMcpClient_test.py`, all downloaded page contents were empty (0 bytes) for text and HTML content.

## Root Cause

The Chrome MCP server returns **nested JSON responses** that require **double parsing**:

```
MCP Response Structure:
result.content[0].text (JSON string #1)
  ↓ parse
  {status, message, data}
    ↓
    data.content[0].text (JSON string #2)
      ↓ parse
      {success, textContent, htmlContent, ...}
```

The test was only parsing the first layer of JSON, not reaching the actual content.

## Solution

Updated the test file to parse JSON **twice** to reach the actual content:

### Before (incorrect):
```python
text_data = json.loads(content_list[0].get("text", "{}"))
text_content = text_data.get("textContent", "")  # textContent was not at this level!
```

### After (correct):
```python
# First parse: get outer wrapper
outer_data = json.loads(content_list[0].get("text", "{}"))
# Second parse: get actual content
inner_text = outer_data.get("data", {}).get("content", [{}])[0].get("text", "{}")
inner_data = json.loads(inner_text)
# Now get the actual content
text_content = inner_data.get("textContent", "")
```

## Changes Made

Fixed three test cases in `test/ChromeMcpClient_test.py`:

1. **Test 1: Get text content** - Now correctly extracts text content
2. **Test 2: Get HTML content** - Now correctly extracts HTML content
3. **Test 3: Get selector content** - Now correctly extracts content with added error handling

Added error handling for selectors that don't find any elements.

## Results

After the fix:
- Text content: **5.7KB** (was 0B)
- HTML content: **68KB** (was 0B)
- Selector content: **50B** (was 0B)

The content is now being successfully extracted and saved to files.

## Note on Test 4 (JavaScript Injection)

Test 4 (JavaScript injection via `browser_evaluate`) still returns minimal results because `chrome_inject_script` is designed to inject scripts, not evaluate and return results. This would require using a different Chrome MCP API or implementation approach.
