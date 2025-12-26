#!/usr/bin/env python3
"""
Web Extraction MCP Server
Provides intelligent HTML extraction and sanitization for Claude Code
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from transaction_manager import TransactionManager
from browser_integration import BrowserIntegration
from query_engine import QueryEngine
from html_sanitizer import HTMLSanitizer


# Initialize components
DATA_DIR = os.getenv("DATA_DIR", "./data")
transaction_manager = TransactionManager(DATA_DIR)
query_engine = QueryEngine()

# Browser integration is initialized per-request to avoid keeping connections open
browser_integration = None


def get_browser() -> BrowserIntegration:
    """Get or create browser integration instance"""
    global browser_integration
    if browser_integration is None:
        browser_integration = BrowserIntegration()
    return browser_integration


# Create MCP server
server = Server("web-extraction")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="extract_page",
            description="Extract and sanitize the current browser page for AI analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "transaction_id": {
                        "type": "string",
                        "description": "Optional transaction ID (auto-generated if omitted)"
                    },
                    "extraction_mode": {
                        "type": "string",
                        "enum": ["links", "forms", "content", "all"],
                        "description": "Type of elements to extract",
                        "default": "links"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens for sanitized output",
                        "default": 4000
                    },
                    "include_raw": {
                        "type": "boolean",
                        "description": "Whether to save raw HTML",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="query_page_elements",
            description="Query elements from a previously extracted page",
            inputSchema={
                "type": "object",
                "properties": {
                    "transaction_id": {
                        "type": "string",
                        "description": "Transaction ID of extracted page"
                    },
                    "query": {
                        "type": "string",
                        "description": "Natural language query (e.g., 'Find all forum post links')"
                    },
                    "filters": {
                        "type": "object",
                        "description": "Structured filters (tag, href_pattern, text_contains, etc.)",
                        "properties": {
                            "tag": {"type": "string"},
                            "href_pattern": {"type": "string"},
                            "text_contains": {"type": "string"},
                            "text_matches": {"type": "string"},
                            "class_contains": {"type": "string"}
                        }
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return"
                    }
                },
                "required": ["transaction_id"]
            }
        ),
        Tool(
            name="get_sanitized_html",
            description="Retrieve sanitized HTML for a transaction",
            inputSchema={
                "type": "object",
                "properties": {
                    "transaction_id": {
                        "type": "string",
                        "description": "Transaction ID"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["html", "indexed_text", "elements_only"],
                        "description": "Output format",
                        "default": "indexed_text"
                    }
                },
                "required": ["transaction_id"]
            }
        ),
        Tool(
            name="list_transactions",
            description="List all stored transactions",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of transactions to return"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of transactions to skip",
                        "default": 0
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls"""

    try:
        if name == "extract_page":
            result = await extract_page(
                transaction_id=arguments.get("transaction_id"),
                extraction_mode=arguments.get("extraction_mode", "links"),
                max_tokens=arguments.get("max_tokens", 4000),
                include_raw=arguments.get("include_raw", False)
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]

        elif name == "query_page_elements":
            result = await query_page_elements(
                transaction_id=arguments["transaction_id"],
                query=arguments.get("query"),
                filters=arguments.get("filters"),
                limit=arguments.get("limit")
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]

        elif name == "get_sanitized_html":
            result = await get_sanitized_html(
                transaction_id=arguments["transaction_id"],
                output_format=arguments.get("format", "indexed_text")
            )
            return [TextContent(type="text", text=result)]

        elif name == "list_transactions":
            result = await list_transactions_tool(
                limit=arguments.get("limit"),
                offset=arguments.get("offset", 0)
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]

        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e), "type": type(e).__name__})
        )]


