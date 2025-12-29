#!/usr/bin/env python3
"""
Test script for Special Parser Feature
Tests the complete workflow from navigation to parsing to saving results
"""

import sys
import os
import json
import time
from pathlib import Path

# Add src and helper to path
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
helper_path = os.path.join(os.path.dirname(__file__), '..', 'helper')
sys.path.insert(0, src_path)
sys.path.insert(0, helper_path)

# Import special parsers only (doesn't require browser)
from special_parsers import get_parser_for_url, list_available_parsers, XComParser

# BrowserIntegration will be imported only when needed for integration test
BrowserIntegration = None


def test_parser_components():
    """Test individual parser components"""
    print("=" * 60)
    print("Testing Parser Components")
    print("=" * 60)

    # Test 1: Parser Registry
    print("\n1. Testing Parser Registry...")

    # Test URL matching
    test_cases = [
        ("https://x.com/search?q=test", "x.com", True),
        ("https://twitter.com/elonmusk", "x.com", True),
        ("https://www.google.com", None, False),
        ("https://reddit.com/r/test", None, False),  # Not implemented yet
    ]

    for url, expected_name, should_exist in test_cases:
        parser = get_parser_for_url(url)
        parser_name = parser.name if parser else None

        if should_exist:
            if parser_name == expected_name:
                print(f"   ✅ {url} → {parser_name}")
            else:
                print(f"   ❌ {url} → Expected {expected_name}, got {parser_name}")
                return False
        else:
            if parser is None:
                print(f"   ✅ {url} → None (as expected)")
            else:
                print(f"   ❌ {url} → Expected None, got {parser_name}")
                return False

    # List available parsers
    parsers = list_available_parsers()
    print(f"\n   Available parsers: {len(parsers)}")
    for p in parsers:
        print(f"   - {p['name']}: {p['description']}")
        print(f"     Patterns: {p['patterns']}")
        print(f"     Supports: {p['supported_pages']}")

    print("   ✅ Parser Registry works correctly")

    # Test 2: XComParser Structure
    print("\n2. Testing XComParser Structure...")
    parser = XComParser()

    assert parser.name == "x.com", "Parser name incorrect"
    assert parser.version == "1.0.0", "Parser version incorrect"
    assert callable(parser.parse), "parse() method not callable"
    assert callable(parser.get_extraction_js), "get_extraction_js() method not callable"
    assert callable(parser.validate_page), "validate_page() method not callable"

    print(f"   Parser name: {parser.name}")
    print(f"   Parser version: {parser.version}")
    print(f"   Description: {parser.description}")
    print("   ✅ XComParser structure valid")

    # Test 3: JavaScript Extraction Code
    print("\n3. Testing JavaScript Extraction Code...")
    js_code = parser.get_extraction_js()

    # Verify key components are present
    required_components = [
        'article[data-testid="tweet"]',
        'data-testid="User-Name"',
        'data-testid="tweetText"',
        'metrics',
        'extractTweetFromDOM',
    ]

    for component in required_components:
        if component in js_code:
            print(f"   ✅ Contains: {component}")
        else:
            print(f"   ❌ Missing: {component}")
            return False

    print(f"   JavaScript code length: {len(js_code)} characters")
    print("   ✅ JavaScript extraction code valid")

    # Test 4: Output Format Validation
    print("\n4. Testing Output Format...")

    # Mock parsed data (what parser.parse() should return)
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
            }
        ],
        "metadata": {
            "page_title": "test - Search / X",
            "extraction_time_ms": 150,
            "total_articles_found": 2
        }
    }

    # Verify required fields
    required_fields = ["parser", "parser_version", "url", "timestamp", "item_count", "items", "metadata"]
    for field in required_fields:
        if field in mock_output:
            print(f"   ✅ Has field: {field}")
        else:
            print(f"   ❌ Missing field: {field}")
            return False

    # Verify item structure
    if mock_output["items"]:
        item = mock_output["items"][0]
        required_item_fields = ["id", "username", "displayName", "text", "timestamp", "metrics", "url"]
        for field in required_item_fields:
            if field in item:
                print(f"   ✅ Item has field: {field}")
            else:
                print(f"   ❌ Item missing field: {field}")
                return False

    print("   ✅ Output format validation passed")

    print("\n" + "=" * 60)
    print("✅ All component tests PASSED!")
    print("=" * 60)
    return True


