# Web Extraction MCP Server Design

## Overview

A Model Context Protocol (MCP) server that bridges Playwright browser automation with intelligent HTML sanitization for Claude Code. This enables Claude to understand web pages through sanitized HTML instead of browser snapshots, improving context efficiency and enabling better web automation workflows.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Claude Code                              │
└───────────────┬───────────────────────────┬─────────────────────┘
                │                           │
                │ 1. Navigate               │ 3. Query & Act
                │    to URL                 │    on Page
                ▼                           ▼
┌──────────────────────────┐  ┌─────────────────────────────────┐
│   Playwright MCP         │  │  Web Extraction MCP             │
│   - browser_navigate()   │  │  - extract_page()               │
│   - browser_click()      │  │  - get_sanitized_html()         │
│   - browser_snapshot()   │  │  - query_page_elements()        │
└────────────┬─────────────┘  └────────────┬────────────────────┘
             │                              │
             │ 2. Get current page HTML     │
             │◄─────────────────────────────┤
             │                              │
             │                              ▼
             │                    ┌──────────────────────┐
             │                    │  HTML Sanitizer      │
             │                    │  - Remove noise      │
             │                    │  - Extract elements  │
             │                    │  - Token reduction   │
             │                    └──────────┬───────────┘
             │                               │
             │                               ▼
             │                    ┌──────────────────────┐
             │                    │  Transaction Storage │
             │                    │  data/<txn_id>/      │
             │                    │    - raw.html        │
             │                    │    - sanitized.html  │
             │                    │    - elements.json   │
             │                    └──────────────────────┘
             │
             ▼
    ┌────────────────────┐
    │  Browser Instance  │
    │  (Current Page)    │
    └────────────────────┘
```

## Workflow

### 1. Page Navigation
```python
# Claude uses Playwright MCP to navigate
browser_navigate("https://example.com/forum")
```

### 2. Page Extraction
```python
# Claude calls Web Extraction MCP
extract_page(
    transaction_id="txn_12345",  # Auto-generated or provided
    extraction_mode="links"       # 'links', 'forms', 'content', 'all'
)
```

**What happens:**
- Uses PlaywrightMcpClient to get current page HTML via `browser_evaluate()`
- Downloads raw HTML
- Sanitizes HTML using `HTMLSanitizer`
- Saves to `/data/txn_12345/`:
  - `raw.html` - Original HTML
  - `sanitized.html` - Cleaned HTML
  - `elements.json` - Interactive element registry
  - `metadata.json` - Extraction metadata

### 3. Query & Understand
```python
# Claude queries the sanitized page
result = query_page_elements(
    transaction_id="txn_12345",
    query="Find the next page button"
)

