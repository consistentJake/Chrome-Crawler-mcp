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
import subprocess
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("[WARNING] PyAutoGUI not available. Scrolling will use JavaScript fallback.")

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Add helper directory to path for PlaywrightMcpClient import
helper_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'helper')
sys.path.insert(0, helper_dir)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from browser_integration import BrowserIntegration
from query_engine import QueryEngine
from html_sanitizer import HTMLSanitizer
from session_manager import SessionManager
from debug_logger import DebugLogger, OperationTimer
from PlaywrightMcpClient import activate_chrome_and_position_mouse


# Configuration
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "./downloads")
Path(DOWNLOADS_DIR).mkdir(parents=True, exist_ok=True)

# Debug mode configuration
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "yes")
SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", "60"))

# MCP Client type configuration ("playwright" or "chrome")
CLIENT_TYPE = os.getenv("MCP_CLIENT_TYPE", "chrome").lower()
print(f"[MCP CLIENT] Using {CLIENT_TYPE} client")

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
        browser_integration = BrowserIntegration(client_type=CLIENT_TYPE)
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

        Tool(
            name="scroll_down",
            description="""Scroll down the page using PyAutoGUI mouse wheel simulation.

This simulates actual mouse wheel scrolling by:
1. Activating the Chrome window and bringing it to front
2. Positioning the mouse at the center of the window
3. Performing mouse wheel scroll events

Use this when:
- Need to load more content on infinite scroll pages
- Navigate to content below the fold
- Trigger lazy-loaded elements that respond to real scroll events

Examples:
- scroll_down(times=1) - Scroll down once by default amount (3 clicks)
- scroll_down(times=3, amount=5) - Scroll down 3 times, 5 clicks each time

Note: Requires PyAutoGUI and accessibility permissions on macOS. Falls back to JavaScript if unavailable.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "times": {
                        "type": "integer",
                        "description": "Number of times to scroll down",
                        "default": 1
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Number of scroll clicks per action (default: 3). Higher values = faster scrolling."
                    }
                }
            }
        ),

        Tool(
            name="scroll_up",
            description="""Scroll up the page using PyAutoGUI mouse wheel simulation.

This simulates actual mouse wheel scrolling by:
1. Activating the Chrome window and bringing it to front
2. Positioning the mouse at the center of the window
3. Performing mouse wheel scroll events

Use this when:
- Need to go back to previous content
- Navigate to content above current view
- Return to top of page

Examples:
- scroll_up(times=1) - Scroll up once by default amount (3 clicks)
- scroll_up(times=3, amount=5) - Scroll up 3 times, 5 clicks each time

Note: Requires PyAutoGUI and accessibility permissions on macOS. Falls back to JavaScript if unavailable.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "times": {
                        "type": "integer",
                        "description": "Number of times to scroll up",
                        "default": 1
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Number of scroll clicks per action (default: 3). Higher values = faster scrolling."
                    }
                }
            }
        ),

        Tool(
            name="close_page",
            description="""Close the current browser page.

Use this when:
- Done with current browsing session
- Need to clean up browser resources
- Want to close the current page/tab

This will close the current page that the browser is displaying.

Example:
- close_page() - Closes the current browser page
""",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),

        Tool(
            name="manage_tabs",
            description="""Manage browser tabs (list, create, close, or select).

Use this to:
- List all open tabs to see what's available
- Create a new tab
- Close a specific tab by index
- Switch to a specific tab by index

Actions:
- "list" - Returns all open tabs with their index, title, and URL
- "new" - Creates a new blank tab
- "close" - Closes the tab at the specified index
- "select" - Switches to the tab at the specified index

Examples:
- manage_tabs(action="list") - List all tabs
- manage_tabs(action="new") - Create a new tab
- manage_tabs(action="close", index=1) - Close tab at index 1
- manage_tabs(action="select", index=0) - Switch to tab at index 0

IMPORTANT: After selecting a tab, call get_page_content() to see the content of the newly selected tab.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "new", "close", "select"],
                        "description": "Operation to perform: list all tabs, create new tab, close a tab, or select a tab"
                    },
                    "index": {
                        "type": "integer",
                        "description": "Tab index for close/select operations (0-based)"
                    }
                },
                "required": ["action"]
            }
        ),

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

        elif name == "scroll_down":
            result = await scroll_down(
                times=arguments.get("times", 1),
                amount=arguments.get("amount")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "scroll_up":
            result = await scroll_up(
                times=arguments.get("times", 1),
                amount=arguments.get("amount")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "close_page":
            result = await close_page()
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "manage_tabs":
            result = await manage_tabs(
                action=arguments["action"],
                index=arguments.get("index")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "parse_page_with_special_parser":
            result = await parse_page_with_special_parser(
                parser_name=arguments.get("parser_name", "auto"),
                save_results=arguments.get("save_results", True)
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


async def _inject_web_agent_ids(browser, element_registry: List[Dict]) -> Dict:
    """
    Inject data-web-agent-id attributes into the actual browser DOM.

    This ensures that click_element() can use [data-web-agent-id="wa-X"] CSS selectors
    to target elements in the live browser page.

    Args:
        browser: BrowserIntegration instance
        element_registry: List of element info dicts with locators

    Returns:
        Dict with injection results: {total, injected, failed, success}
    """
    if not element_registry:
        return {
            "success": True,
            "total": 0,
            "injected": 0,
            "failed": []
        }

    # Extract only the necessary data for injection (web_agent_id and xpath)
    # This reduces the payload size and avoids JSON serialization issues
    injection_data = [
        {
            "web_agent_id": el["web_agent_id"],
            "xpath": el["locators"]["xpath"]
        }
        for el in element_registry
    ]

    # Serialize the injection data as JSON and embed it in the JavaScript
    injection_data_json = json.dumps(injection_data, ensure_ascii=False)

    # Build JavaScript to inject IDs using XPath for reliable element location
    # The element data is embedded directly in the script as a JSON literal
    inject_js = f"""
    () => {{
        const elements = {injection_data_json};
        const results = {{
            total: elements.length,
            injected: 0,
            failed: []
        }};

        elements.forEach(el => {{
            try {{
                // Use XPath to find the element (most reliable locator)
                const xpath = el.xpath;
                const xpathResult = document.evaluate(
                    xpath,
                    document,
                    null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                    null
                );
                const element = xpathResult.singleNodeValue;

                if (element) {{
                    // Inject data-web-agent-id attribute
                    element.setAttribute('data-web-agent-id', el.web_agent_id);
                    results.injected++;
                }} else {{
                    results.failed.push({{
                        web_agent_id: el.web_agent_id,
                        xpath: xpath,
                        reason: 'Element not found by XPath'
                    }});
                }}
            }} catch (err) {{
                results.failed.push({{
                    web_agent_id: el.web_agent_id,
                    xpath: el.xpath,
                    reason: err.message
                }});
            }}
        }});

        return results;
    }}
    """

    try:
        # Execute injection JavaScript
        result = browser.playwright_client.browser_evaluate(function=inject_js)

        # Parse response from MCP format
        if result.get("status") == "success":
            # Extract the actual result from nested MCP structure
            result_data = result.get("result", {})
            if isinstance(result_data, dict) and "content" in result_data:
                content_list = result_data.get("content", [])
                if isinstance(content_list, list) and len(content_list) > 0:
                    first_item = content_list[0]
                    if isinstance(first_item, dict) and "text" in first_item:
                        text = first_item["text"]
                        # Parse JSON from markdown format
                        import re
                        result_match = re.search(r'### Result\s*\n(\{.*?\})', text, re.DOTALL)
                        if result_match:
                            injection_result = json.loads(result_match.group(1))
                            injection_result["success"] = True
                            return injection_result

            # Fallback: assume success if no errors
            return {
                "success": True,
                "total": len(element_registry),
                "injected": len(element_registry),
                "failed": []
            }
        else:
            return {
                "success": False,
                "total": len(element_registry),
                "injected": 0,
                "failed": [],
                "error": result.get("message", "Injection failed")
            }

    except Exception as e:
        return {
            "success": False,
            "total": len(element_registry),
            "injected": 0,
            "failed": [],
            "error": f"Exception during injection: {str(e)}"
        }


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

        # Inject data-web-agent-id attributes into actual browser DOM
        # This allows click_element() to use CSS selectors like [data-web-agent-id="wa-5"]
        injection_result = await _inject_web_agent_ids(browser, current_page_elements)

        # Log injection results if in debug mode
        logger = get_debug_logger()
        if logger and injection_result.get("failed"):
            # Log warning about failed injections
            failed_count = len(injection_result.get("failed", []))
            print(f"[WARNING] Failed to inject {failed_count}/{injection_result.get('total', 0)} web_agent_ids")

        # Return based on format
        if output_format == "indexed":
            content = sanitized_result['indexed_text']
            output = {
                "url": current_page_url,
                "title": current_page_title,
                "format": "indexed",
                "content": content,
                "element_count": len(current_page_elements),
                "element_types": sanitized_result['statistics']['element_types'],
                "injection": {
                    "total": injection_result.get("total", 0),
                    "injected": injection_result.get("injected", 0),
                    "failed": len(injection_result.get("failed", []))
                }
            }

        elif output_format == "full_html":
            output = {
                "url": current_page_url,
                "title": current_page_title,
                "format": "full_html",
                "content": sanitized_result['sanitized_html'],
                "element_count": len(current_page_elements),
                "injection": {
                    "total": injection_result.get("total", 0),
                    "injected": injection_result.get("injected", 0),
                    "failed": len(injection_result.get("failed", []))
                }
            }

        elif output_format == "elements_json":
            output = {
                "url": current_page_url,
                "title": current_page_title,
                "format": "elements_json",
                "elements": current_page_elements,
                "element_count": len(current_page_elements),
                "injection": {
                    "total": injection_result.get("total", 0),
                    "injected": injection_result.get("injected", 0),
                    "failed": len(injection_result.get("failed", []))
                }
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

        # Use the new click_element method which handles Chrome auto-scroll
        # Don't use wait_for_navigation here - we handle waiting separately below
        result = browser.click_element(css_selector=locator, wait_for_navigation=False)

        # Check if click was successful
        if result.get("status") == "error":
            output = {
                "success": False,
                "error": f"Failed to click element: {result.get('message', 'Unknown error')}"
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("click_element", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

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

        # Use the new type_into_element method which handles Chrome native typing
        result = browser.type_into_element(css_selector=locator, text=text)

        # Check if typing was successful
        if result.get("status") == "error":
            output = {
                "success": False,
                "error": f"Failed to type into element: {result.get('message', 'Unknown error')}"
            }

            # Log failed operation
            logger = get_debug_logger()
            if logger:
                logger.log_operation("type_into_element", input_data, output, timer.get_duration())
                session_manager.update_operation_time()

            return output

        # Submit if requested
        if submit:
            # Use keyboard Enter instead of JavaScript events for React compatibility
            if browser.client_type == "chrome":
                # Use Chrome's native keyboard simulation for Enter key
                browser.playwright_client.chrome_keyboard(
                    keys="Enter",
                    selector=locator
                )
            else:
                # Fallback to JavaScript for Playwright
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

        # Determine download directory
        # If logger is present, use session folder; otherwise use default DOWNLOADS_DIR
        logger = get_debug_logger()
        if logger and logger.session_dir:
            # Create downloads subfolder under session directory
            download_dir = Path(logger.session_dir) / "downloads"
            download_dir.mkdir(parents=True, exist_ok=True)
            filepath = download_dir / filename
        else:
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


async def scroll_down(times: int = 1, amount: Optional[int] = None) -> Dict:
    """Scroll down the page using PyAutoGUI mouse wheel simulation"""
    # Start timing for debug
    timer = OperationTimer()
    input_data = {"times": times, "amount": amount}

    with timer:
        if not PYAUTOGUI_AVAILABLE:
            # Fallback to JavaScript scrolling
            browser = get_browser()
            result = browser.playwright_client.scroll_down(times=times, amount=amount)

            if result.get("status") == "success":
                output = {
                    "success": True,
                    "times": times,
                    "scroll_amount": amount or 300,
                    "method": "javascript_fallback",
                    "message": result.get("message", f"Scrolled down {times} time(s) using JavaScript"),
                    "results": result.get("results", [])
                }
            else:
                output = {
                    "success": False,
                    "error": result.get("message", "Failed to scroll down")
                }
        else:
            # Use PyAutoGUI for scrolling
            try:
                # Activate Chrome and position mouse
                app_name = os.getenv("BROWSER_APP_NAME", "Google Chrome")
                center_x, center_y = activate_chrome_and_position_mouse(app_name)

                # Perform scrolling
                scroll_clicks = -(amount if amount is not None else 3)  # Negative for down
                results = []

                for i in range(times):
                    pyautogui.scroll(scroll_clicks)
                    results.append({
                        "status": "success",
                        "action": "scroll_down",
                        "iteration": i + 1,
                        "scroll_amount": scroll_clicks
                    })

                    # Pause between scrolls
                    if i < times - 1:
                        await asyncio.sleep(0.1)

                output = {
                    "success": True,
                    "times": times,
                    "scroll_amount": abs(scroll_clicks),
                    "method": "pyautogui",
                    "mouse_position": {"x": center_x, "y": center_y},
                    "message": f"Scrolled down {times} time(s) using PyAutoGUI",
                    "results": results
                }
            except Exception as e:
                output = {
                    "success": False,
                    "error": f"PyAutoGUI scroll failed: {str(e)}"
                }

    # Log operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("scroll_down", input_data, output, timer.get_duration())
        if session_manager:
            session_manager.update_operation_time()

    return output


async def scroll_up(times: int = 1, amount: Optional[int] = None) -> Dict:
    """Scroll up the page using PyAutoGUI mouse wheel simulation"""
    # Start timing for debug
    timer = OperationTimer()
    input_data = {"times": times, "amount": amount}

    with timer:
        if not PYAUTOGUI_AVAILABLE:
            # Fallback to JavaScript scrolling
            browser = get_browser()
            result = browser.playwright_client.scroll_up(times=times, amount=amount)

            if result.get("status") == "success":
                output = {
                    "success": True,
                    "times": times,
                    "scroll_amount": amount or 300,
                    "method": "javascript_fallback",
                    "message": result.get("message", f"Scrolled up {times} time(s) using JavaScript"),
                    "results": result.get("results", [])
                }
            else:
                output = {
                    "success": False,
                    "error": result.get("message", "Failed to scroll up")
                }
        else:
            # Use PyAutoGUI for scrolling
            try:
                # Activate Chrome and position mouse
                app_name = os.getenv("BROWSER_APP_NAME", "Google Chrome")
                center_x, center_y = activate_chrome_and_position_mouse(app_name)

                # Perform scrolling
                scroll_clicks = amount if amount is not None else 3  # Positive for up
                results = []

                for i in range(times):
                    pyautogui.scroll(scroll_clicks)
                    results.append({
                        "status": "success",
                        "action": "scroll_up",
                        "iteration": i + 1,
                        "scroll_amount": scroll_clicks
                    })

                    # Pause between scrolls
                    if i < times - 1:
                        await asyncio.sleep(0.1)

                output = {
                    "success": True,
                    "times": times,
                    "scroll_amount": scroll_clicks,
                    "method": "pyautogui",
                    "mouse_position": {"x": center_x, "y": center_y},
                    "message": f"Scrolled up {times} time(s) using PyAutoGUI",
                    "results": results
                }
            except Exception as e:
                output = {
                    "success": False,
                    "error": f"PyAutoGUI scroll failed: {str(e)}"
                }

    # Log operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("scroll_up", input_data, output, timer.get_duration())
        if session_manager:
            session_manager.update_operation_time()

    return output


async def close_page() -> Dict:
    """Close the current browser page"""
    # Start timing for debug
    timer = OperationTimer()
    input_data = {}

    with timer:
        try:
            browser = get_browser()

            # Close the browser page using the Playwright client
            result = browser.playwright_client.browser_close()

            if result.get("status") == "success":
                output = {
                    "success": True,
                    "message": "Browser page closed successfully"
                }
            else:
                output = {
                    "success": False,
                    "error": result.get("message", "Failed to close browser page")
                }
        except Exception as e:
            output = {
                "success": False,
                "error": f"Failed to close page: {str(e)}"
            }

    # Log operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("close_page", input_data, output, timer.get_duration())
        if session_manager:
            session_manager.update_operation_time()

    return output


async def manage_tabs(action: str, index: Optional[int] = None) -> Dict:
    """Manage browser tabs (list, create, close, or select)"""
    global current_page_url, current_page_title, current_page_elements

    # Start timing for debug
    timer = OperationTimer()
    input_data = {"action": action, "index": index}

    with timer:
        try:
            browser = get_browser()

            # Validate index for operations that require it
            if action in ["close", "select"] and index is None:
                output = {
                    "success": False,
                    "error": f"Action '{action}' requires an 'index' parameter"
                }
            else:
                # Call the browser_tabs method from PlaywrightMcpClient
                result = browser.playwright_client.browser_tabs(action=action, index=index)

                if result.get("status") == "success":
                    # Parse the result based on action
                    if action == "list":
                        # Extract tabs data from nested MCP response format
                        # The response is: {'status': 'success', 'result': {'content': [{'type': 'text', 'text': '...'}]}}
                        # The text format is markdown like:
                        # ### Open tabs
                        # - 0: (current) [Example Domain] (https://example.com/)
                        # - 1: [Google] (https://google.com/)

                        tabs_list = []
                        current_index = -1

                        result_data = result.get("result", {})

                        # Parse from nested content structure (MCP format)
                        if isinstance(result_data, dict) and "content" in result_data:
                            content_list = result_data.get("content", [])
                            if isinstance(content_list, list) and len(content_list) > 0:
                                first_item = content_list[0]
                                if isinstance(first_item, dict) and "text" in first_item:
                                    text = first_item["text"]

                                    # Parse the markdown text format
                                    # Format: "- 0: (current) [Title] (URL)"
                                    import re
                                    lines = text.split('\n')
                                    for line in lines:
                                        # Match pattern like: "- 0: (current) [Example Domain] (https://example.com/)"
                                        # or: "- 1: [Google] (https://google.com/)"
                                        match = re.match(r'^-\s*(\d+):\s*(\(current\)\s*)?\[([^\]]*)\]\s*\(([^)]+)\)', line.strip())
                                        if match:
                                            index = int(match.group(1))
                                            is_current = bool(match.group(2))
                                            title = match.group(3)
                                            url = match.group(4)

                                            tabs_list.append({
                                                "index": index,
                                                "title": title,
                                                "url": url
                                            })

                                            if is_current:
                                                current_index = index

                        output = {
                            "success": True,
                            "action": "list",
                            "tabs": tabs_list,
                            "current_index": current_index,
                            "total_tabs": len(tabs_list),
                            "message": f"Found {len(tabs_list)} tab(s). Current tab index: {current_index}"
                        }

                    elif action == "new":
                        output = {
                            "success": True,
                            "action": "new",
                            "message": "New tab created successfully. Use get_page_content() to see the new tab content."
                        }
                        # Clear current elements since we're on a new tab
                        current_page_elements = []

                    elif action == "close":
                        output = {
                            "success": True,
                            "action": "close",
                            "closed_index": index,
                            "message": f"Tab at index {index} closed successfully"
                        }
                        # Clear current elements as the active tab might have changed
                        current_page_elements = []

                    elif action == "select":
                        output = {
                            "success": True,
                            "action": "select",
                            "selected_index": index,
                            "message": f"Switched to tab at index {index}. Use get_page_content() to see the tab content."
                        }
                        # Clear current elements since we switched tabs
                        current_page_elements = []

                        # Update current URL and title for the newly selected tab
                        try:
                            await asyncio.sleep(0.5)  # Brief wait for tab switch
                            current_page_url = browser.get_current_url()
                            current_page_title = browser.get_page_title()
                            output["url"] = current_page_url
                            output["title"] = current_page_title
                        except:
                            pass
                    else:
                        output = {
                            "success": False,
                            "error": f"Unknown action: {action}"
                        }
                else:
                    output = {
                        "success": False,
                        "error": result.get("message", f"Tab operation '{action}' failed")
                    }

        except Exception as e:
            output = {
                "success": False,
                "error": f"Failed to manage tabs: {str(e)}"
            }

    # Log operation
    logger = get_debug_logger()
    if logger:
        logger.log_operation("manage_tabs", input_data, output, timer.get_duration())
        if session_manager:
            session_manager.update_operation_time()

    return output


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
        if session_manager:
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
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(parsed_data, f, indent=2, ensure_ascii=False)

    return filepath


def _summarize_items(items) -> Dict:
    """Create summary of parsed items"""
    # Handle both list and dict formats
    if isinstance(items, dict):
        # For parsers like 1point3acres that return {main_post: ..., replies: [...]}
        total = 0
        summary = {}

        if "main_post" in items:
            total += 1
            summary["main_post"] = True
            if items["main_post"] and items["main_post"].get("content"):
                summary["main_post_preview"] = items["main_post"].get("content", "")[:100]

        if "replies" in items:
            total += len(items["replies"])
            summary["replies_count"] = len(items["replies"])
            if items["replies"]:
                summary["first_reply_preview"] = items["replies"][0].get("content", "")[:100] if items["replies"][0] else ""

        summary["total"] = total
        return summary

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