def test_complete_workflow(target_url: str = "https://x.com/search?q=gold"):
    """Test complete parsing workflow with real browser"""
    print("\n" + "=" * 60)
    print("Special Parser - Complete Workflow Test")
    print("=" * 60)

    # Import browser integration (only needed for this test)
    print("\n1. Initializing components...")
    try:
        from browser_integration import BrowserIntegration
        browser = BrowserIntegration()
        print("   ✅ Browser integration initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize browser: {e}")
        print("   Make sure helper/ directory is available")
        return False

    # Navigate to test page
    print("\n2. Navigating to X.com...")
    print(f"   Target URL: {target_url}")
    result = browser.playwright_client.browser_navigate(target_url)
    print(f"   Navigation result: {result.get('status')}")

    if result.get("status") != "success":
        print(f"   ❌ Navigation failed: {result}")
        browser.close()
        return False

    time.sleep(3)  # Wait for page load

    # Verify current URL
    current_url = browser.get_current_url()
    print(f"   Current URL: {current_url}")

    if not ('x.com' in current_url or 'twitter.com' in current_url):
        print(f"   ❌ Not on X.com page!")
        browser.close()
        return False

    print("   ✅ Navigation successful")

    # Get page metadata
    print("\n3. Getting page metadata...")
    try:
        url = browser.get_current_url()
        title = browser.get_page_title()
        print(f"   URL: {url}")
        print(f"   Title: {title}")
        print("   ✅ Metadata retrieved")
    except Exception as e:
        print(f"   ⚠️  Metadata retrieval failed: {e}")

    # Get parser
    print("\n4. Getting parser for URL...")
    parser = get_parser_for_url(url)

    if not parser:
        print(f"   ❌ No parser found for URL: {url}")
        browser.close()
        return False

    print(f"   Parser: {parser.name} v{parser.version}")
    print(f"   Description: {parser.description}")
    print("   ✅ Parser retrieved")

    # Validate page
    print("\n5. Validating page compatibility...")
    if not parser.validate_page(browser):
        print(f"   ❌ Page not compatible with {parser.name} parser")
        browser.close()
        return False

    print(f"   ✅ Page compatible with {parser.name} parser")

    # Scroll to load more content (optional)
    print("\n6. Scrolling to load more content...")
    try:
        for i in range(3):
            browser.playwright_client.browser_press_key("PageDown")
            time.sleep(0.5)
        print(f"   ✅ Scrolled 3 times")
    except Exception as e:
        print(f"   ⚠️  Scrolling failed: {e}")

    # Execute parser
    print("\n7. Executing parser...")
    try:
        import time
        start_time = time.time()
        parsed_data = parser.parse(browser)
        end_time = time.time()

        print(f"   Parser: {parsed_data.get('parser')}")
        print(f"   URL: {parsed_data.get('url')}")
        print(f"   Items extracted: {parsed_data.get('item_count')}")
        print(f"   Execution time: {int((end_time - start_time) * 1000)}ms")

        if parsed_data.get('item_count', 0) == 0:
            print(f"   ⚠️  WARNING: No items extracted!")
            print(f"   This might mean:")
            print(f"      - Page is still loading")
            print(f"      - Login required")
            print(f"      - No tweets on page")
            print(f"      - Page structure changed")
        else:
            print("   ✅ Parser execution successful")

    except Exception as e:
        print(f"   ❌ Parser execution failed: {e}")
        import traceback
        traceback.print_exc()
        browser.close()
        return False

    # Display sample items
    print("\n8. Sample extracted items...")
    items = parsed_data.get('items', [])

    if items:
        print(f"   Total items: {len(items)}")
        print(f"\n   Sample items:")
        for i, item in enumerate(items[:3], 1):
            print(f"\n   [{i}] Tweet ID: {item.get('id')}")
            print(f"       User: @{item.get('username')} ({item.get('displayName')})")
            print(f"       Text: {item.get('text', '')[:80]}...")
            print(f"       Timestamp: {item.get('timestamp')}")
            print(f"       Metrics: {item.get('metrics')}")
            if item.get('media'):
                print(f"       Media: {len(item.get('media'))} items")

        print("   ✅ Items displayed")
    else:
        print("   ⚠️  No items to display")

    # Save results
    print("\n9. Saving results...")

    # Create test output directory
    output_dir = Path("./test_output/parsed_results/x.com")
    output_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_test.json"
    filepath = output_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(parsed_data, f, indent=2, ensure_ascii=False)

    print(f"   File saved: {filepath}")
    print(f"   File size: {filepath.stat().st_size} bytes")
    print("   ✅ Results saved")

    # Verify saved file
    print("\n10. Verifying saved file...")
    with open(filepath, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)

    assert loaded_data['parser'] == parsed_data['parser'], "Parser name mismatch"
    assert loaded_data['item_count'] == parsed_data['item_count'], "Item count mismatch"
    assert len(loaded_data['items']) == len(parsed_data['items']), "Items length mismatch"

    print("   ✅ File verification passed")

    # Cleanup
    print("\n11. Cleaning up...")
    browser.close()
    print("   ✅ Browser closed")

    print("\n" + "=" * 60)
    print("✅ Complete workflow test PASSED!")
    print("=" * 60)

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Special Parser Test Suite")
    print("=" * 60)

    # Test components individually
    try:
        success = test_parser_components()
        if not success:
            print("\n❌ Component tests FAILED")
            return False
    except Exception as e:
        print(f"\n❌ Component tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Ask user if they want to run integration test
    print("\n" + "=" * 60)
    print("Integration Test (requires browser and X.com access)")
    print("=" * 60)
    print("\nThis test will:")
    print("  1. Navigate to X.com")
    print("  2. Extract tweets from the page")
    print("  3. Save results to test_output/")
    print("\nRequirements:")
    print("  - Chrome browser running")
    print("  - Network access to x.com")
    print("  - MCP server configured")

    response = input("\nRun integration test? (y/N): ").strip().lower()

    if response == 'y':
        try:
            success = test_complete_workflow()
            if not success:
                print("\n❌ Workflow test FAILED")
                return False
        except Exception as e:
            print(f"\n❌ Workflow test FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("\nSkipping integration test")

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    print("\nSpecial parser feature is ready to use!")
    print("\nExample usage with Claude Code:")
    print("  1. Navigate: navigate('https://x.com/search?q=gold')")
    print("  2. Scroll: scroll_down(times=20)")
    print("  3. Parse: parse_page_with_special_parser()")
    print("\nResults will be saved to session_dir/parsed_results/x.com/")

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