# Returns:
{
    "matches": [
        {
            "element_id": "elem-42",
            "tag": "a",
            "text": "Next Page",
            "attributes": {"href": "/page/2"},
            "locators": {
                "data_id": "[data-element-id='elem-42']",
                "xpath": "//div[@class='pagination']/a[2]",
                "href": "a[href='/page/2']"
            }
        }
    ]
}
```

### 4. Interact with Page
```python
# Claude uses the locator to click on the ACTUAL browser page
browser_click(
    element="Next page button",
    ref="a[href='/page/2']"  # From query result
)
```

## MCP Server Implementation

### Tools

#### 1. `extract_page`
**Purpose:** Extract and sanitize the current browser page

**Input:**
```json
{
    "transaction_id": "optional-txn-id",  // Auto-generated if omitted
    "extraction_mode": "links",           // 'links', 'forms', 'content', 'all'
    "max_tokens": 4000,                   // Token limit for sanitization
    "include_raw": false                  // Whether to save raw HTML
}
```

**Output:**
```json
{
    "transaction_id": "txn_20251225_123456",
    "statistics": {
        "total_elements": 245,
        "estimated_tokens": 3500,
        "element_types": {"a": 120, "button": 25, "input": 15}
    },
    "storage_path": "/data/txn_20251225_123456/",
    "preview": {
        "indexed_text": "[0] <a href=\"...\">Post Title 1</a>\n[1] <a href=\"...\">Post Title 2</a>\n..."
    }
}
```

#### 2. `query_page_elements`
**Purpose:** Query elements from a previously extracted page

**Input:**
```json
{
    "transaction_id": "txn_20251225_123456",
    "query": "Find all forum post links",  // Natural language query
    "filters": {                            // Optional structured filters
        "tag": "a",
        "href_pattern": "thread-*",
        "text_contains": ""
    }
}
```

**Output:**
```json
{
    "matches": [
        {
            "index": 5,
            "element_id": "elem-5",
            "tag": "a",
            "text": "How to use Playwright MCP",
            "attributes": {
                "href": "thread-12345-1-1.html",
                "class": ["post-link", "thread-link"]
            },
            "locators": {
                "data_id": "[data-element-id='elem-5']",
                "xpath": "//div[@class='post-list']/a[6]",
                "href": "a[href='thread-12345-1-1.html']",
                "class": ".post-link.thread-link"
            }
        }
    ],
    "count": 15
}
```

#### 3. `get_sanitized_html`
**Purpose:** Retrieve sanitized HTML for a transaction

**Input:**
```json
{
    "transaction_id": "txn_20251225_123456",
    "format": "indexed_text"  // 'html', 'indexed_text', 'elements_only'
}
```

**Output:**
```json
{
    "content": "...",
    "format": "indexed_text",
    "token_count": 3500
}
```

#### 4. `list_transactions`
**Purpose:** List all stored transactions

**Output:**
```json
{
    "transactions": [
        {
            "transaction_id": "txn_20251225_123456",
            "created_at": "2025-12-25T12:34:56",
            "url": "https://example.com/forum",
            "element_count": 245
        }
    ]
}
```

## Implementation Components

### 1. MCP Server (`web_extraction_mcp.py`)
```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
import json
import asyncio

server = Server("web-extraction")

@server.tool()
async def extract_page(
    transaction_id: str | None = None,
    extraction_mode: str = "links",
    max_tokens: int = 4000,
    include_raw: bool = False
) -> dict:
    """Extract and sanitize the current browser page"""
    # Implementation
    pass
```

### 2. Transaction Manager (`transaction_manager.py`)
```python
class TransactionManager:
    """Manage transaction lifecycle and storage"""

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir

    def create_transaction(self, transaction_id: str = None) -> str:
        """Create new transaction with unique ID"""
        if transaction_id is None:
            transaction_id = self._generate_transaction_id()
        return transaction_id

    def save_html(self, transaction_id: str, raw_html: str, sanitized_html: str):
        """Save HTML files for transaction"""
        pass

    def save_elements(self, transaction_id: str, elements: list):
        """Save element registry as JSON"""
        pass

    def get_transaction(self, transaction_id: str) -> dict:
        """Retrieve transaction data"""
        pass
```

### 3. Browser Integration (`browser_integration.py`)
```python
from helper.PlaywrightMcpClient import MCPPlaywrightClient

class BrowserIntegration:
    """Integration with Playwright MCP for HTML extraction"""

    def __init__(self):
        self.playwright_client = MCPPlaywrightClient()

    def get_current_page_html(self) -> str:
        """Get HTML of current browser page"""
        result = self.playwright_client.browser_evaluate(
            function="() => document.documentElement.outerHTML"
        )
        return result['result']['content']

    def get_current_url(self) -> str:
        """Get current page URL"""
        result = self.playwright_client.browser_evaluate(
            function="() => window.location.href"
        )
        return result['result']['content']
```

### 4. Element Query Engine (`query_engine.py`)
```python
class QueryEngine:
    """Natural language and structured querying of extracted elements"""

    def query_elements(
        self,
        elements: list,
        query: str = None,
        filters: dict = None
    ) -> list:
        """Query elements using NL or structured filters"""
        # Support both natural language and structured queries
        pass

    def _match_pattern(self, element: dict, pattern: str) -> bool:
        """Pattern matching for element filtering"""
        pass
