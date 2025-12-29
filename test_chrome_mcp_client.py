#!/usr/bin/env python3
"""
Test script for ChromeMcpClient API
Tests various functionalities to ensure the API is working correctly.
"""

import time
import sys
import os

# Add the helper directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'helper'))

from ChromeMcpClient import MCPChromeClient


def print_test_header(test_name):
    """Print a formatted test header"""
    print("\n" + "=" * 60)
    print(f"TEST: {test_name}")
    print("=" * 60)


def print_result(result):
    """Print the result in a formatted way"""
    print(f"Status: {result.get('status', 'unknown')}")
    if result.get('status') == 'error':
        print(f"Error: {result.get('message', 'Unknown error')}")
    else:
        print(f"Result: {result.get('result', result)}")
    print("-" * 60)


def test_get_windows_and_tabs(client):
    """Test getting windows and tabs"""
    print_test_header("Get Windows and Tabs")
    result = client.get_windows_and_tabs()
    print_result(result)
    return result


def test_navigate(client, url):
    """Test navigation"""
    print_test_header(f"Navigate to {url}")
    result = client.chrome_navigate(url=url)
    print_result(result)
    time.sleep(2)  # Wait for page to load
    return result


def test_get_web_content(client):
    """Test getting web content"""
    print_test_header("Get Web Content")
    result = client.chrome_get_web_content(text_content=True)
    print_result(result)
    return result


def test_screenshot(client):
    """Test taking a screenshot"""
    print_test_header("Take Screenshot")
    result = client.chrome_screenshot(
        name="test_screenshot",
        full_page=True,
        save_png=True
    )
    print_result(result)
    return result


def test_get_interactive_elements(client):
    """Test getting interactive elements"""
    print_test_header("Get Interactive Elements")
    result = client.chrome_get_interactive_elements()
    print_result(result)
    return result


def test_browser_evaluate(client):
    """Test JavaScript evaluation (Playwright compatibility)"""
    print_test_header("Browser Evaluate (Get Page Title)")
    result = client.browser_evaluate("() => { return document.title; }")
    print_result(result)
    return result


def test_scroll(client):
    """Test scrolling"""
    print_test_header("Scroll Down")
    result = client.scroll_down(times=2, amount=500)
    print_result(result)

    time.sleep(1)

    print_test_header("Scroll Up")
    result = client.scroll_up(times=2, amount=500)
    print_result(result)
    return result


def test_browser_tabs(client):
    """Test browser tabs management (Playwright compatibility)"""
    print_test_header("List Browser Tabs")
    result = client.browser_tabs(action="list")
    print_result(result)
    return result


def test_click_element(client):
    """Test clicking an element"""
    print_test_header("Get Interactive Elements for Clicking")
    elements = client.chrome_get_interactive_elements(text_query="search")
    print_result(elements)

    # This is just to show the API, actual clicking would need a valid selector
    print("\nNote: Actual element clicking would require a valid CSS selector")
    print("Example: client.chrome_click_element(selector='#search-button')")


def test_fill_form(client):
    """Test filling a form"""
    print_test_header("Fill Form Element")
    print("Note: Actual form filling would require a valid CSS selector")
    print("Example: client.chrome_fill_or_select(selector='#search-input', value='test query')")


def test_history(client):
    """Test browsing history"""
    print_test_header("Get Browser History")
    result = client.chrome_history(max_results=5)
    print_result(result)
    return result


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Chrome MCP Client API Test Suite")
    print("=" * 60)

    try:
        # Initialize the client
        print("\nInitializing Chrome MCP Client...")
        client = MCPChromeClient()
        print("✓ Client initialized successfully")

        # Run tests
        test_get_windows_and_tabs(client)

        # Navigate to a test page
        test_navigate(client, "https://www.example.com")

        # Test getting page content
        test_get_web_content(client)

        # Test screenshot
        test_screenshot(client)

        # Test getting interactive elements
        test_get_interactive_elements(client)

        # Test JavaScript evaluation
        test_browser_evaluate(client)

        # Test scrolling
        test_scroll(client)

        # Test browser tabs
        test_browser_tabs(client)

        # Test element interaction (demonstration)
        test_click_element(client)
        test_fill_form(client)

        # Test history
        test_history(client)

        # Final summary
        print("\n" + "=" * 60)
        print("TEST SUITE COMPLETED")
        print("=" * 60)
        print("\n✓ All basic API tests executed successfully!")
        print("Please review the results above to verify correctness.")

    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Clean up
        if 'client' in locals():
            print("\nClosing Chrome MCP Client...")
            client.close()
            print("✓ Client closed")

    return 0


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
