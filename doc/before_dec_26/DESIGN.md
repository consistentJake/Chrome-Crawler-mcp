# Interactive Web Agent MCP - Design Document

## Overview

An integrated MCP server that combines browser automation with intelligent HTML extraction, designed for agentic workflows. Agents can navigate websites, understand page content through sanitized HTML, and interact with elements using assigned IDs.

## Core Design Principles

### 1. Interactable Elements Only

**Problem**: Current implementation assigns IDs to all tracked elements (links, headers, etc.), creating noise.

**Solution**: Only assign `data-web-agent-id` to truly interactable elements:
- Links with href: `<a href="...">`
- Buttons: `<button>`, `<input type="submit/button/reset">`
- Form inputs: `<input>`, `<textarea>`, `<select>`
- Elements with explicit interaction handlers: `onclick`, `role="button"`, `role="link"`

### 2. Single Integrated MCP

**Problem**: Current architecture requires agents to use both Web Extraction MCP and Playwright MCP separately.

**Solution**: New `InteractiveWebAgentMCP` that:
- Wraps Playwright MCP client internally
- Provides high-level tools for navigation, extraction, querying, and interaction
- Manages browser state automatically
- No need for agents to interact with Playwright MCP directly

### 3. Agent-Guided Workflow

**Problem**: Tool descriptions don't clearly guide agents on the workflow.

**Solution**: Each tool has:
- Clear description of purpose
- When to use it in the workflow sequence
- Expected inputs and outputs
- Usage examples in description

**Typical Agent Workflow**:
```
1. navigate(url) → Navigate to target page
2. get_page_content() → Get sanitized HTML with indexed interactable elements
3. query_elements(query) → Find specific elements (e.g., "Find the 3rd page button")
4. click_element(element_id) → Click on element by its ID
5. get_page_content() → Get new page content after interaction
6. download_page() → Save current page content
```

## Architecture

```
┌─────────────────────────────────────────────┐
│   Interactive Web Agent MCP Server          │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │        MCP Tools Layer              │   │
│  │  - navigate                         │   │
│  │  - get_page_content                 │   │
│  │  - query_elements                   │   │
│  │  - find_by_text                     │   │
│  │  - click_element                    │   │
│  │  - type_into_element                │   │
│  │  - download_page                    │   │
│  │  - get_current_url                  │   │
│  └─────────────────────────────────────┘   │
│               ↓           ↓                 │
│    ┌──────────────┐  ┌──────────────┐      │
│    │ HTML         │  │ Query        │      │
│    │ Sanitizer    │  │ Engine       │      │
│    └──────────────┘  └──────────────┘      │
│               ↓                             │
│    ┌──────────────────────────────┐        │
│    │   Browser Integration        │        │
│    │   (Playwright MCP Client)    │        │
│    └──────────────────────────────┘        │
│                                             │
└─────────────────────────────────────────────┘
                   ↓
        ┌─────────────────────┐
        │  Playwright MCP     │
        │  (External Process) │
        └─────────────────────┘
```

## Tool Specifications

### 1. navigate

**Purpose**: Navigate to a URL and wait for page load.

**Parameters**:
- `url` (string, required): The URL to navigate to
- `wait_seconds` (float, optional, default=2.0): Time to wait after navigation

**Returns**:
```json
{
  "success": true,
  "url": "https://...",
  "title": "Page Title"
}
```

**Usage**: First step in any web interaction workflow.

---

### 2. get_page_content

**Purpose**: Extract and return sanitized HTML with indexed interactable elements. Use this IMMEDIATELY after navigation or interaction to understand what elements are available on the page.

**Parameters**:
- `format` (enum, optional, default="indexed"): Output format
  - `indexed`: Numbered list of interactable elements
  - `full_html`: Complete sanitized HTML
  - `elements_json`: JSON array of element objects

**Returns**:
```json
{
  "url": "https://...",
  "title": "Page Title",
  "format": "indexed",
  "content": "[0] <a href=\"...\">Link Text</a>\n[1] <button>Click Me</button>...",
  "element_count": 42,
  "element_types": {
    "a": 30,
    "button": 10,
    "input": 2
  }
}
```

**Usage**: Call this after every navigation or interaction to see available elements. The agent should read this content to understand what elements can be interacted with.

---

### 3. query_elements

**Purpose**: Query interactable elements using natural language or structured filters. Use this to find specific elements from the page content.

**Parameters**:
- `query` (string, optional): Natural language query
  - Examples: "Find the next page button", "Find all forum post links", "Find the login button"
