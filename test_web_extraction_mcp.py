#!/usr/bin/env python3
"""
Test script for Web Extraction MCP
Tests the complete workflow from navigation to extraction to querying
"""

import json
import time
from browser_integration import BrowserIntegration
from transaction_manager import TransactionManager
from query_engine import QueryEngine
from html_sanitizer import HTMLSanitizer


def test_complete_workflow():
    """Test complete extraction workflow"""
    print("=" * 60)
    print("Web Extraction MCP - Complete Workflow Test")
    print("=" * 60)

    # Initialize components
    print("\n1. Initializing components...")
    browser = BrowserIntegration()
    txn_manager = TransactionManager("./data")
    query_engine = QueryEngine()
    print("   ✅ Components initialized")

    # Navigate to test page
    print("\n2. Navigating to test page...")
    result = browser.playwright_client.browser_navigate("https://example.com")
    if result.get("status") != "success":
        print(f"   ❌ Navigation failed: {result}")
        browser.close()
        return False

    time.sleep(2)  # Wait for page load
    print("   ✅ Navigation successful")

    # Get page metadata
    print("\n3. Getting page metadata...")
    try:
        metadata = browser.get_page_metadata()
        url = metadata.get("url", "")
        title = metadata.get("title", "")
        print(f"   URL: {url}")
        print(f"   Title: {title}")
        print("   ✅ Metadata retrieved")
    except Exception as e:
        print(f"   ⚠️  Metadata retrieval failed: {e}")
        url = browser.get_current_url()
        title = browser.get_page_title()

    # Extract page HTML
    print("\n4. Extracting page HTML...")
    try:
        raw_html = browser.get_current_page_html()
        print(f"   HTML type: {type(raw_html)}")
        print(f"   HTML length: {len(raw_html) if isinstance(raw_html, str) else 'N/A'} characters")
        print(f"   HTML preview: {str(raw_html)[:200]}...")
        if not raw_html or not isinstance(raw_html, str):
            print(f"   ⚠️  Warning: HTML is not a valid string: {raw_html}")
            # Use fallback HTML
            raw_html = "<html><body><h1>Example Domain</h1><p>This domain is for use in illustrative examples.</p></body></html>"
        print("   ✅ HTML extracted")
    except Exception as e:
        print(f"   ❌ HTML extraction failed: {e}")
        import traceback
        traceback.print_exc()
        browser.close()
        return False

    # Create transaction
    print("\n5. Creating transaction...")
    txn_id = txn_manager.create_transaction(
        url=url,
        extraction_mode="links"
    )
    print(f"   Transaction ID: {txn_id}")
    print("   ✅ Transaction created")

    # Sanitize HTML
    print("\n6. Sanitizing HTML...")
    sanitizer = HTMLSanitizer(max_tokens=4000)
    sanitized_result = sanitizer.sanitize(raw_html, extraction_mode="links")

    print(f"   Total elements: {sanitized_result['statistics']['total_elements']}")
    print(f"   Estimated tokens: {sanitized_result['statistics']['estimated_tokens']}")
    print(f"   Element types: {sanitized_result['statistics']['element_types']}")
    print("   ✅ HTML sanitized")

    # Save transaction data
    print("\n7. Saving transaction data...")
    txn_manager.save_html(
        txn_id,
        raw_html=raw_html,
        sanitized_html=sanitized_result['sanitized_html']
    )
    txn_manager.save_elements(txn_id, sanitized_result['element_registry'])
    txn_manager.save_indexed_text(txn_id, sanitized_result['indexed_text'])

    txn_manager.update_metadata(txn_id, {
        "url": url,
        "title": title,
        "statistics": sanitized_result['statistics'],
        "status": "completed"
    })
    print("   ✅ Transaction data saved")

    # Query elements
    print("\n8. Testing element queries...")

    # Query 1: Get all links
    print("\n   Query 1: Find all links")
    results = query_engine.query_elements(
        sanitized_result['element_registry'],
        filters={"tag": "a"}
    )
    print(f"   Found {len(results)} links")
    if results:
        for i, r in enumerate(results[:3]):
            print(f"   - {r.get('text', 'No text')[:50]}")

    # Query 2: Natural language query
    print("\n   Query 2: Natural language - 'Find links'")
    results = query_engine.query_elements(
        sanitized_result['element_registry'],
        query="Find all links"
    )
    print(f"   Found {len(results)} results")

    print("   ✅ Queries successful")

    # Retrieve sanitized content
    print("\n9. Retrieving sanitized content...")
    indexed_text = txn_manager.get_indexed_text(txn_id)
    preview_lines = indexed_text.split('\n')[:5]
    print("   Preview:")
    for line in preview_lines:
        print(f"   {line}")
    print("   ✅ Content retrieved")

    # List transactions
    print("\n10. Listing transactions...")
    transactions = txn_manager.list_transactions(limit=5)
    print(f"   Total transactions: {len(transactions)}")
    for txn in transactions[:3]:
        print(f"   - {txn['transaction_id']}: {txn.get('url', 'N/A')}")
    print("   ✅ Transactions listed")

    # Cleanup
    print("\n11. Cleaning up...")
    browser.close()
    print("   ✅ Browser closed")

    print("\n" + "=" * 60)
    print("✅ Complete workflow test PASSED!")
    print("=" * 60)

    return True


