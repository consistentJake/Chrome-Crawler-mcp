#!/usr/bin/env python3
"""
Demo script showing how to close all tabs matching a URL pattern using BrowserIntegration.

This demonstrates the correct API usage for the manage_tabs() method.
"""

import sys
import os

# Add src directory to path (script is at project root)
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "src")
sys.path.insert(0, src_dir)

from browser_integration import BrowserIntegration


def close_tabs_by_url_pattern(browser: BrowserIntegration, url_pattern: str) -> dict:
    """
    Close all tabs whose URL contains the specified pattern.
    
    Args:
        browser: BrowserIntegration instance
        url_pattern: URL pattern to match (e.g., "1point3acres.com")
    
    Returns:
        Dictionary with operation results:
        {
            "success": bool,
            "tabs_found": int,
            "tabs_closed": int,
            "errors": list of error messages
        }
    """
    result = {
        "success": True,
        "tabs_found": 0,
        "tabs_closed": 0,
        "errors": []
    }
    
    # Step 1: List all tabs
    print(f"[1/3] Listing all tabs...")
    list_result = browser.manage_tabs(action="list")

    if not list_result.get("success"):
        result["success"] = False
        result["errors"].append(f"Failed to list tabs: {list_result.get('error', 'Unknown error')}")
        return result

    tabs = list_result.get("tabs", [])
    print(f"      Found {len(tabs)} total tabs")
    
    # Step 2: Filter tabs by URL pattern
    print(f"[2/3] Filtering tabs by URL pattern: '{url_pattern}'")
    matching_tabs = [tab for tab in tabs if url_pattern in tab.get("url", "")]
    result["tabs_found"] = len(matching_tabs)
    
    if not matching_tabs:
        print(f"      No tabs match the pattern '{url_pattern}'")
        return result
    
    print(f"      Found {len(matching_tabs)} tabs matching pattern:")
    for tab in matching_tabs:
        print(f"        - [{tab['index']}] {tab['title'][:50]}...")
    
    # Step 3: Close matching tabs (from highest index to lowest to avoid index shifting)
    print(f"[3/3] Closing {len(matching_tabs)} matching tabs...")
    
    # Sort by index in descending order to avoid index shifting issues
    matching_tabs_sorted = sorted(matching_tabs, key=lambda t: t["index"], reverse=True)
    
    for tab in matching_tabs_sorted:
        index = tab["index"]
        title = tab["title"][:50]
        
        print(f"      Closing tab [{index}]: {title}...")
        close_result = browser.manage_tabs(action="close", index=index)
        
        if close_result.get("success"):
            result["tabs_closed"] += 1
            print(f"      ✅ Closed tab [{index}]")
        else:
            error_msg = f"Failed to close tab [{index}]: {close_result.get('error', 'Unknown error')}"
            result["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Cleanup Summary:")
    print(f"  - Tabs found matching '{url_pattern}': {result['tabs_found']}")
    print(f"  - Tabs successfully closed: {result['tabs_closed']}")
    if result["errors"]:
        print(f"  - Errors: {len(result['errors'])}")
        for error in result["errors"]:
            print(f"    • {error}")
    print(f"{'='*60}\n")
    
    return result


def main():
    """Main function to demonstrate tab cleanup"""
    print("="*60)
    print("Tab Cleanup Demo - Using BrowserIntegration.manage_tabs()")
    print("="*60)
    print()
    
    # Initialize browser integration with Chrome client
    print("Initializing BrowserIntegration with Chrome client...")
    browser = BrowserIntegration(client_type="chrome")
    print("✅ BrowserIntegration initialized\n")
    
    # Close all tabs from 1point3acres.com
    result = close_tabs_by_url_pattern(browser, "1point3acres.com")
    
    # Check if operation was successful
    if result["success"] and result["tabs_closed"] > 0:
        print("✅ Tab cleanup completed successfully!")
    elif result["success"] and result["tabs_closed"] == 0:
        print("ℹ️  No tabs needed to be closed")
    else:
        print("⚠️  Tab cleanup completed with errors")
    
    return 0 if result["success"] else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