- `filters` (object, optional): Structured filters
  - `tag`: Element tag name (a, button, input)
  - `href_pattern`: Pattern for href attribute (supports wildcards: `thread-*`)
  - `text_contains`: Text content contains string
  - `text_matches`: Text matches regex
  - `id_range`: Filter by element index range `[min, max]`
- `limit` (integer, optional): Maximum results to return

**Returns**:
```json
{
  "matches": [
    {
      "web_agent_id": "wa-15",
      "index": 15,
      "tag": "a",
      "text": "Next Page",
      "attributes": {
        "href": "/page/2",
        "class": ["pagination-next"]
      }
    }
  ],
  "count": 1
}
```

**Usage**: After getting page content, use this to find specific elements before interacting.

**Examples**:
- Find pagination: `query_elements(query="Find the 3rd page button")`
- Find posts: `query_elements(filters={"tag": "a", "href_pattern": "thread-*"})`
- Find by text: `query_elements(query="Find link with text 'OAI 面试挂经'")`

---

### 4. find_by_text

**Purpose**: Find interactable elements by exact or partial text match.

**Parameters**:
- `text` (string, required): Text to search for
- `exact` (boolean, optional, default=false): Whether to match exactly

**Returns**:
```json
{
  "matches": [
    {
      "web_agent_id": "wa-23",
      "index": 23,
      "tag": "a",
      "text": "OAI 面试挂经",
      "attributes": {"href": "thread-1155609-1-1.html"}
    }
  ],
  "count": 1
}
```

**Usage**: Quick way to find elements by their visible text.

---

### 5. click_element

**Purpose**: Click on an interactable element by its web_agent_id. Use this after finding an element via query_elements or find_by_text.

**Parameters**:
- `web_agent_id` (string, required): The element ID from query results (e.g., "wa-15")
- `wait_after` (float, optional, default=1.0): Seconds to wait after clicking

**Returns**:
```json
{
  "success": true,
  "web_agent_id": "wa-15",
  "action": "clicked",
  "new_url": "https://..."
}
```

**Usage**: After finding the element you want to interact with, use its web_agent_id to click it.

**Workflow Example**:
```
1. results = query_elements(query="Find the 3rd page button")
2. element_id = results['matches'][0]['web_agent_id']  # Get "wa-15"
3. click_element(web_agent_id="wa-15")
4. get_page_content()  # Get new page content
```

---

### 6. type_into_element

**Purpose**: Type text into an input element.

**Parameters**:
- `web_agent_id` (string, required): The element ID from query results
- `text` (string, required): Text to type
- `submit` (boolean, optional, default=false): Press Enter after typing

**Returns**:
```json
{
  "success": true,
  "web_agent_id": "wa-5",
  "action": "typed",
  "text_length": 15
}
```

---

### 7. download_page

**Purpose**: Download and save the current page HTML content. Use this as the final step to capture page content.

**Parameters**:
- `filename` (string, optional): Filename to save (auto-generated if omitted)
- `include_metadata` (boolean, optional, default=true): Include metadata in download

**Returns**:
```json
{
  "success": true,
  "url": "https://...",
  "title": "Page Title",
  "filepath": "/path/to/downloads/page_20241226_143022.html",
  "size_bytes": 45678
}
```

**Usage**: Final step to save the page content after navigating to target.

---

### 8. get_current_url

**Purpose**: Get the current browser URL.

**Returns**:
```json
{
  "url": "https://www.1point3acres.com/bbs/thread-1155609-1-1.html",
  "title": "Page Title"
}
```

---

### 9. wait_for_page

**Purpose**: Wait for page to load or specific content to appear.

**Parameters**:
- `seconds` (float, optional): Time to wait
- `text_to_appear` (string, optional): Wait for specific text to appear

**Returns**:
```json
{
  "success": true,
  "waited_seconds": 2.0
}
```

## Element ID Assignment Strategy

### Interactable Element Criteria

An element gets a `data-web-agent-id` if it matches ANY of these criteria:

1. **Links**: `<a>` with `href` attribute (excluding `javascript:`, `#`, `mailto:`)
2. **Buttons**:
   - `<button>` elements
   - `<input type="submit">`, `<input type="button">`, `<input type="reset">`
3. **Form Inputs**:
   - `<input>` (text, password, email, search, tel, url, number, etc.)
   - `<textarea>`
   - `<select>`
4. **Custom Interactive Elements**:
   - Elements with `onclick` attribute
   - Elements with `role="button"` or `role="link"`
   - Elements with `tabindex >= 0`

