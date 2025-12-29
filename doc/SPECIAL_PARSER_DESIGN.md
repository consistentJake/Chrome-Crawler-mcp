# Special Parser Design & Architecture Review

**Date:** 2025-12-29
**Author:** Code Review & Design
**Status:** Design Phase - Pending Review

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Part 1: Code Review - Critical Issue](#part-1-code-review---critical-issue)
3. [Part 2: Special Parser Design](#part-2-special-parser-design)
4. [Implementation Plan](#implementation-plan)
5. [Testing Strategy](#testing-strategy)

---

## Executive Summary

This document addresses two key aspects of the WebAgent system:

1. **Code Review**: Identified a critical architectural issue where `data-web-agent-id` attributes used for element targeting are not properly synchronized between the sanitized HTML and the live browser DOM.

2. **Special Parser Design**: Proposes a new feature to enable URL-specific parsers (starting with X.com) that extract structured data and save results for downstream processing.

**Recommendation**: Fix the DOM synchronization issue first (Part 1), then implement the special parser feature (Part 2).

---

## Part 1: Code Review - Critical Issue

### Current Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           get_page_content()                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. browser.get_current_page_html()                                          │
│     └─ Fetches raw HTML string from live browser                             │
│                                                                              │
│  2. HTMLSanitizer.sanitize(raw_html)                                         │
│     ├─ Parses HTML with BeautifulSoup (creates Python object tree)           │
│     ├─ _build_element_registry()                                             │
│     │   ├─ Iterates all visible interactable elements                        │
│     │   └─ For each element:                                                 │
│     │       ├─ Assigns web_agent_id: "wa-0", "wa-1", ...                     │
│     │       ├─ tag['data-web-agent-id'] = web_agent_id  ← BeautifulSoup only │
│     │       └─ Builds locators (xpath, css, data_id)                         │
│     ├─ Removes scripts/styles, sanitizes attributes                          │
│     └─ Returns {sanitized_html, element_registry, statistics}                │
│                                                                              │
│  3. current_page_elements = element_registry  ← Global state update          │
│  4. Returns indexed text for LLM consumption                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
                         LLM analyzes sanitized content
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                        click_element(web_agent_id)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Lookup in current_page_elements by web_agent_id                          │
│     └─ element = find_by_id("wa-5")                                          │
│                                                                              │
│  2. Get locator from element registry                                        │
│     └─ locator = element['locators']['data_id']                              │
│        = '[data-web-agent-id="wa-5"]'                                        │
│                                                                              │
│  3. browser.click_element(css_selector=locator)                              │
│     ├─ Chrome: chrome_click_element(selector='[data-web-agent-id="wa-5"]')   │
│     └─ Playwright: document.querySelector('[data-web-agent-id="wa-5"]')     │
│                                                                              │
│  4. ❌ Element NOT FOUND in browser DOM                                      │
│     └─ data-web-agent-id only exists in Python, not in actual browser!       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Problem

**Location:** `src/html_sanitizer.py:256`

```python
def _create_element_info(self, tag: Tag) -> Optional[Dict]:
    web_agent_id = f"wa-{self._element_counter}"
    self._element_counter += 1

    # Inject data-web-agent-id for later targeting
    tag['data-web-agent-id'] = web_agent_id  # ← Only modifies BeautifulSoup object!
```

**Impact:**
- The `data-web-agent-id` attribute is injected into the BeautifulSoup object (Python memory)
- The **live browser DOM** is never modified to include these attributes
- When `click_element()` uses `[data-web-agent-id="wa-5"]` as CSS selector, **the element cannot be found**

### Evidence of Broken Flow

**File:** `src/interactive_web_agent_mcp.py:1047`

```python
async def click_element(web_agent_id: str, wait_after: float = 1.0) -> Dict:
    # Find element in registry
    element = None
    for elem in current_page_elements:
        if elem.get("web_agent_id") == web_agent_id:
            element = elem
            break

    # Use the data-web-agent-id locator to click
    locator = element['locators']['data_id']  # '[data-web-agent-id="wa-5"]'

    # This will FAIL - attribute doesn't exist in browser DOM!
    result = browser.click_element(css_selector=locator)
```

### Why It Might Appear to Work

The `_build_locators()` function creates **multiple fallback locators**:

```python
locators = {
    'data_id': '[data-web-agent-id="wa-5"]',  # ← Used, but broken
    'id': '#element-id',                       # ← If element has id
    'class': '.class1.class2',                 # ← If element has classes
    'xpath': '//div[2]/a[3]',                  # ← Generated XPath (works!)
    'href': 'a[href="/path"]',                 # ← For links
    'name': 'input[name="field"]'              # ← For inputs
}
```

However, the code **only uses `data_id`**, ignoring the working alternatives.

### Recommended Solution

**Option 1: DOM Injection (Recommended)**

Inject `data-web-agent-id` attributes into the actual browser DOM after building the registry.

```python
# src/interactive_web_agent_mcp.py

async def get_page_content(output_format: str = "indexed") -> Dict:
    browser = get_browser()
    raw_html = browser.get_current_page_html()

    # Sanitize and build registry
    sanitizer = HTMLSanitizer(max_tokens=8000)
    sanitized_result = sanitizer.sanitize(raw_html, extraction_mode="all")

    # NEW: Inject data-web-agent-id into actual browser DOM
    injection_success = await _inject_web_agent_ids(
        browser,
        sanitized_result['element_registry']
    )

    # Update global state
    current_page_elements = sanitized_result['element_registry']

    # ... rest of function


async def _inject_web_agent_ids(browser, element_registry):
    """
    Inject data-web-agent-id attributes into the actual browser DOM.

    This ensures click_element() can use [data-web-agent-id="wa-X"] selectors.
    """
    inject_js = """
    (elements) => {
        const results = {
            total: elements.length,
            injected: 0,
            failed: []
        };

        elements.forEach(el => {
            // Use XPath to find the element (most reliable)
            const xpath = el.locators.xpath;
            const xpathResult = document.evaluate(
                xpath,
                document,
                null,
                XPathResult.FIRST_ORDERED_NODE_TYPE,
                null
            );
            const element = xpathResult.singleNodeValue;

            if (element) {
                element.setAttribute('data-web-agent-id', el.web_agent_id);
                results.injected++;
            } else {
                results.failed.push({
                    web_agent_id: el.web_agent_id,
                    xpath: xpath
                });
            }
        });

        return results;
    }
    """

    result = browser.playwright_client.browser_evaluate(
        function=inject_js,
        element=json.dumps(element_registry)
    )

    # Parse result and log any failures
    logger = get_debug_logger()
    if logger:
        logger.log_operation(
            "inject_web_agent_ids",
            {"total_elements": len(element_registry)},
            result,
            0
        )

    return result.get("status") == "success"
```

**Option 2: Use XPath Locators**

Modify `click_element()` to use XPath instead of data_id:

```python
async def click_element(web_agent_id: str, wait_after: float = 1.0) -> Dict:
    # Find element in registry
    element = find_element_by_id(web_agent_id)

    # Use XPath locator (always works)
    locator = element['locators']['xpath']  # Instead of 'data_id'

    # Click using XPath
    result = browser.click_element_by_xpath(locator)
```

**Recommendation:** Implement **Option 1** for consistency with the current design, with Option 2 as a fallback if XPath lookup fails.

---

## Part 2: Special Parser Design

### Overview

A new MCP API that enables URL-specific parsers to extract structured data from web pages and save results for downstream processing.

```
User Request: "Go to x.com/search?q=gold, scroll 20 times, parse tweets"
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Claude: navigate(url="https://x.com/search?q=gold")                        │
│          scroll_down(times=20)                                               │
│          parse_page_with_special_parser()  ← NEW API                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│              parse_page_with_special_parser() Implementation                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Get current URL from browser                                             │
│     └─ url = browser.get_current_url()                                       │
│                                                                              │
│  2. Look up parser in registry                                               │
│     ├─ parser = ParserRegistry.get_parser_for_url(url)                       │
│     └─ Matches "x.com" → XComParser                                          │
│                                                                              │
│  3. Execute parser                                                           │
│     ├─ parsed_data = parser.parse(browser_client)                            │
│     └─ Uses JavaScript to extract structured data from DOM                   │
│                                                                              │
│  4. Save results to session folder                                           │
│     ├─ Path: downloads/sessions/{session_id}/parsed_results/x.com/          │
│     ├─ File: 2025-12-29_103000_gold.json                                     │
│     └─ Format: {parser, url, timestamp, item_count, items, metadata}        │
│                                                                              │
│  5. Return summary to LLM                                                    │
│     └─ {success, parser_used, item_count, file_path, summary}               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Architecture Components

#### 1. Parser Registry

**File:** `src/special_parsers/__init__.py`

```python
"""
Special Parser Registry
Maps URL patterns to specialized parsers for structured data extraction.
"""

import re
from typing import Optional
from .base import BaseParser
from .x_com import XComParser

# Parser registry with URL pattern matching
PARSER_REGISTRY = {
    "x.com": {
        "patterns": [
            r"x\.com",
            r"twitter\.com",
        ],
        "parser_class": XComParser,
        "description": "Extracts tweets with user info, text, metrics, and media",
        "supported_pages": ["search", "timeline", "profile"]
    },
    # Future parsers
    # "reddit": {
    #     "patterns": [r"reddit\.com"],
    #     "parser_class": RedditParser,
    #     "description": "Extracts posts, comments, subreddit info"
    # },
}

def get_parser_for_url(url: str) -> Optional[BaseParser]:
    """
    Match URL to appropriate parser.

    Args:
        url: Current page URL

    Returns:
        Parser instance or None if no match
    """
    for name, config in PARSER_REGISTRY.items():
        for pattern in config["patterns"]:
            if re.search(pattern, url, re.IGNORECASE):
                parser_class = config["parser_class"]
                return parser_class()
    return None

def list_available_parsers():
    """Return list of available parsers with descriptions"""
    return [
        {
            "name": name,
            "description": config["description"],
            "supported_pages": config.get("supported_pages", []),
            "patterns": config["patterns"]
        }
        for name, config in PARSER_REGISTRY.items()
    ]
```

#### 2. Base Parser Interface

**File:** `src/special_parsers/base.py`

```python
"""
Base Parser Interface
All special parsers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from datetime import datetime

class BaseParser(ABC):
    """
    Base class for all special parsers.

    Parsers extract structured data from specific websites
    using DOM manipulation and JavaScript evaluation.
    """

    name: str = "base"
    description: str = "Base parser"
    version: str = "1.0.0"

    @abstractmethod
    def parse(self, browser_client) -> Dict[str, Any]:
        """
        Extract structured data from current page.

        Args:
            browser_client: BrowserIntegration instance for DOM access

        Returns:
            {
                "parser": "x.com",
                "parser_version": "1.0.0",
                "url": "https://x.com/search?q=gold",
                "timestamp": "2025-12-29T10:30:00Z",
                "item_count": 50,
                "items": [...],  # Parsed items (structure depends on parser)
                "metadata": {...}  # Additional metadata
            }
        """
        pass

    @abstractmethod
    def get_extraction_js(self) -> str:
        """
        Return JavaScript code for DOM extraction.

        This JavaScript will be executed in the browser context
        and should return a JSON-serializable object.
        """
        pass

    def validate_page(self, browser_client) -> bool:
        """
        Validate that current page is suitable for this parser.

        Override to add custom validation logic.
        """
        return True

    def _parse_response(self, raw_response: Dict) -> Any:
        """
        Parse the raw browser_evaluate response.

        Handles different response formats from Playwright/Chrome MCP.
        Override if custom parsing is needed.
        """
        if raw_response.get("status") != "success":
            raise RuntimeError(f"Parser execution failed: {raw_response.get('message')}")

        # Extract content from nested MCP response structure
        result_data = raw_response.get("result", {})
        if isinstance(result_data, dict) and "content" in result_data:
            content_list = result_data.get("content", [])
            if isinstance(content_list, list) and len(content_list) > 0:
                first_item = content_list[0]
                if isinstance(first_item, dict) and "text" in first_item:
                    text = first_item["text"]
                    # Parse JSON from markdown format
                    import re
                    import json
                    result_match = re.search(r'### Result\s*\n(.*?)(?:\n###|$)', text, re.DOTALL)
                    if result_match:
                        json_str = result_match.group(1).strip()
                        return json.loads(json_str)

        return raw_response
```

#### 3. X.com Parser Implementation

**File:** `src/special_parsers/x_com.py`

```python
"""
X.com / Twitter Parser
Extracts structured tweet data from X.com pages.

Based on: /Users/zhenkai/Documents/personal/Projects/BrowserAgent/crawler/x_com/dom_extractor.py
"""

from datetime import datetime
from typing import Dict, List, Any
from .base import BaseParser

class XComParser(BaseParser):
    """
    Parser for X.com (formerly Twitter) pages.

    Supports:
    - Search results
    - User timelines
    - Single tweet pages
    - Trending topics
    """

    name = "x.com"
    description = "Extracts tweets with user info, text, metrics, and media"
    version = "1.0.0"

    def parse(self, browser_client) -> Dict[str, Any]:
        """
        Extract tweets from current X.com page.

        Args:
            browser_client: BrowserIntegration instance

        Returns:
            Structured tweet data
        """
        # Get current URL
        url = browser_client.get_current_url()
        page_title = browser_client.get_page_title()

        # Execute extraction JavaScript
        js_code = self.get_extraction_js()

        start_time = datetime.now()
        result = browser_client.playwright_client.browser_evaluate(function=js_code)
        end_time = datetime.now()

        # Parse response
        extraction_result = self._parse_response(result)

        # Build structured output
        tweets = extraction_result.get('tweets', [])

        return {
            "parser": self.name,
            "parser_version": self.version,
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "item_count": len(tweets),
            "items": tweets,
            "metadata": {
                "page_title": page_title,
                "extraction_time_ms": int((end_time - start_time).total_seconds() * 1000),
                "total_articles_found": extraction_result.get('count', 0)
            }
        }

    def get_extraction_js(self) -> str:
        """
        JavaScript code to extract tweets from DOM.

        Adapted from dom_extractor.py
        """
        return """
        () => {
          const articles = document.querySelectorAll('article[data-testid="tweet"]');

          const extractTweetFromDOM = (article) => {
            try {
              // Extract username from status link
              const statusLink = article.querySelector('a[href*="/status/"]');
              const href = statusLink?.getAttribute('href') || '';
              const username = href.split('/')[1] || '';

              // Extract display name from User-Name element
              const displayNameElement = article.querySelector('[data-testid="User-Name"]');
              let displayName = '';
              if (displayNameElement) {
                const fullText = displayNameElement.textContent || '';
                displayName = fullText.split('@')[0].trim();
              }

              // Extract tweet text
              const tweetTextElement = article.querySelector('[data-testid="tweetText"]');
              const text = tweetTextElement?.textContent || '';

              // Extract timestamp
              const timeElement = article.querySelector('time');
              const timestamp = timeElement?.getAttribute('datetime') || '';

              // Extract tweet ID from URL
              const tweetId = href.match(/status\\/(\\d+)/)?.[1] || '';

              // Extract metrics from aria-labels
              const metricsGroup = article.querySelector('[role="group"]');
              const metrics = {
                replies: 0,
                retweets: 0,
                likes: 0,
                views: 0,
                bookmarks: 0
              };

              if (metricsGroup) {
                const buttons = metricsGroup.querySelectorAll('button, a');
                buttons.forEach(btn => {
                  const ariaLabel = btn.getAttribute('aria-label') || '';

                  // Parse numbers from aria labels like "10 Replies"
                  const numberMatch = ariaLabel.match(/(\\d+)/);
                  const count = numberMatch ? parseInt(numberMatch[1], 10) : 0;

                  if (ariaLabel.toLowerCase().includes('repl')) {
                    metrics.replies = count;
                  } else if (ariaLabel.toLowerCase().includes('repost')) {
                    metrics.retweets = count;
                  } else if (ariaLabel.toLowerCase().includes('like')) {
                    metrics.likes = count;
                  } else if (ariaLabel.toLowerCase().includes('view')) {
                    metrics.views = count;
                  } else if (ariaLabel.toLowerCase().includes('bookmark')) {
                    metrics.bookmarks = count;
                  }
                });
              }

              // Extract media (images, videos)
              const media = [];
              const mediaImages = article.querySelectorAll('img[src*="pbs.twimg.com/media"]');
              mediaImages.forEach(img => {
                media.push({
                  type: 'photo',
                  url: img.src,
                  alt: img.alt || ''
                });
              });

              // Check for video
              const videoElement = article.querySelector('video');
              if (videoElement) {
                media.push({
                  type: 'video',
                  url: videoElement.src || '',
                  poster: videoElement.poster || ''
                });
              }

              // Check if it's a retweet or quote tweet
              const isRetweet = !!article.querySelector('[data-testid="socialContext"]')?.textContent?.includes('reposted');

              return {
                id: tweetId,
                username,
                displayName: displayName.replace(/\\s+/g, ' ').trim(),
                text: text.trim(),
                timestamp,
                metrics,
                media,
                url: `https://x.com/${username}/status/${tweetId}`,
                isRetweet,
                source: 'dom-parser',
                capturedAt: new Date().toISOString()
              };
            } catch (err) {
              return {
                error: err.message,
                stack: err.stack
              };
            }
          };

          const tweets = Array.from(articles).map(extractTweetFromDOM);

          // Filter out tweets with errors or missing IDs
          const validTweets = tweets.filter(t => t.id && !t.error);

          return {
            count: validTweets.length,
            tweets: validTweets
          };
        }
        """

    def validate_page(self, browser_client) -> bool:
        """Check if current page is a valid X.com page"""
        url = browser_client.get_current_url()
        return 'x.com' in url or 'twitter.com' in url
```

#### 4. MCP Tool Handler

**File:** `src/interactive_web_agent_mcp.py` (add to existing file)

```python
# Add to list_tools()
Tool(
    name="parse_page_with_special_parser",
    description="""Parse current page using a specialized parser for structured data extraction.

Use this when you need to extract structured data from supported websites:
- **x.com / twitter.com**: Extracts tweets with user info, text, engagement metrics, media
  - Supports: search results, timelines, profiles
  - Returns: tweet ID, username, display name, text, timestamp, metrics (replies, retweets, likes, views), media

The parser is auto-selected based on the current URL, or you can specify one explicitly.
Results are automatically saved to the session's parsed_results folder as JSON.

Example workflow:
1. navigate(url="https://x.com/search?q=gold")
2. scroll_down(times=20)  # Load more content
3. parse_page_with_special_parser()  # Extract all visible tweets
4. Result: File saved with 50+ tweets in structured JSON format

Returns:
- Summary of extracted items (count, types)
- Full file path to saved JSON results
- Parser used and execution time
""",
    inputSchema={
        "type": "object",
        "properties": {
            "parser_name": {
                "type": "string",
                "description": "Parser to use (auto-detected from URL if not specified)",
                "enum": ["auto", "x.com"]
            },
            "save_results": {
                "type": "boolean",
                "description": "Save results to file (default: true)",
                "default": True
            }
        }
    }
)

# Add tool handler
async def parse_page_with_special_parser(
    parser_name: str = "auto",
    save_results: bool = True
) -> Dict:
    """Parse current page using specialized parser"""
    timer = OperationTimer()
    input_data = {"parser_name": parser_name, "save_results": save_results}

    with timer:
        browser = get_browser()

        # Get current URL
        try:
            current_url = browser.get_current_url()
        except Exception as e:
            output = {
                "success": False,
                "error": f"Failed to get current URL: {str(e)}"
            }
            return output

        # Get parser
        from special_parsers import get_parser_for_url, list_available_parsers

        if parser_name == "auto":
            parser = get_parser_for_url(current_url)
            if not parser:
                available = list_available_parsers()
                output = {
                    "success": False,
                    "error": f"No parser available for URL: {current_url}",
                    "available_parsers": available
                }
                return output
        else:
            # Try to get specific parser by name
            parser = get_parser_for_url(f"https://{parser_name}/")
            if not parser:
                output = {
                    "success": False,
                    "error": f"Parser '{parser_name}' not found"
                }
                return output

        # Validate page
        if not parser.validate_page(browser):
            output = {
                "success": False,
                "error": f"Current page not compatible with {parser.name} parser",
                "url": current_url
            }
            return output

        # Execute parser
        try:
            parsed_data = parser.parse(browser)
        except Exception as e:
            import traceback
            output = {
                "success": False,
                "error": f"Parser execution failed: {str(e)}",
                "traceback": traceback.format_exc()
            }
            return output

        # Save results if requested
        filepath = None
        if save_results:
            filepath = _save_parsed_results(parser.name, parsed_data)

        # Build output
        output = {
            "success": True,
            "parser_used": parser.name,
            "parser_version": parser.version,
            "url": current_url,
            "item_count": parsed_data.get("item_count", 0),
            "items_summary": _summarize_items(parsed_data.get("items", [])),
            "filepath": str(filepath) if filepath else None,
            "execution_time_ms": parsed_data.get("metadata", {}).get("extraction_time_ms", 0),
            "message": f"Successfully parsed {parsed_data.get('item_count', 0)} items using {parser.name} parser" +
                      (f". Results saved to {filepath}" if filepath else "")
        }

    # Log operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("parse_page_with_special_parser", input_data, output, timer.get_duration())
        session_manager.update_operation_time()

    return output

def _save_parsed_results(parser_name: str, parsed_data: Dict) -> Path:
    """
    Save parsed results to session folder.

    Returns:
        Path to saved file
    """
    # Get session directory
    logger = get_debug_logger()
    if logger and logger.session_dir:
        base_dir = Path(logger.session_dir)
    else:
        base_dir = Path(DOWNLOADS_DIR)

    # Create parsed_results directory structure
    parsed_results_dir = base_dir / "parsed_results" / parser_name
    parsed_results_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from URL and timestamp
    url = parsed_data.get("url", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Extract query or identifier from URL
    import re
    from urllib.parse import urlparse, parse_qs

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # Try to get meaningful identifier
    identifier = ""
    if 'q' in query_params:  # Search query
        identifier = query_params['q'][0][:30]  # Limit length
    elif parsed_url.path:
        # Use last path component
        path_parts = [p for p in parsed_url.path.split('/') if p]
        if path_parts:
            identifier = path_parts[-1][:30]

    # Clean identifier for filename
    identifier = re.sub(r'[^\w\-]', '_', identifier) if identifier else "page"

    filename = f"{timestamp}_{identifier}.json"
    filepath = parsed_results_dir / filename

    # Save JSON
    import json
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(parsed_data, f, indent=2, ensure_ascii=False)

    return filepath

def _summarize_items(items: List[Dict]) -> Dict:
    """Create summary of parsed items"""
    if not items:
        return {"total": 0}

    # Count by type if available
    type_counts = {}
    for item in items:
        item_type = item.get("type", "item")
        type_counts[item_type] = type_counts.get(item_type, 0) + 1

    # Sample first few items
    sample = items[:3] if len(items) > 3 else items

    return {
        "total": len(items),
        "type_counts": type_counts,
        "sample": [
            {
                "id": item.get("id", ""),
                "text": item.get("text", "")[:100],  # First 100 chars
                "username": item.get("username", "")
            }
            for item in sample
        ]
    }
```

### Directory Structure

```
src/
├── interactive_web_agent_mcp.py       # Main MCP server (add new tool)
├── browser_integration.py
├── html_sanitizer.py
├── special_parsers/                   # NEW
│   ├── __init__.py                    # Parser registry
│   ├── base.py                        # BaseParser ABC
│   └── x_com.py                       # X.com parser implementation
└── ...

downloads/
└── sessions/
    └── session_20251229_103000/
        ├── operations.log
        ├── downloads/
        │   └── page_x_com_search_20251229_103500.html
        └── parsed_results/            # NEW
            └── x.com/
                ├── 20251229_103000_gold.json
                ├── 20251229_103530_ai.json
                └── 20251229_104000_crypto.json
```

### Output Format Example

**File:** `parsed_results/x.com/20251229_103000_gold.json`

```json
{
  "parser": "x.com",
  "parser_version": "1.0.0",
  "url": "https://x.com/search?q=gold",
  "timestamp": "2025-12-29T10:30:00.123456",
  "item_count": 47,
  "items": [
    {
      "id": "1869234567890123456",
      "username": "goldtrader",
      "displayName": "Gold Trader Pro",
      "text": "Gold prices hitting new highs this morning! 🚀 Technical analysis suggests continued bullish momentum. #gold #trading",
      "timestamp": "2025-12-29T09:15:00.000Z",
      "metrics": {
        "replies": 12,
        "retweets": 45,
        "likes": 230,
        "views": 15000,
        "bookmarks": 8
      },
      "media": [
        {
          "type": "photo",
          "url": "https://pbs.twimg.com/media/GFxxx.jpg",
          "alt": "Gold price chart"
        }
      ],
      "url": "https://x.com/goldtrader/status/1869234567890123456",
      "isRetweet": false,
      "source": "dom-parser",
      "capturedAt": "2025-12-29T10:30:00.123Z"
    },
    {
      "id": "1869234567890123457",
      "username": "cryptoanalyst",
      "displayName": "Crypto Analyst",
      "text": "Interesting correlation between gold and BTC lately. Both acting as safe havens during market uncertainty.",
      "timestamp": "2025-12-29T09:10:00.000Z",
      "metrics": {
        "replies": 8,
        "retweets": 23,
        "likes": 156,
        "views": 8900,
        "bookmarks": 12
      },
      "media": [],
      "url": "https://x.com/cryptoanalyst/status/1869234567890123457",
      "isRetweet": false,
      "source": "dom-parser",
      "capturedAt": "2025-12-29T10:30:00.456Z"
    }
    // ... 45 more tweets
  ],
  "metadata": {
    "page_title": "gold - Search / X",
    "extraction_time_ms": 187,
    "total_articles_found": 47
  }
}
```

---

## Implementation Plan

### Phase 1: Fix DOM Synchronization (Critical)

**Priority:** HIGH
**Estimated Effort:** 2-3 hours

1. **Implement DOM Injection** (`interactive_web_agent_mcp.py`)
   - [ ] Add `_inject_web_agent_ids()` function
   - [ ] Modify `get_page_content()` to call injection after sanitization
   - [ ] Add error handling for failed injections
   - [ ] Add logging for injection results

2. **Add Fallback Mechanism** (`interactive_web_agent_mcp.py`)
   - [ ] Modify `click_element()` to try XPath if data_id fails
   - [ ] Add retry logic with different locators

3. **Testing**
   - [ ] Test DOM injection on various pages
   - [ ] Verify click_element works after injection
   - [ ] Test fallback to XPath locator
   - [ ] Add unit tests for injection logic

### Phase 2: Special Parser Infrastructure

**Priority:** MEDIUM
**Estimated Effort:** 4-5 hours

1. **Create Parser Module** (`src/special_parsers/`)
   - [ ] Implement `__init__.py` with registry
   - [ ] Implement `base.py` with BaseParser ABC
   - [ ] Add parser discovery and matching logic

2. **Implement X.com Parser** (`src/special_parsers/x_com.py`)
   - [ ] Port extraction JavaScript from dom_extractor.py
   - [ ] Implement parse() method
   - [ ] Add validation logic
   - [ ] Handle response parsing

3. **Add MCP Tool** (`interactive_web_agent_mcp.py`)
   - [ ] Add `parse_page_with_special_parser` tool definition
   - [ ] Implement tool handler
   - [ ] Add result saving logic
   - [ ] Add summary generation

4. **Testing**
   - [ ] Test X.com parser on search results
   - [ ] Test X.com parser on timelines
   - [ ] Verify JSON output format
   - [ ] Test file saving to correct location

### Phase 3: Integration Testing

**Priority:** MEDIUM
**Estimated Effort:** 2-3 hours

1. **End-to-End Test**
   - [ ] Navigate to x.com/search?q=gold
   - [ ] Scroll 20 times
   - [ ] Parse and save results
   - [ ] Verify JSON contains tweets
   - [ ] Verify file location correct

2. **Edge Cases**
   - [ ] Test with no results
   - [ ] Test with network errors
   - [ ] Test with invalid pages
   - [ ] Test parser auto-detection

### Phase 4: Documentation

**Priority:** LOW
**Estimated Effort:** 1-2 hours

1. **User Documentation**
   - [ ] Add usage examples to README
   - [ ] Document parser API
   - [ ] Add troubleshooting guide

2. **Developer Documentation**
   - [ ] Document how to add new parsers
   - [ ] Add architecture diagrams
   - [ ] Document output format standards

---

## Testing Strategy

### Unit Tests

```python
# test_special_parsers.py

def test_parser_registry():
    """Test parser registration and lookup"""
    from special_parsers import get_parser_for_url

    parser = get_parser_for_url("https://x.com/search?q=test")
    assert parser is not None
    assert parser.name == "x.com"

def test_x_com_parser_validation():
    """Test X.com parser validation"""
    from special_parsers.x_com import XComParser

    parser = XComParser()
    # Mock browser client with x.com URL
    assert parser.validate_page(mock_browser_x_com)
    assert not parser.validate_page(mock_browser_google)

def test_parse_output_format():
    """Test parser output format compliance"""
    parser = XComParser()
    result = parser.parse(mock_browser_with_tweets)

    assert "parser" in result
    assert "url" in result
    assert "timestamp" in result
    assert "item_count" in result
    assert "items" in result
    assert isinstance(result["items"], list)
```

### Integration Tests

```python
# test_integration.py

async def test_full_workflow():
    """Test complete parsing workflow"""
    # Navigate to X.com
    await navigate("https://x.com/search?q=gold")

    # Scroll to load content
    await scroll_down(times=5)

    # Parse
    result = await parse_page_with_special_parser()

    assert result["success"] == True
    assert result["parser_used"] == "x.com"
    assert result["item_count"] > 0
    assert result["filepath"] is not None

    # Verify file exists
    assert Path(result["filepath"]).exists()
```

### Manual Test Plan

1. **X.com Search Results**
   - [ ] Navigate to x.com/search?q=gold
   - [ ] Scroll down 20 times
   - [ ] Call parse_page_with_special_parser()
   - [ ] Verify 40+ tweets extracted
   - [ ] Check JSON file format

2. **X.com User Timeline**
   - [ ] Navigate to x.com/elonmusk
   - [ ] Scroll down 10 times
   - [ ] Parse tweets
   - [ ] Verify user info correct

3. **Error Handling**
   - [ ] Try parsing non-X.com page
   - [ ] Try parsing empty search results
   - [ ] Disconnect network during parse

---

## Future Enhancements

### Additional Parsers

1. **Reddit Parser**
   - Extract posts from subreddits
   - Extract comments
   - Extract user info

2. **LinkedIn Parser**
   - Extract job postings
   - Extract company info
   - Extract profiles

3. **GitHub Parser**
   - Extract repository info
   - Extract issues
   - Extract pull requests

### Advanced Features

1. **Incremental Parsing**
   - Track already-parsed items
   - Only extract new content
   - Deduplication across sessions

2. **Export Formats**
   - CSV export
   - Excel export
   - Database storage

3. **Scheduling**
   - Periodic parsing
   - Automated scrolling
   - Background monitoring

---

## Appendix

### Example Integration Test Case

**Task from user:** "use interactive-web-agent, go to https://x.com/search?q=gold, scroll down 20 times, use special parser to parse and dump the content"

**Expected Claude Workflow:**

```python
# Step 1: Navigate
navigate(url="https://x.com/search?q=gold", wait_seconds=3.0)

# Step 2: Scroll to load content
scroll_down(times=20, amount=3)

# Step 3: Parse and save
parse_page_with_special_parser(parser_name="auto", save_results=True)
```

**Expected Output:**

```json
{
  "success": true,
  "parser_used": "x.com",
  "parser_version": "1.0.0",
  "url": "https://x.com/search?q=gold",
  "item_count": 52,
  "items_summary": {
    "total": 52,
    "type_counts": {"item": 52},
    "sample": [
      {
        "id": "1869234567890123456",
        "text": "Gold prices hitting new highs this morning! 🚀 Technical analysis suggests...",
        "username": "goldtrader"
      },
      {
        "id": "1869234567890123457",
        "text": "Interesting correlation between gold and BTC lately...",
        "username": "cryptoanalyst"
      }
    ]
  },
  "filepath": "/Users/zhenkai/Documents/personal/Projects/WebAgent/downloads/sessions/session_20251229_103000/parsed_results/x.com/20251229_105030_gold.json",
  "execution_time_ms": 187,
  "message": "Successfully parsed 52 items using x.com parser. Results saved to .../20251229_105030_gold.json"
}
```

---

## Sign-off

**Ready for Review:** ✅
**Implementation Start:** Pending approval
**Questions/Concerns:** Please review the DOM injection approach in Part 1 and the parser architecture in Part 2

**Next Steps:**
1. Review this design document
2. Approve or request changes
3. Begin Phase 1 implementation (DOM fix)
4. Proceed to Phase 2 (special parsers)
