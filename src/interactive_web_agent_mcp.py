#!/usr/bin/env python3
"""
Interactive Web Agent MCP Server
Combines browser automation with intelligent HTML extraction for agentic workflows.

This MCP provides a complete workflow for agents to:
1. Navigate to websites
2. Extract and understand page content via sanitized HTML
3. Query for specific elements
4. Interact with elements (click, type, etc.)
5. Download page content

No need to use Playwright MCP separately - everything is included here.
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from browser_integration import BrowserIntegration
from query_engine import QueryEngine
from html_sanitizer import HTMLSanitizer
from session_manager import SessionManager
from debug_logger import DebugLogger, OperationTimer


# Configuration
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "./downloads")
Path(DOWNLOADS_DIR).mkdir(parents=True, exist_ok=True)

# Debug mode configuration
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "yes")
SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", "60"))

# Global state
browser_integration = None
current_page_elements = []
current_page_url = ""
current_page_title = ""

# Debug state
session_manager = None
debug_logger = None

if DEBUG_MODE:
    print(f"[DEBUG MODE] Enabled - Sessions will be saved to {DOWNLOADS_DIR}/sessions/")
    session_manager = SessionManager(DOWNLOADS_DIR, timeout_seconds=SESSION_TIMEOUT_SECONDS)


def get_browser() -> BrowserIntegration:
    """Get or create browser integration instance"""
    global browser_integration
    if browser_integration is None:
        browser_integration = BrowserIntegration()
    return browser_integration


def get_debug_logger() -> Optional[DebugLogger]:
    """Get or create debug logger for current session"""
    global session_manager, debug_logger

    if not DEBUG_MODE or not session_manager:
        return None

    # Get or create session
    session_id, session_dir = session_manager.get_or_create_session()

    # Create debug logger if needed or session changed
    if debug_logger is None or debug_logger.session_dir != session_dir:
        debug_logger = DebugLogger(session_dir)
        print(f"[DEBUG MODE] Session: {session_id}")
        print(f"[DEBUG MODE] Session directory: {session_dir}")

    return debug_logger


# Create MCP server
server = Server("interactive-web-agent")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools with comprehensive descriptions for agent guidance"""
    return [
        Tool(
            name="navigate",
            description="""Navigate to a URL and wait for page load. This is the FIRST step in any web interaction workflow.

Usage: Use this tool whenever you need to visit a new URL or navigate to a different page.

After navigation, you MUST call get_page_content() to see what interactable elements are available on the page.

Example workflow:
1. navigate(url="https://example.com")
2. get_page_content() to see available elements
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to navigate to (must be a valid http/https URL)"
                    },
                    "wait_seconds": {
                        "type": "number",
                        "description": "Seconds to wait after navigation for page to load",
                        "default": 2.0
                    }
                },
                "required": ["url"]
            }
        ),

        Tool(
            name="get_page_content",
            description="""Extract and return sanitized HTML with indexed interactable elements.

CRITICAL: Use this tool immediately after ANY navigation or interaction to see what elements are available.

The tool returns a numbered list of ONLY interactable elements (links, buttons, inputs) with their:
- Index number [0], [1], [2]...
- web_agent_id (e.g., "wa-5") - USE THIS ID to interact with elements
- Tag type (a, button, input)
- Text content
- Attributes (href, type, placeholder, etc.)

Output formats:
- "indexed" (default): Easy-to-read numbered list like "[0] <a id=\"wa-0\" href=\"...\">Link Text</a>"
- "full_html": Complete sanitized HTML with data-web-agent-id attributes
- "elements_json": JSON array of all element objects

Example workflow:
1. navigate(url="https://example.com")
2. content = get_page_content(format="indexed")  # See what's on the page
3. Read the content to find elements you need
4. Use query_elements() or find_by_text() to find specific elements
5. Use click_element() or type_into_element() to interact
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["indexed", "full_html", "elements_json"],
                        "description": "Output format: 'indexed' for numbered list (recommended), 'full_html' for complete HTML, 'elements_json' for JSON array",
                        "default": "indexed"
                    }
                }
            }
        ),

        Tool(
            name="query_elements",
            description="""Query interactable elements using natural language or structured filters.

Use this AFTER get_page_content() to find specific elements before interacting with them.

Natural Language Examples:
- "Find the next page button"
- "Find all forum post links"
- "Find the 3rd page button"
- "Find the login button"
- "Find all links with 'OpenAI' in the text"

Structured Filter Examples:
- {"tag": "a"} - Find all links
- {"tag": "button", "text_contains": "submit"} - Find submit buttons
- {"href_pattern": "thread-*"} - Find links with href matching pattern
- {"tag": "a", "text_contains": "page", "id_range": [10, 20]} - Links containing "page" in index range 10-20

The tool returns matching elements with their web_agent_id which you can then use with click_element().

Workflow:
1. get_page_content() to load elements
2. query_elements(query="Find the 3rd page button")
3. Get the web_agent_id from results (e.g., "wa-15")
4. click_element(web_agent_id="wa-15")

IMPORTANT: Use compact=true (default) for large result sets to reduce token usage. Only use compact=false if you need full element details.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query to find elements"
                    },
                    "filters": {
                        "type": "object",
                        "description": "Structured filters for precise element matching",
                        "properties": {
                            "tag": {
                                "type": "string",
                                "description": "HTML tag name (a, button, input, etc.)"
                            },
                            "href_pattern": {
                                "type": "string",
                                "description": "Pattern for href attribute. Supports wildcards: 'thread-*', 'page/*'"
                            },
                            "text_contains": {
                                "type": "string",
                                "description": "Element text must contain this string (case-insensitive)"
                            },
                            "text_matches": {
                                "type": "string",
                                "description": "Element text must match this regex pattern"
                            },
                            "class_contains": {
                                "type": "string",
                                "description": "Element class must contain this string"
                            },
                            "id_range": {
                                "type": "array",
                                "description": "Filter by element index range [min, max]. E.g., [10, 20] for elements 10-20",
                                "items": {"type": "integer"},
                                "minItems": 2,
                                "maxItems": 2
                            }
                        }
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 50
                    },
                    "compact": {
                        "type": "boolean",
                        "description": "Return compact results (only web_agent_id, tag, text snippet, href) to save tokens. Default: true",
                        "default": True
                    }
                }
            }
        ),

        Tool(
            name="find_by_text",
            description="""Find interactable elements by their visible text content.

Use this for quick lookups when you know the exact or partial text of an element.

Examples:
- find_by_text(text="Login", exact=true) - Find element with exactly "Login"
- find_by_text(text="Next Page", exact=false) - Find elements containing "Next Page"
- find_by_text(text="OAI 面试挂经") - Find Chinese text (supports Unicode)

Returns elements with their web_agent_id for use with click_element().

Workflow:
1. get_page_content()
2. find_by_text(text="Submit")
3. click_element(web_agent_id=result['matches'][0]['web_agent_id'])

IMPORTANT: Use compact=true (default) for large result sets to reduce token usage.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to search for (supports Unicode/Chinese characters)"
                    },
                    "exact": {
                        "type": "boolean",
                        "description": "Whether to match exactly (true) or partial match (false)",
                        "default": False
                    },
                    "compact": {
                        "type": "boolean",
                        "description": "Return compact results to save tokens. Default: true",
                        "default": True
                    }
                },
                "required": ["text"]
            }
        ),

        Tool(
            name="click_element",
            description="""Click on an interactable element using its web_agent_id.

IMPORTANT: You must first find the element using query_elements() or find_by_text() to get its web_agent_id.

After clicking, ALWAYS call get_page_content() again to see the new page content.

Workflow Example:
1. get_page_content()
2. results = query_elements(query="Find the next page button")
3. web_agent_id = results['matches'][0]['web_agent_id']  # e.g., "wa-15"
4. click_element(web_agent_id="wa-15", wait_after=2.0)
5. get_page_content() # Get new page content after navigation

Common use cases:
- Clicking links to navigate
- Clicking buttons to submit forms or trigger actions
- Clicking pagination buttons to go to next page
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_agent_id": {
                        "type": "string",
                        "description": "The web_agent_id from query results (e.g., 'wa-15')"
                    },
                    "wait_after": {
                        "type": "number",
                        "description": "Seconds to wait after clicking for page to load",
                        "default": 1.0
                    }
                },
                "required": ["web_agent_id"]
            }
        ),

        Tool(
            name="type_into_element",
            description="""Type text into an input element (input, textarea).

Use this to fill forms, search boxes, text fields, etc.

Workflow Example:
1. get_page_content()
2. results = query_elements(filters={"tag": "input", "type": "text"})
3. type_into_element(web_agent_id="wa-5", text="search query", submit=true)

The 'submit' parameter will press Enter after typing, useful for search forms.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_agent_id": {
                        "type": "string",
                        "description": "The web_agent_id of the input element"
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to type into the element"
                    },
                    "submit": {
                        "type": "boolean",
                        "description": "Press Enter after typing (useful for search/login forms)",
                        "default": False
                    }
                },
                "required": ["web_agent_id", "text"]
            }
        ),

        Tool(
            name="download_page",
            description="""Download and save the current page HTML content to a file.

Use this as the FINAL step when you've navigated to the target page and want to save its content.

The downloaded file will include:
- Full HTML content
- Metadata (URL, title, timestamp)
- Filename is auto-generated or can be specified

Workflow Example:
1. navigate() to target page
2. click_element() to get to specific content
3. download_page() to save the page

Returns the filepath where the page was saved and the current URL for verification.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Optional filename (auto-generated if omitted). Saved to downloads/ directory."
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "Include metadata (URL, title, timestamp) at top of file",
                        "default": True
                    }
                }
            }
        ),

        Tool(
            name="get_current_url",
            description="""Get the current browser URL and page title.

Use this to verify you're on the correct page or to check where a click/navigation took you.

Returns:
- Current URL
- Page title

Useful for debugging and validation.
""",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),

        Tool(
            name="wait_for_page",
            description="""Wait for page to load or specific content to appear.

Use this when:
- Page is loading slowly after click
- Waiting for dynamic content to appear
- Need to pause between actions

Examples:
- wait_for_page(seconds=3.0) - Wait 3 seconds
- wait_for_page(text_to_appear="Login successful") - Wait until text appears
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "number",
                        "description": "Seconds to wait"
                    },
                    "text_to_appear": {
                        "type": "string",
                        "description": "Wait for this text to appear on the page"
                    }
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "navigate":
            result = await navigate(
                url=arguments["url"],
                wait_seconds=arguments.get("wait_seconds", 2.0)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "get_page_content":
            result = await get_page_content(
                output_format=arguments.get("format", "indexed")
            )
            # Return as plain text for indexed format, JSON for others
            if arguments.get("format") in ["elements_json"]:
                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
            else:
                # For indexed and full_html, return more readable format
                return [TextContent(type="text", text=result.get("content", ""))]

        elif name == "query_elements":
            result = await query_elements(
                query=arguments.get("query"),
                filters=arguments.get("filters"),
                limit=arguments.get("limit"),
                compact=arguments.get("compact", True)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "find_by_text":
            result = await find_by_text(
                text=arguments["text"],
                exact=arguments.get("exact", False),
                compact=arguments.get("compact", True)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "click_element":
            result = await click_element(
                web_agent_id=arguments["web_agent_id"],
                wait_after=arguments.get("wait_after", 1.0)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "type_into_element":
            result = await type_into_element(
                web_agent_id=arguments["web_agent_id"],
                text=arguments["text"],
                submit=arguments.get("submit", False)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "download_page":
            result = await download_page(
                filename=arguments.get("filename"),
                include_metadata=arguments.get("include_metadata", True)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "get_current_url":
            result = await get_current_url_tool()
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "wait_for_page":
            result = await wait_for_page(
                seconds=arguments.get("seconds"),
                text_to_appear=arguments.get("text_to_appear")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        return [TextContent(type="text", text=json.dumps(error_details, indent=2))]


# Tool Implementation Functions

async def navigate(url: str, wait_seconds: float = 2.0) -> Dict:
    """Navigate to URL and wait for page load"""
    global current_page_url, current_page_title, current_page_elements

    # Start timing for debug
    timer = OperationTimer()
    input_data = {"url": url, "wait_seconds": wait_seconds}

    with timer:
        browser = get_browser()

        # Navigate
        result = browser.playwright_client.browser_navigate(url)
        if result.get("status") != "success":
            output = {
                "success": False,
                "error": f"Navigation failed: {result.get('message', 'Unknown error')}"
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("navigate", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

        # Wait for page load
        await asyncio.sleep(wait_seconds)

        # Get page metadata
        try:
            current_page_url = browser.get_current_url()
            current_page_title = browser.get_page_title()
        except Exception as e:
            current_page_url = url
            current_page_title = ""

        # Clear current elements (will be populated on next get_page_content call)
        current_page_elements = []

        output = {
            "success": True,
            "url": current_page_url,
            "title": current_page_title,
            "message": f"Navigated to {current_page_url}. Call get_page_content() to see available elements."
        }

    # Log successful operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("navigate", input_data, output, timer.get_duration())
        session_manager.update_operation_time()

    return output


async def get_page_content(output_format: str = "indexed") -> Dict:
    """Extract and return sanitized page content with interactable elements"""
    global current_page_elements, current_page_url, current_page_title

    # Start timing for debug
    timer = OperationTimer()
    input_data = {"format": output_format}

    with timer:
        browser = get_browser()

        # Get current URL and title
        try:
            current_page_url = browser.get_current_url()
            current_page_title = browser.get_page_title()
        except:
            pass

        # Get page HTML
        try:
            raw_html = browser.get_current_page_html()
        except Exception as e:
            output = {
                "success": False,
                "error": f"Failed to get page HTML: {str(e)}"
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("get_page_content", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

        # Sanitize HTML and extract interactable elements
        sanitizer = HTMLSanitizer(max_tokens=8000, preserve_structure=True)
        sanitized_result = sanitizer.sanitize(raw_html, extraction_mode="all")

        # Update global state
        current_page_elements = sanitized_result['element_registry']

        # Return based on format
        if output_format == "indexed":
            content = sanitized_result['indexed_text']
            output = {
                "url": current_page_url,
                "title": current_page_title,
                "format": "indexed",
                "content": content,
                "element_count": len(current_page_elements),
                "element_types": sanitized_result['statistics']['element_types']
            }

        elif output_format == "full_html":
            output = {
                "url": current_page_url,
                "title": current_page_title,
                "format": "full_html",
                "content": sanitized_result['sanitized_html'],
                "element_count": len(current_page_elements)
            }

        elif output_format == "elements_json":
            output = {
                "url": current_page_url,
                "title": current_page_title,
                "format": "elements_json",
                "elements": current_page_elements,
                "element_count": len(current_page_elements)
            }

        else:
            output = {"error": f"Unknown format: {output_format}"}

    # Log operation with HTML snapshots
    logger = get_debug_logger()
    if logger:
        logger.log_operation(
            "get_page_content",
            input_data,
            output,
            timer.get_duration(),
            raw_html=raw_html,
            sanitized_html=sanitized_result['sanitized_html']
        )
        session_manager.update_operation_time()

    return output


def _compact_element(element: Dict) -> Dict:
    """
    Create a compact representation of an element.

    Only includes essential fields to reduce token usage:
    - web_agent_id (required for interaction)
    - tag (element type)
    - text (first 100 chars)
    - href (if it's a link)
    - index (position)
    """
    compact = {
        "web_agent_id": element.get("web_agent_id"),
        "tag": element.get("tag"),
        "index": element.get("index")
    }

    # Add text (truncated)
    text = element.get("text", "")
    if text:
        compact["text"] = text[:100] + ("..." if len(text) > 100 else "")

    # Add href for links
    if element.get("tag") == "a" and element.get("attributes", {}).get("href"):
        compact["href"] = element["attributes"]["href"]

    # Add other useful attributes for specific elements
    attrs = element.get("attributes", {})
    if element.get("tag") == "input":
        if "type" in attrs:
            compact["type"] = attrs["type"]
        if "placeholder" in attrs:
            compact["placeholder"] = attrs["placeholder"]

    return compact


async def query_elements(
    query: Optional[str] = None,
    filters: Optional[Dict] = None,
    limit: Optional[int] = None,
    compact: bool = True
) -> Dict:
    """Query elements using natural language or structured filters"""
    global current_page_elements

    # Start timing for debug
    timer = OperationTimer()
    input_data = {"query": query, "filters": filters, "limit": limit, "compact": compact}

    with timer:
        if not current_page_elements:
            output = {
                "success": False,
                "error": "No page content loaded. Call get_page_content() first.",
                "matches": [],
                "count": 0
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("query_elements", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

        # Handle id_range filter
        if filters and "id_range" in filters:
            id_range = filters["id_range"]
            if isinstance(id_range, list) and len(id_range) == 2:
                filters["index_min"] = id_range[0]
                filters["index_max"] = id_range[1]
                del filters["id_range"]

        query_engine = QueryEngine()
        matches = query_engine.query_elements(
            current_page_elements,
            query=query,
            filters=filters,
            limit=limit
        )

        # Convert to compact format if requested
        if compact:
            matches = [_compact_element(elem) for elem in matches]

        output = {
            "success": True,
            "query": query,
            "filters": filters,
            "matches": matches,
            "count": len(matches),
            "total_elements": len(current_page_elements),
            "compact": compact
        }

    # Log successful operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("query_elements", input_data, output, timer.get_duration())
        session_manager.update_operation_time()

    return output


async def find_by_text(text: str, exact: bool = False, compact: bool = True) -> Dict:
    """Find elements by text content"""
    global current_page_elements

    # Start timing for debug
    timer = OperationTimer()
    input_data = {"text": text, "exact": exact, "compact": compact}

    with timer:
        if not current_page_elements:
            output = {
                "success": False,
                "error": "No page content loaded. Call get_page_content() first.",
                "matches": [],
                "count": 0
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("find_by_text", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

        query_engine = QueryEngine()
        matches = query_engine.find_by_text(current_page_elements, text, exact)

        # Convert to compact format if requested
        if compact:
            matches = [_compact_element(elem) for elem in matches]

        output = {
            "success": True,
            "text": text,
            "exact": exact,
            "matches": matches,
            "count": len(matches),
            "compact": compact
        }

    # Log successful operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("find_by_text", input_data, output, timer.get_duration())
        session_manager.update_operation_time()

    return output


async def click_element(web_agent_id: str, wait_after: float = 1.0) -> Dict:
    """Click on an element by its web_agent_id"""
    global current_page_elements, current_page_url

    # Start timing for debug
    timer = OperationTimer()
    input_data = {"web_agent_id": web_agent_id, "wait_after": wait_after}

    with timer:
        # Find element in registry
        element = None
        for elem in current_page_elements:
            if elem.get("web_agent_id") == web_agent_id:
                element = elem
                break

        if not element:
            output = {
                "success": False,
                "error": f"Element with web_agent_id '{web_agent_id}' not found. Call get_page_content() to refresh elements."
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("click_element", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

        browser = get_browser()

        # Store old URL for verification
        try:
            old_url = browser.get_current_url()
        except:
            old_url = current_page_url

        # Use the data-web-agent-id locator to click
        locator = element['locators']['data_id']  # e.g., '[data-web-agent-id="wa-5"]'

        # Use browser_evaluate to click the element
        click_js = f"""
        () => {{
            const element = document.querySelector('{locator}');
            if (element) {{
                element.click();
                return {{success: true, clicked: true}};
            }} else {{
                return {{success: false, error: 'Element not found in DOM'}};
            }}
        }}
        """

        result = browser.playwright_client.browser_evaluate(function=click_js)

        # Wait for navigation to complete (if it's a link)
        if element.get("tag") == "a":
            # Wait for page load with timeout (use max of wait_after and 3.0 seconds)
            browser.wait_for_page_load(timeout=max(wait_after, 3.0))
        else:
            # For non-link elements, just wait the specified delay
            await asyncio.sleep(wait_after)

        # Get new URL
        try:
            new_url = browser.get_current_url()
        except:
            new_url = old_url

        # Verify navigation occurred
        navigation_occurred = (new_url != old_url)

        output = {
            "success": True,
            "web_agent_id": web_agent_id,
            "element_text": element.get("text", "")[:50],
            "element_tag": element.get("tag"),
            "action": "clicked",
            "old_url": old_url,
            "new_url": new_url,
            "navigation_occurred": navigation_occurred,
            "message": f"Clicked element {web_agent_id}. " +
                      (f"Navigated from {old_url} to {new_url}" if navigation_occurred else f"No navigation occurred, still on {new_url}") +
                      ". Call get_page_content() to see new page content."
        }

    # Log successful operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("click_element", input_data, output, timer.get_duration())
        session_manager.update_operation_time()

    return output


async def type_into_element(web_agent_id: str, text: str, submit: bool = False) -> Dict:
    """Type text into an input element"""
    global current_page_elements

    # Start timing for debug
    timer = OperationTimer()
    input_data = {"web_agent_id": web_agent_id, "text": text, "submit": submit}

    with timer:
        # Find element
        element = None
        for elem in current_page_elements:
            if elem.get("web_agent_id") == web_agent_id:
                element = elem
                break

        if not element:
            output = {
                "success": False,
                "error": f"Element with web_agent_id '{web_agent_id}' not found."
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("type_into_element", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

        # Verify it's an input element
        if element.get("tag") not in ["input", "textarea"]:
            output = {
                "success": False,
                "error": f"Element {web_agent_id} is a <{element.get('tag')}>, not an input. Can only type into <input> or <textarea>."
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("type_into_element", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

        browser = get_browser()
        locator = element['locators']['data_id']

        # Type into element using JavaScript
        type_js = f"""
        () => {{
            const element = document.querySelector('{locator}');
            if (element) {{
                element.value = {json.dumps(text)};
                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return {{success: true}};
            }} else {{
                return {{success: false, error: 'Element not found in DOM'}};
            }}
        }}
        """

        result = browser.playwright_client.browser_evaluate(function=type_js)

        # Submit if requested
        if submit:
            submit_js = f"""
            () => {{
                const element = document.querySelector('{locator}');
                if (element && element.form) {{
                    element.form.submit();
                    return {{success: true}};
                }} else if (element) {{
                    // Try pressing Enter
                    element.dispatchEvent(new KeyboardEvent('keydown', {{key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true}}));
                    return {{success: true, submitted_via_enter: true}};
                }}
                return {{success: false}};
            }}
            """
            browser.playwright_client.browser_evaluate(function=submit_js)
            await asyncio.sleep(1.0)

        output = {
            "success": True,
            "web_agent_id": web_agent_id,
            "action": "typed",
            "text_length": len(text),
            "submitted": submit
        }

    # Log successful operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("type_into_element", input_data, output, timer.get_duration())
        session_manager.update_operation_time()

    return output


async def download_page(filename: Optional[str] = None, include_metadata: bool = True) -> Dict:
    """Download current page HTML to file"""
    global current_page_url, current_page_title

    # Start timing for debug
    timer = OperationTimer()
    input_data = {"filename": filename, "include_metadata": include_metadata}

    with timer:
        browser = get_browser()

        # Get current page HTML
        try:
            html_content = browser.get_current_page_html()
            url = browser.get_current_url()
            title = browser.get_page_title()
        except Exception as e:
            output = {
                "success": False,
                "error": f"Failed to get page content: {str(e)}"
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("download_page", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Clean URL for filename
            url_safe = url.replace("https://", "").replace("http://", "")
            url_safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in url_safe)[:50]
            filename = f"page_{url_safe}_{timestamp}.html"

        # Ensure .html extension
        if not filename.endswith(".html"):
            filename += ".html"

        filepath = Path(DOWNLOADS_DIR) / filename

        # Prepare content
        if include_metadata:
            metadata = f"""<!--
Downloaded: {datetime.now().isoformat()}
URL: {url}
Title: {title}
-->

"""
            content = metadata + html_content
        else:
            content = html_content

        # Write to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            output = {
                "success": False,
                "error": f"Failed to write file: {str(e)}"
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("download_page", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

        output = {
            "success": True,
            "url": url,
            "title": title,
            "filepath": str(filepath.absolute()),
            "filename": filename,
            "size_bytes": len(content),
            "message": f"Page downloaded successfully to {filepath.absolute()}"
        }

    # Log successful operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("download_page", input_data, output, timer.get_duration())
        session_manager.update_operation_time()

    return output


async def get_current_url_tool() -> Dict:
    """Get current URL and title"""
    # Start timing for debug
    timer = OperationTimer()
    input_data = {}

    with timer:
        browser = get_browser()

        try:
            url = browser.get_current_url()
            title = browser.get_page_title()
        except Exception as e:
            output = {
                "success": False,
                "error": f"Failed to get URL: {str(e)}"
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("get_current_url", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

        output = {
            "success": True,
            "url": url,
            "title": title
        }

    # Log successful operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("get_current_url", input_data, output, timer.get_duration())
        session_manager.update_operation_time()

    return output


async def wait_for_page(seconds: Optional[float] = None, text_to_appear: Optional[str] = None) -> Dict:
    """Wait for page load or text to appear"""
    # Start timing for debug
    timer = OperationTimer()
    input_data = {"seconds": seconds, "text_to_appear": text_to_appear}

    with timer:
        browser = get_browser()

        if text_to_appear:
            # Wait for text to appear
            result = browser.playwright_client.browser_wait_for(text=text_to_appear)
            output = {
                "success": result.get("status") == "success",
                "waited_for_text": text_to_appear
            }

        elif seconds:
            # Wait for specified time
            await asyncio.sleep(seconds)
            output = {
                "success": True,
                "waited_seconds": seconds
            }

        else:
            output = {
                "success": False,
                "error": "Must specify either 'seconds' or 'text_to_appear'"
            }

    # Log operation (both success and failure cases)
    logger = get_debug_logger()
    if logger:
        logger.log_operation("wait_for_page", input_data, output, timer.get_duration())
        session_manager.update_operation_time()

    return output


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
