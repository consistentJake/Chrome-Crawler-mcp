"""
Base Parser Interface
All special parsers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from datetime import datetime
import json
import re


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
                    result_match = re.search(r'### Result\s*\n(.*?)(?:\n###|$)', text, re.DOTALL)
                    if result_match:
                        json_str = result_match.group(1).strip()
                        # Extract JSON object from the result
                        json_match = re.search(r'\{[\s\S]*\}', json_str)
                        if json_match:
                            return json.loads(json_match.group(0))

        return raw_response
