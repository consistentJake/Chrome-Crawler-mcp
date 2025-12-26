# Web Extraction MCP - Usage Guide

## Overview

The Web Extraction MCP is a Model Context Protocol server that enables Claude Code to intelligently understand web pages through HTML sanitization instead of browser snapshots. This dramatically improves context efficiency and enables more reliable web automation.

## Architecture

```
Claude Code
    ├── Playwright MCP (browser interaction)
    └── Web Extraction MCP (page understanding)
            ├── Browser Integration
            ├── HTML Sanitizer
            ├── Transaction Manager
            └── Query Engine
```

## Installation

### 1. Install Dependencies

```bash
pip install beautifulsoup4 mcp
```

### 2. Configure Claude Code

Add to your Claude Code MCP configuration (usually in `~/.config/claude-code/mcp.json` or similar):

```json
{
    "mcpServers": {
        "playwright": {
            "command": "npx",
            "args": ["@playwright/mcp@latest", "--extension"]
        },
        "web-extraction": {
            "command": "python",
            "args": ["/home/zhenkai/personal/Projects/WebAgent/web_extraction_mcp.py"],
            "env": {
                "DATA_DIR": "/home/zhenkai/personal/Projects/WebAgent/data"
            }
        }
    }
}
```

### 3. Verify Installation

```bash
python test_web_extraction_mcp.py
```

## Usage

### Basic Workflow

#### Step 1: Navigate to Page (Playwright MCP)

```python
# Claude uses Playwright MCP to navigate
browser_navigate("https://www.1point3acres.com/bbs/tag/openai-9407-1.html")
```

#### Step 2: Extract and Sanitize Page (Web Extraction MCP)

```python
# Extract the current page
extract_page(
    extraction_mode="links",  # 'links', 'forms', 'content', 'all'
    max_tokens=4000
)

# Returns:
{
    "transaction_id": "txn_20251225_123456",
    "url": "https://www.1point3acres.com/bbs/tag/openai-9407-1.html",
    "title": "OpenAI - 一亩三分地",
    "statistics": {
        "total_elements": 245,
        "estimated_tokens": 3500,
        "element_types": {"a": 120, "button": 25}
    },
    "storage_path": "/data/txn_20251225_123456/",
    "preview": {
        "indexed_text": "[0] <a href=\"thread-12345-1-1.html\">Post Title 1</a>\n[1] <a href=\"thread-67890-1-1.html\">Post Title 2</a>\n..."
    }
}
```

#### Step 3: Query Elements

```python
# Natural language query
query_page_elements(
    transaction_id="txn_20251225_123456",
    query="Find all forum post links"
)

# Returns:
{
    "matches": [
        {
            "index": 5,
            "element_id": "elem-5",
            "tag": "a",
            "text": "How to use Playwright MCP",
            "attributes": {
                "href": "thread-12345-1-1.html",
                "class": ["post-link"]
            },
            "locators": {
                "data_id": "[data-element-id='elem-5']",
                "xpath": "//div[@class='post-list']/a[6]",
                "href": "a[href='thread-12345-1-1.html']"
            }
        }
    ],
    "count": 15
}
```

#### Step 4: Interact with Page (Playwright MCP)

```python
# Use locator from query to click on actual page
browser_click(
    element="Forum post link",
    ref="a[href='thread-12345-1-1.html']"
)
```

### Advanced Queries

#### Structured Filters

```python
query_page_elements(
    transaction_id="txn_20251225_123456",
    filters={
        "tag": "a",
        "href_pattern": "thread-*",
        "text_contains": "Playwright"
    },
    limit=10
)
```

#### Get Sanitized HTML

```python
get_sanitized_html(
    transaction_id="txn_20251225_123456",
    format="indexed_text"  # 'html', 'indexed_text', 'elements_only'
)
```

#### List Transactions

```python
list_transactions(limit=10, offset=0)
```

## Extraction Modes

### `links` (Default)
- Extracts all `<a>` elements
- Best for: Navigation, scraping links, finding forum posts
- Token efficient

### `forms`
- Extracts form controls: `<input>`, `<button>`, `<select>`, `<textarea>`
- Best for: Form filling, login automation
- Moderate token usage

### `content`
- Extracts headings: `<h1>` through `<h6>`
- Best for: Content analysis, article extraction
- Low token usage

### `all`
- Extracts all interactive and content elements
- Best for: Complete page understanding
- Highest token usage

## Query Capabilities

### Natural Language Queries

The query engine understands common intents:

- **Navigation**: "Find the next page button", "Get pagination links"
- **Forum Posts**: "Find all forum post links", "Get thread links"
- **Products**: "Find all product links", "Get items to buy"
- **Forms**: "Find login button", "Get submit button"