async def extract_page(
    transaction_id: Optional[str] = None,
    extraction_mode: str = "links",
    max_tokens: int = 4000,
    include_raw: bool = False
) -> Dict:
    """
    Extract and sanitize the current browser page.

    Returns:
        Dictionary with extraction results
    """
    # Get browser instance
    browser = get_browser()

    # Get page metadata
    try:
        page_metadata = browser.get_page_metadata()
        url = page_metadata.get("url", "")
        title = page_metadata.get("title", "")
    except:
        url = ""
        title = ""

    # Create transaction
    if transaction_id is None:
        transaction_id = transaction_manager.create_transaction(
            url=url,
            extraction_mode=extraction_mode
        )
    else:
        if not transaction_manager.transaction_exists(transaction_id):
            transaction_manager.create_transaction(
                transaction_id=transaction_id,
                url=url,
                extraction_mode=extraction_mode
            )

    # Get page HTML
    raw_html = browser.get_current_page_html()

    # Sanitize HTML
    sanitizer = HTMLSanitizer(max_tokens=max_tokens)
    sanitized_result = sanitizer.sanitize(raw_html, extraction_mode=extraction_mode)

    # Save data
    if include_raw:
        transaction_manager.save_html(
            transaction_id,
            raw_html=raw_html,
            sanitized_html=sanitized_result['sanitized_html']
        )
    else:
        transaction_manager.save_html(
            transaction_id,
            sanitized_html=sanitized_result['sanitized_html']
        )

    transaction_manager.save_elements(
        transaction_id,
        sanitized_result['element_registry']
    )

    transaction_manager.save_indexed_text(
        transaction_id,
        sanitized_result['indexed_text']
    )

    # Update metadata
    transaction_manager.update_metadata(transaction_id, {
        "url": url,
        "title": title,
        "extraction_mode": extraction_mode,
        "max_tokens": max_tokens,
        "statistics": sanitized_result['statistics'],
        "status": "completed"
    })

    # Prepare response
    storage_path = str(transaction_manager.get_transaction_dir(transaction_id))

    # Get preview of indexed text
    indexed_text = sanitized_result['indexed_text']
    preview_lines = indexed_text.split('\n')[:10]
    preview = '\n'.join(preview_lines)
    if len(preview_lines) < len(indexed_text.split('\n')):
        preview += f"\n... and {len(indexed_text.split('\n')) - len(preview_lines)} more elements"

    return {
        "transaction_id": transaction_id,
        "url": url,
        "title": title,
        "statistics": sanitized_result['statistics'],
        "storage_path": storage_path,
        "preview": {
            "indexed_text": preview
        }
    }


async def query_page_elements(
    transaction_id: str,
    query: Optional[str] = None,
    filters: Optional[Dict] = None,
    limit: Optional[int] = None
) -> Dict:
    """
    Query elements from a previously extracted page.

    Returns:
        Dictionary with matching elements
    """
    # Get elements from transaction
    elements = transaction_manager.get_elements(transaction_id)

    # Query elements
    matches = query_engine.query_elements(
        elements,
        query=query,
        filters=filters,
        limit=limit
    )

    return {
        "transaction_id": transaction_id,
        "matches": matches,
        "count": len(matches),
        "total_elements": len(elements)
    }


async def get_sanitized_html(
    transaction_id: str,
    output_format: str = "indexed_text"
) -> str:
    """
    Retrieve sanitized HTML for a transaction.

    Returns:
        Sanitized content in requested format
    """
    if output_format == "html":
        return transaction_manager.get_html(transaction_id, "sanitized")

    elif output_format == "indexed_text":
        return transaction_manager.get_indexed_text(transaction_id)

    elif output_format == "elements_only":
        elements = transaction_manager.get_elements(transaction_id)
        return json.dumps(elements, indent=2, ensure_ascii=False)

    else:
        raise ValueError(f"Unknown format: {output_format}")


async def list_transactions_tool(
    limit: Optional[int] = None,
    offset: int = 0
) -> Dict:
    """
    List all stored transactions.

    Returns:
        Dictionary with transaction list
    """
    transactions = transaction_manager.list_transactions(limit=limit, offset=offset)

    return {
        "transactions": transactions,
        "count": len(transactions),
        "offset": offset
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