### ID Format

- Pattern: `wa-{counter}` where counter is a sequential number
- Example: `wa-0`, `wa-1`, `wa-2`, ...
- Stored in `data-web-agent-id` attribute

### Visibility Filtering

Elements are excluded if:
- `display: none` or `visibility: hidden`
- `hidden` attribute present
- Class contains: `hidden`, `invisible`, `sr-only`, `visually-hidden`
- Width or height is 0

## Implementation Changes

### html_sanitizer.py Changes

1. Update `INTERACTIVE_ELEMENTS` to only include truly interactable elements
2. Modify `_build_element_registry()` to check if element is interactable
3. Add `_is_interactable_element()` method with criteria above
4. Change `data-element-id` to `data-web-agent-id`
5. Update element info to include `web_agent_id` field

### New File: interactive_web_agent_mcp.py

1. Combines all functionality into one MCP server
2. Internal BrowserIntegration instance for Playwright control
3. Internal HTMLSanitizer for page extraction
4. Internal QueryEngine for element querying
5. Session state management (current page elements, URL, etc.)
6. All tools as specified above

### File Structure

```
WebAgent/
├── html_sanitizer.py              # Updated to only track interactable elements
├── interactive_web_agent_mcp.py   # NEW: Integrated MCP server
├── browser_integration.py         # Reused as-is
├── query_engine.py               # Reused as-is
├── eval/
│   ├── __init__.py              # NEW
│   └── test_forum_navigation.py # NEW: Evaluation task
└── downloads/                    # NEW: For downloaded pages
```

## Evaluation Task Specification

### Task: Forum Post Navigation and Download

**Objective**: Navigate to a forum page, find a specific post, and download it.

**Steps**:
1. Navigate to `https://www.1point3acres.com/bbs/tag/openai-9407-1.html`
2. Query for pagination buttons
3. Find the 3rd page button
4. Query for post links
5. Find post with title containing "OAI 面试挂经"
6. Click on the post
7. Download the page
8. Verify final URL is `https://www.1point3acres.com/bbs/thread-1155609-1-1.html`

**Success Criteria**:
- All steps complete without errors
- Final URL matches expected URL
- Downloaded file exists and contains post content

### Evaluation Code Structure

```python
class ForumNavigationEval:
    def __init__(self, mcp_client):
        self.client = mcp_client

    def run(self):
        # Step 1: Navigate
        # Step 2-7: Execute workflow
        # Step 8: Validate
        return success, details
```

## Agent Workflow Example

Here's how an agent would use this MCP:

```
User: "Go to the OpenAI forum page and download the post titled 'OAI 面试挂经'"

Agent thoughts and actions:

1. First, I need to navigate to the forum page
   Action: navigate(url="https://www.1point3acres.com/bbs/tag/openai-9407-1.html")

2. Now I need to see what's on the page
   Action: get_page_content(format="indexed")
   Result: [Shows indexed list of 50+ elements]

3. I need to find the post titled "OAI 面试挂经"
   Action: find_by_text(text="OAI 面试挂经", exact=False)
   Result: {
     "matches": [
       {
         "web_agent_id": "wa-23",
         "tag": "a",
         "text": "OAI 面试挂经",
         "attributes": {"href": "thread-1155609-1-1.html"}
       }
     ]
   }

4. Found it! Now I'll click on element wa-23
   Action: click_element(web_agent_id="wa-23")

5. Wait for page to load
   Action: wait_for_page(seconds=2)

6. Download the post page
   Action: download_page()
   Result: {
     "success": true,
     "url": "https://www.1point3acres.com/bbs/thread-1155609-1-1.html",
     "filepath": "/downloads/page_20241226_143022.html"
   }

Done! Downloaded the post successfully.
```

## Benefits of This Design

1. **Self-Contained**: Agents only need to interact with one MCP
2. **Clear Workflow**: Tool descriptions guide agents through proper usage
3. **Reduced Noise**: Only interactable elements get IDs, making content easier to parse
4. **Reliable Targeting**: Elements tracked via data-web-agent-id attributes
5. **Testable**: Evaluation framework validates the complete workflow
6. **Scalable**: Can add more tools (scroll, hover, etc.) without changing architecture

## Next Steps

1. ✅ Design complete
2. ⏭ Update html_sanitizer.py
3. ⏭ Create interactive_web_agent_mcp.py
4. ⏭ Create evaluation task
5. ⏭ Test complete workflow