### Structured Filters

Available filter options:

- `tag`: Element tag name (e.g., "a", "button")
- `href_pattern`: Pattern for href attribute (supports `*` wildcards)
- `text_contains`: Text content contains string
- `text_matches`: Text matches regex pattern
- `class_contains`: Class attribute contains string
- `id_equals`: ID attribute equals value
- `attribute_exists`: Check if attribute exists

### Pattern Matching

Supports wildcards and regex:

```python
# Wildcard
"href_pattern": "thread-*-1-1.html"

# Regex
"href_pattern": "regex:thread-\\d+-1-1\\.html"
```

## File Storage

Transactions are stored in the data directory:

```
data/
├── txn_20251225_123456/
│   ├── metadata.json          # Transaction metadata
│   ├── raw.html               # Original HTML (if include_raw=True)
│   ├── sanitized.html         # Sanitized HTML
│   ├── elements.json          # Element registry
│   └── indexed_text.txt       # Indexed text format
└── transactions.index         # Index of all transactions
```

## Benefits

1. **Context Efficiency**: ~75% reduction in tokens vs browser snapshots
2. **Better Understanding**: Indexed text optimized for LLM comprehension
3. **Reliable Targeting**: Multiple locator strategies for robust element selection
4. **Transaction History**: Saved extractions enable debugging and replay
5. **Separation of Concerns**: Playwright handles interaction, Web Extraction handles understanding

## Real-World Examples

### Example 1: Forum Post Scraping

```python
# Navigate to forum
browser_navigate("https://www.1point3acres.com/bbs/tag/openai-9407-1.html")

# Extract page
result = extract_page(extraction_mode="links")

# Find all forum posts
posts = query_page_elements(
    transaction_id=result["transaction_id"],
    filters={"tag": "a", "href_pattern": "thread-*-1-1.html"}
)

# Click on first post
browser_click(
    element="Forum post",
    ref=posts["matches"][0]["locators"]["href"]
)
```

### Example 2: Multi-Page Navigation

```python
page = 1
while page <= 10:
    # Extract current page
    result = extract_page(extraction_mode="links")

    # Find posts on this page
    posts = query_page_elements(
        transaction_id=result["transaction_id"],
        query="Find all forum post links"
    )

    # Process posts...

    # Find next page button
    next_button = query_page_elements(
        transaction_id=result["transaction_id"],
        query="Find the next page button"
    )

    # Click next
    if next_button["count"] > 0:
        browser_click(
            element="Next page",
            ref=next_button["matches"][0]["locators"]["href"]
        )
        page += 1
    else:
        break
```

### Example 3: Form Filling

```python
# Navigate to login page
browser_navigate("https://example.com/login")

# Extract form
result = extract_page(extraction_mode="forms")

# Find username field
username_field = query_page_elements(
    transaction_id=result["transaction_id"],
    filters={"tag": "input", "attribute_exists": "name", "text_contains": "username"}
)

# Fill username
browser_type(
    element="Username field",
    ref=username_field["matches"][0]["locators"]["data_id"],
    text="myusername"
)
```

## Troubleshooting

### Error: "Failed to get page HTML"

**Cause**: Browser integration cannot connect to Playwright MCP

**Solution**:
1. Ensure Playwright MCP is running
2. Check that browser has navigated to a page
3. Verify PLAYWRIGHT_MCP_EXTENSION_TOKEN is set correctly

### Error: "Transaction not found"

**Cause**: Transaction ID doesn't exist

**Solution**:
1. Use `list_transactions()` to see available transactions
2. Ensure you're using the correct transaction ID from `extract_page()` response

### Warning: "Token limit exceeded"

**Cause**: Page is too large for specified `max_tokens`

**Solution**:
1. Increase `max_tokens` parameter
2. Use more specific `extraction_mode` (e.g., "links" instead of "all")
3. Filter elements after extraction

## Performance Tips

1. **Use specific extraction modes**: Don't use "all" if you only need links
2. **Set appropriate token limits**: Balance between completeness and efficiency
3. **Reuse transactions**: Query the same extraction multiple times instead of re-extracting
4. **Clean up old transactions**: Delete transactions you no longer need

## API Reference

See `web_extraction_mcp_design.md` for complete API documentation.

## Testing

Run the test suite:

```bash
python test_web_extraction_mcp.py
```

This will test:
- Transaction management
- HTML sanitization
- Query engine
- Browser integration
- Complete workflow

## Support

For issues or questions:
1. Check the design document: `web_extraction_mcp_design.md`
2. Review test examples: `test_web_extraction_mcp.py`
3. Inspect transaction data in `data/` directory