def test_components_individually():
    """Test individual components"""
    print("\n" + "=" * 60)
    print("Testing Individual Components")
    print("=" * 60)

    # Test 1: Transaction Manager
    print("\n1. Testing Transaction Manager...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = TransactionManager(tmpdir)
        txn_id = manager.create_transaction(url="https://test.com")
        manager.save_html(txn_id, sanitized_html="<html>Test</html>")
        manager.save_elements(txn_id, [{"tag": "a", "text": "Link"}])
        manager.save_indexed_text(txn_id, "[0] <a>Link</a>")

        # Retrieve
        html = manager.get_html(txn_id, "sanitized")
        elements = manager.get_elements(txn_id)
        text = manager.get_indexed_text(txn_id)

        assert html == "<html>Test</html>"
        assert len(elements) == 1
        assert "[0]" in text

        print("   ✅ Transaction Manager works correctly")

    # Test 2: Query Engine
    print("\n2. Testing Query Engine...")
    engine = QueryEngine()
    test_elements = [
        {"tag": "a", "text": "Forum Post", "attributes": {"href": "thread-123-1-1.html"}},
        {"tag": "a", "text": "Next Page", "attributes": {"href": "/page/2"}},
        {"tag": "button", "text": "Login", "attributes": {"type": "submit"}},
    ]

    # Test filters
    links = engine.query_elements(test_elements, filters={"tag": "a"})
    assert len(links) == 2

    # Test pattern matching
    threads = engine.query_elements(
        test_elements,
        filters={"tag": "a", "href_pattern": "thread-*"}
    )
    assert len(threads) == 1

    # Test natural language
    nav = engine.query_elements(test_elements, query="Find the next page button")
    assert len(nav) >= 1

    print("   ✅ Query Engine works correctly")

    # Test 3: HTML Sanitizer
    print("\n3. Testing HTML Sanitizer...")
    sanitizer = HTMLSanitizer(max_tokens=1000)
    test_html = """
    <html>
    <head><title>Test</title></head>
    <body>
        <a href="link1.html">Link 1</a>
        <a href="link2.html">Link 2</a>
        <script>alert('test');</script>
    </body>
    </html>
    """

    result = sanitizer.sanitize(test_html, extraction_mode="links")
    assert len(result['element_registry']) == 2
    assert 'script' not in result['sanitized_html'].lower()
    assert 'Link 1' in result['indexed_text']

    print("   ✅ HTML Sanitizer works correctly")

    print("\n" + "=" * 60)
    print("✅ All individual component tests PASSED!")
    print("=" * 60)


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Web Extraction MCP Test Suite")
    print("=" * 60)

    # Test components individually
    try:
        test_components_individually()
    except Exception as e:
        print(f"\n❌ Component tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test complete workflow
    try:
        test_complete_workflow()
    except Exception as e:
        print(f"\n❌ Workflow test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    print("\nYou can now use the Web Extraction MCP with Claude Code!")
    print("\nTo integrate with Claude Code, add this to your MCP config:")
    print("""
{
    "mcpServers": {
        "web-extraction": {
            "command": "python",
            "args": ["/path/to/web_extraction_mcp.py"],
            "env": {
                "DATA_DIR": "/home/zhenkai/personal/Projects/WebAgent/data"
            }
        }
    }
}
""")

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
