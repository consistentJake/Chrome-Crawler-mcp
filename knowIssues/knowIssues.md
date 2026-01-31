# Known Issues - WebAgent

## Issue: type_into_element Fails on React SPAs (X.com)

### Summary
The `type_into_element` function fails to type text into search inputs on Single Page Application (SPA) sites like X.com, though it works correctly on traditional sites like Google.com. The issue stems from a DOM injection failure when targeting elements on dynamically rendered pages.

### Root Cause Analysis

**Why It Fails on X.com:**
1. **XPath Mismatch**: The HTML Sanitizer (html_sanitizer.py) generates XPaths based on BeautifulSoup's parsed HTML structure
2. **DOM Discrepancy**: On React/SPA sites, the parsed HTML structure differs from the actual browser DOM
3. **Failed Injection**: The `_inject_web_agent_ids()` function attempts to inject `data-web-agent-id` attributes using generated XPaths
4. **Zero Injections**: Debug logs show `"injection": {"total": 318, "injected": 0, "failed": 0}` - no elements receive the web_agent_id
5. **Silent Failure**: `chrome_fill_or_select` silently fails when the selector `[data-web-agent-id="wa-280"]` doesn't exist

**Evidence from Debug Session (2026-01-11):**
```json
{
  "operation": "get_page_content",
  "injection": {
    "total": 318,
    "injected": 0,
    "failed": 0
  }
}
```

### Why Google.com Works
- Google has relatively static HTML structure
- BeautifulSoup's parsed structure matches the browser DOM more closely
- XPath-based injection succeeds on traditional server-rendered pages

### Technical Details

**Current Flow:**
1. `get_page_content()` → calls `HTMLSanitizer.sanitize()`
2. Sanitizer builds element registry with XPaths from BeautifulSoup
3. `_inject_web_agent_ids()` tries to inject attributes via XPath
4. XPaths fail on React DOM → 0 injections
5. `type_into_element()` looks for `[data-web-agent-id]` selector → element not found

**Example Issue with X.com Search:**
- HTML shows: `<input data-testid="SearchBox_Search_Input" placeholder="Search" />`
- BeautifulSoup generates XPath: `//input[1]` (or similar)
- Actual browser DOM may have different element order due to React rendering
- XPath evaluation fails → injection skipped

### Suggested Solutions

#### Solution 1: Use CSS Selectors Instead of XPath (Recommended)
**Implementation:**
- Replace XPath-based injection with CSS selector approach
- Use multiple selector strategies: `data-testid`, `name`, `id`, `class`
- Build robust selectors that work with React/dynamically rendered content

**File to Modify:** `src/interactive_web_agent_mcp.py` → `_inject_web_agent_ids()`

```javascript
// Current broken approach:
document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)

// Better approach:
// 1. Try data-testid first (often stable on SPAs)
// 2. Try CSS selectors from element attributes
// 3. Fall back to direct selector injection without finding first
```

#### Solution 2: Fallback to Native Selectors
**Implementation:**
- When XPath injection fails, use native selectors directly
- Store backup selectors in element registry (data-testid, name, class, id)
- In `type_into_element()`, try multiple selector strategies

**Files to Modify:**
- `src/html_sanitizer.py` → Store additional selectors
- `src/browser_integration.py` → Implement fallback logic

#### Solution 3: Use Element Registry Attributes Directly
**Implementation:**
- Don't rely on DOM injection for SPA sites
- Store stable attribute selectors (data-testid, name, id) during registry building
- Use these pre-built selectors directly in `type_into_element()`

### Working Example from Tests
File: `test/test_type_into_element_flow.py` (lines 93-106)

This test demonstrates the **correct approach** that works:
```javascript
var el = document.querySelector('textarea[name="q"], input[name="q"]');
if (el) {
    el.setAttribute('data-web-agent-id', 'wa-test');
}
```

This uses **CSS selectors** instead of XPath and succeeds.

### Testing Notes
- ✅ **Google.com**: `type_into_element` works (traditional HTML)
- ❌ **X.com**: `type_into_element` fails (React SPA)
- **Expected Behavior**: Should work on both

### Priority
**High** - Blocks interaction with modern SPA sites (X/Twitter, React-based apps)

### Related Files
- `src/interactive_web_agent_mcp.py` - Line 808-936 (`_inject_web_agent_ids`)
- `src/html_sanitizer.py` - Line 312-329 (`_generate_xpath`)
- `src/browser_integration.py` - Line 466-523 (`type_into_element`)
- `helper/ChromeMcpClient.py` - Line 352-407 (`type_into_element`)
