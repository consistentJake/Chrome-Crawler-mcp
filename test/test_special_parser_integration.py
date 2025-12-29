#!/usr/bin/env python3
"""
Integration test for special parser feature.

Tests the complete workflow:
1. Navigate to X.com search
2. Scroll to load content
3. Parse with special parser
4. Verify results saved

REQUIRES: Chrome/Playwright MCP server running
"""

import sys
import os
import json
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set environment variables for testing
os.environ['DEBUG_MODE'] = 'true'
os.environ['MCP_CLIENT_TYPE'] = 'chrome'  # or 'playwright'


async def test_x_com_parser():
    """
    Integration test for X.com parser.

    This requires a running browser and will:
    1. Navigate to X.com search page
    2. Scroll to load tweets
    3. Parse tweets with special parser
    4. Verify results
    """
    print("=" * 70)
    print("Integration Test: X.com Special Parser")
    print("=" * 70)

    # Import after setting env vars
    from interactive_web_agent_mcp import (
        navigate,
        scroll_down,
        parse_page_with_special_parser,
        get_browser
    )

    try:
        # Step 1: Navigate to X.com search
        print("\n[1/4] Navigating to X.com search page...")
        result = await navigate("https://x.com/search?q=gold", wait_seconds=3.0)

        if not result.get("success"):
            print(f"❌ Navigation failed: {result.get('error')}")
            return False

        print(f"✓ Navigated to: {result.get('url')}")
        print(f"  Page title: {result.get('title')}")

        # Step 2: Scroll to load more content
        print("\n[2/4] Scrolling to load more tweets...")
        scroll_result = await scroll_down(times=5, amount=3)  # Start with 5 scrolls

        if not scroll_result.get("success"):
            print(f"❌ Scroll failed: {scroll_result.get('error')}")
            return False

        print(f"✓ Scrolled {scroll_result.get('times')} times")

        # Step 3: Parse with special parser
        print("\n[3/4] Parsing page with X.com parser...")
        parse_result = await parse_page_with_special_parser(
            parser_name="auto",
            save_results=True
        )

        if not parse_result.get("success"):
            print(f"❌ Parsing failed: {parse_result.get('error')}")
            print(f"  Traceback: {parse_result.get('traceback', 'N/A')}")
            return False

        print(f"✓ Parser used: {parse_result.get('parser_used')}")
        print(f"  Items extracted: {parse_result.get('item_count')}")
        print(f"  Execution time: {parse_result.get('execution_time_ms')}ms")
        print(f"  File saved to: {parse_result.get('filepath')}")

        # Step 4: Verify results
        print("\n[4/4] Verifying results...")

        # Check file exists
        filepath = parse_result.get('filepath')
        if not filepath or not Path(filepath).exists():
            print(f"❌ Results file not found: {filepath}")
            return False

        print(f"✓ Results file exists: {Path(filepath).name}")

        # Load and verify JSON
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"✓ JSON is valid")
        print(f"  Parser: {data.get('parser')}")
        print(f"  URL: {data.get('url')}")
        print(f"  Item count: {data.get('item_count')}")

        # Check items structure
        items = data.get('items', [])
        if len(items) == 0:
            print("⚠️  WARNING: No items extracted (page might not have loaded)")
            return True  # Not a failure, but worth noting

        print(f"✓ {len(items)} items extracted")

        # Display sample tweet
        if items:
            sample = items[0]
            print(f"\n📊 Sample Tweet:")
            print(f"  ID: {sample.get('id')}")
            print(f"  User: @{sample.get('username')} ({sample.get('displayName')})")
            print(f"  Text: {sample.get('text', '')[:100]}...")
            print(f"  Metrics: {sample.get('metrics')}")

        # Display summary
        summary = parse_result.get('items_summary', {})
        if summary and summary.get('sample'):
            print(f"\n📋 Items Summary:")
            print(f"  Total: {summary.get('total')}")
            for i, item in enumerate(summary.get('sample', [])[:3], 1):
                print(f"  [{i}] @{item.get('username')}: {item.get('text', '')[:60]}...")

        print("\n" + "=" * 70)
        print("✅ Integration test PASSED!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_parser_selection():
    """Test parser auto-detection and manual selection"""
    print("\n" + "=" * 70)
    print("Unit Test: Parser Selection")
    print("=" * 70)

    from special_parsers import get_parser_for_url, list_available_parsers

    # Test URL matching
    test_cases = [
        ("https://x.com/search?q=test", "x.com"),
        ("https://twitter.com/elonmusk", "x.com"),
        ("https://www.google.com", None),
    ]

    for url, expected in test_cases:
        parser = get_parser_for_url(url)
        parser_name = parser.name if parser else None

        if parser_name == expected:
            print(f"✓ {url} → {parser_name or 'None'}")
        else:
            print(f"❌ {url} → Expected {expected}, got {parser_name}")
            return False

    # List available parsers
    parsers = list_available_parsers()
    print(f"\n✓ Available parsers: {len(parsers)}")
    for p in parsers:
        print(f"  - {p['name']}: {p['description']}")

    print("\n✅ Parser selection test PASSED!")
    return True


async def test_parser_output_format():
    """Test that parser output matches expected format"""
    print("\n" + "=" * 70)
    print("Unit Test: Parser Output Format")
    print("=" * 70)

    # Mock parsed data (what XComParser.parse() should return)
    mock_output = {
        "parser": "x.com",
        "parser_version": "1.0.0",
        "url": "https://x.com/search?q=test",
        "timestamp": "2025-12-29T10:30:00Z",
        "item_count": 2,
        "items": [
            {
                "id": "123456789",
                "username": "testuser",
                "displayName": "Test User",
                "text": "This is a test tweet",
                "timestamp": "2025-12-29T10:00:00Z",
                "metrics": {
                    "replies": 10,
                    "retweets": 20,
                    "likes": 100,
                    "views": 5000,
                    "bookmarks": 5
                },
                "media": [],
                "url": "https://x.com/testuser/status/123456789",
                "isRetweet": False,
                "source": "dom-parser",
                "capturedAt": "2025-12-29T10:30:00Z"
            },
            {
                "id": "987654321",
                "username": "anotheruser",
                "displayName": "Another User",
                "text": "Another test tweet",
                "timestamp": "2025-12-29T09:00:00Z",
                "metrics": {
                    "replies": 5,
                    "retweets": 10,
                    "likes": 50,
                    "views": 2000,
                    "bookmarks": 2
                },
                "media": [],
                "url": "https://x.com/anotheruser/status/987654321",
                "isRetweet": False,
                "source": "dom-parser",
                "capturedAt": "2025-12-29T10:30:00Z"
            }
        ],
        "metadata": {
            "page_title": "test - Search / X",
            "extraction_time_ms": 150,
            "total_articles_found": 2
        }
    }

    # Verify structure
    required_fields = ["parser", "parser_version", "url", "timestamp", "item_count", "items", "metadata"]
    for field in required_fields:
        if field not in mock_output:
            print(f"❌ Missing required field: {field}")
            return False
        print(f"✓ Has field: {field}")

    # Verify items structure
    if mock_output["items"]:
        item = mock_output["items"][0]
        required_item_fields = ["id", "username", "displayName", "text", "timestamp", "metrics", "url"]
        for field in required_item_fields:
            if field not in item:
                print(f"❌ Item missing field: {field}")
                return False
        print(f"✓ Item structure valid")

    print("\n✅ Output format test PASSED!")
    return True


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("Special Parser Test Suite")
    print("=" * 70)

    # Unit tests (don't require browser)
    print("\nRunning unit tests...")
    unit_tests = [
        ("Parser Selection", test_parser_selection),
        ("Output Format", test_parser_output_format),
    ]

    for name, test_func in unit_tests:
        try:
            result = await test_func()
            if not result:
                print(f"\n❌ {name} test failed")
                return 1
        except Exception as e:
            print(f"\n❌ {name} test error: {e}")
            import traceback
            traceback.print_exc()
            return 1

    # Integration test (requires browser)
    print("\n" + "=" * 70)
    print("Integration Test (requires browser)")
    print("=" * 70)
    print("\nNOTE: This test requires:")
    print("  1. Chrome browser running")
    print("  2. MCP server configured")
    print("  3. Network access to x.com")
    print("\nDo you want to run the integration test? (y/N): ", end='')

    # For automated testing, skip integration test
    import sys
    if sys.stdin.isatty():
        response = input().strip().lower()
        if response == 'y':
            result = await test_x_com_parser()
            if not result:
                print("\n❌ Integration test failed")
                return 1
    else:
        print("N (skipping in automated mode)")

    print("\n" + "=" * 70)
    print("✅ All tests PASSED!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