```

## File Storage Structure

```
data/
├── txn_20251225_123456/
│   ├── metadata.json          # Transaction metadata
│   ├── raw.html               # Original HTML (optional)
│   ├── sanitized.html         # Sanitized HTML
│   ├── elements.json          # Element registry
│   └── indexed_text.txt       # Indexed text format
├── txn_20251225_123457/
│   └── ...
└── transactions.index         # Index of all transactions
```

### metadata.json
```json
{
    "transaction_id": "txn_20251225_123456",
    "created_at": "2025-12-25T12:34:56.789Z",
    "url": "https://example.com/forum",
    "extraction_mode": "links",
    "max_tokens": 4000,
    "statistics": {
        "total_elements": 245,
        "estimated_tokens": 3500,
        "element_types": {"a": 120, "button": 25}
    }
}
```

## Usage Example

```python
# Complete workflow example

# Step 1: Navigate to page
browser_navigate("https://www.1point3acres.com/bbs/tag/openai-9407-1.html")

# Step 2: Extract and sanitize page
extraction_result = extract_page(
    extraction_mode="links",
    max_tokens=4000
)
# Returns: {
#   "transaction_id": "txn_20251225_123456",
#   "statistics": {...},
#   "preview": {...}
# }

# Step 3: Query for specific elements
next_button = query_page_elements(
    transaction_id="txn_20251225_123456",
    query="Find the next page button"
)
# Returns matching elements with locators

# Step 4: Click on the element using Playwright
browser_click(
    element="Next page button",
    ref=next_button['matches'][0]['locators']['href']
)

# Step 5: Extract the new page
new_extraction = extract_page(
    transaction_id="txn_20251225_123457",
    extraction_mode="links"
)
```

## Integration with Claude Code

### Configuration (`claude_desktop_config.json`)
```json
{
    "mcpServers": {
        "playwright": {
            "command": "npx",
            "args": ["@playwright/mcp@latest", "--extension"]
        },
        "web-extraction": {
            "command": "python",
            "args": ["/path/to/web_extraction_mcp.py"],
            "env": {
                "DATA_DIR": "/home/zhenkai/personal/Projects/WebAgent/data"
            }
        }
    }
}
```

### Claude Code Workflow
1. **Navigate:** Claude uses Playwright MCP to navigate to URLs
2. **Extract:** Claude calls `extract_page()` to sanitize and save HTML
3. **Analyze:** Claude reads the indexed text or queries specific elements
4. **Act:** Claude uses locators to interact with the actual page via Playwright
5. **Repeat:** For pagination or multi-page workflows

## Benefits

1. **Context Efficiency:** Sanitized HTML uses ~75% fewer tokens than browser snapshots
2. **Better Understanding:** Indexed text format is optimized for LLM comprehension
3. **Reliable Targeting:** Multiple locator strategies ensure robust element selection
4. **Transaction History:** Saved extractions enable debugging and replay
5. **Separation of Concerns:**
   - Playwright handles browser interaction
   - Web Extraction handles understanding
   - Claude orchestrates the workflow

## Implementation Priority

1. **Phase 1 (MVP):**
   - Basic MCP server structure
   - `extract_page` tool
   - Transaction storage
   - Browser integration

2. **Phase 2:**
   - `query_page_elements` with pattern matching
   - `get_sanitized_html` retrieval
   - Transaction indexing

3. **Phase 3:**
   - Natural language querying
   - Advanced pattern recognition
   - Performance optimization

## Testing Strategy

1. **Unit Tests:**
   - HTML sanitization correctness
   - Transaction storage/retrieval
   - Query engine accuracy

2. **Integration Tests:**
   - Playwright MCP integration
   - End-to-end extraction workflow
   - Multi-page navigation

3. **Real-world Tests:**
   - Forum post extraction (1point3acres)
   - E-commerce product listing
   - News article scraping

## Security Considerations

1. **HTML Sanitization:** Remove `javascript:`, `data:` URIs
2. **File Storage:** Validate transaction IDs to prevent path traversal
3. **Resource Limits:** Enforce max_tokens and file size limits
4. **Access Control:** Ensure MCP server only accesses allowed directories
