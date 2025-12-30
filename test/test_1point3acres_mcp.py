#!/usr/bin/env python3
"""
Comprehensive 1point3acres MCP API Test

Tests the full workflow:
1. Navigate to a 1point3acres thread using MCP API
2. Download the page using MCP download_page API
3. Parse with special parser using MCP parse_page_with_special_parser API
4. Validate results and file locations
"""

import sys
import os

# CRITICAL: Set up paths BEFORE any other imports
# Add project root to path (for helper package)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Add src to path
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

# Now safe to import other modules
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Import MCP functions directly
from interactive_web_agent_mcp import (
    navigate,
    download_page,
    parse_page_with_special_parser,
    get_browser
)


async def test_1point3acres_full_workflow():
    """Test complete workflow: navigate -> download -> parse"""

    # Test URL - a real 1point3acres thread
    test_url = "https://www.1point3acres.com/bbs/thread-1157833-1-1.html"

    test_dir = Path(__file__).parent

    print("=" * 80)
    print("1POINT3ACRES MCP API - FULL WORKFLOW TEST")
    print("=" * 80)
    print()
    print(f"Test URL: {test_url}")
    print()

    # STEP 1: Navigate to the page
    print("STEP 1: Navigating to page...")
    print("-" * 80)

    try:
        nav_result = await navigate(url=test_url, wait_seconds=3)

        if not nav_result.get("success"):
            print(f"❌ Navigation failed: {nav_result.get('error')}")
            return False

        print(f"✓ Navigated successfully")
        print(f"  URL: {nav_result.get('url')}")
        print(f"  Title: {nav_result.get('title')}")
        print()

    except Exception as e:
        print(f"❌ Navigation failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    # STEP 2: Download the page
    print("STEP 2: Downloading page using MCP API...")
    print("-" * 80)

    try:
        download_result = await download_page(
            filename=None,  # Auto-generate filename
            include_metadata=True
        )

        if not download_result.get("success"):
            print(f"❌ Download failed: {download_result.get('error')}")
            return False

        download_filepath = download_result.get('filepath')
        print(f"✓ Downloaded successfully")
        print(f"  Filepath: {download_filepath}")
        print(f"  Filename: {download_result.get('filename')}")
        print(f"  Size: {download_result.get('size_bytes')} bytes")
        print(f"  URL: {download_result.get('url')}")
        print()

        # Validate downloaded file exists
        if not Path(download_filepath).exists():
            print(f"❌ Downloaded file does not exist: {download_filepath}")
            return False

        print(f"✓ Verified downloaded file exists")
        print()

    except Exception as e:
        print(f"❌ Download failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    # STEP 3: Parse with special parser
    print("STEP 3: Parsing with special parser using MCP API...")
    print("-" * 80)

    try:
        parse_result = await parse_page_with_special_parser(
            parser_name="auto",  # Auto-detect parser
            save_results=True
        )

        if not parse_result.get("success"):
            print(f"❌ Parsing failed: {parse_result.get('error')}")
            if 'traceback' in parse_result:
                print("Traceback:")
                print(parse_result['traceback'])
            return False

        parse_filepath = parse_result.get('filepath')
        print(f"✓ Parsed successfully")
        print(f"  Parser used: {parse_result.get('parser_used')} v{parse_result.get('parser_version')}")
        print(f"  Items found: {parse_result.get('item_count')}")
        print(f"  Execution time: {parse_result.get('execution_time_ms')}ms")
        print(f"  Results saved to: {parse_filepath}")
        print()

        # Validate parsed results file exists
        if parse_filepath and not Path(parse_filepath).exists():
            print(f"❌ Parsed results file does not exist: {parse_filepath}")
            return False

        if parse_filepath:
            print(f"✓ Verified parsed results file exists")
            print()

        # Load and validate parsed data
        if parse_filepath:
            with open(parse_filepath, 'r', encoding='utf-8') as f:
                parsed_data = json.load(f)

            print("=" * 80)
            print("PARSED DATA VALIDATION")
            print("=" * 80)
            print()

            # Validate structure
            required_fields = ['parser', 'parser_version', 'url', 'timestamp', 'items', 'metadata']
            missing_fields = [field for field in required_fields if field not in parsed_data]

            if missing_fields:
                print(f"❌ Missing required fields: {', '.join(missing_fields)}")
                return False

            print(f"✓ All required fields present")
            print()

            # Validate items
            items = parsed_data.get('items', {})
            main_post = items.get('main_post')
            replies = items.get('replies', [])

            print(f"Main post present: {'✓ Yes' if main_post else '✗ No'}")
            if main_post:
                has_content = bool(main_post.get('content'))
                print(f"Main post has content: {'✓ Yes' if has_content else '✗ No'}")
                if has_content:
                    print(f"  Content length: {len(main_post.get('content', ''))} chars")
                    print(f"  User: {main_post.get('user', {}).get('username', 'N/A')}")
                    print(f"  Post ID: {main_post.get('post_id', 'N/A')}")
                    print(f"  Timestamp: {main_post.get('timestamp', 'N/A')}")
            print()

            print(f"Replies found: {len(replies)}")
            if replies:
                replies_with_content = sum(1 for r in replies if r.get('content'))
                print(f"Replies with content: {replies_with_content}/{len(replies)}")

                # Show first reply with content
                for reply in replies:
                    if reply.get('content'):
                        print()
                        print("First reply with content:")
                        print(f"  User: {reply.get('user', {}).get('username', 'N/A')}")
                        print(f"  Post ID: {reply.get('post_id', 'N/A')}")
                        print(f"  Content length: {len(reply.get('content', ''))} chars")
                        print(f"  Content preview: {reply.get('content', '')[:100]}...")
                        break
            print()

            # Metadata
            metadata = parsed_data.get('metadata', {})
            print("Metadata:")
            print(f"  Thread title: {metadata.get('thread_title', 'N/A')}")
            print(f"  Tags: {', '.join(metadata.get('thread_tags', []))}")
            print(f"  Total replies: {metadata.get('total_replies', 0)}")
            print()

            # Determine success
            total_posts = parsed_data.get('item_count', 0)
            posts_with_content = 0
            if main_post and main_post.get('content'):
                posts_with_content += 1
            posts_with_content += sum(1 for r in replies if r.get('content'))

            print("=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Total posts found: {total_posts}")
            print(f"Posts with content: {posts_with_content}")
            print(f"Download file: {download_filepath}")
            print(f"Parsed results file: {parse_filepath}")
            print()

            if posts_with_content == 0:
                print("⚠️  WARNING - Posts found but no content extracted")
                print("   This might indicate selector mismatch with current forum structure")
                return False

            print("✅ SUCCESS - Content successfully extracted!")
            return True

    except Exception as e:
        print(f"❌ Parsing failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def cleanup():
    """Cleanup browser resources"""
    try:
        browser = get_browser()
        if browser and hasattr(browser, 'close'):
            await browser.close()
    except:
        pass


async def main():
    """Main test function"""
    success = False

    try:
        success = await test_1point3acres_full_workflow()
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await cleanup()

    print()
    print("=" * 80)
    if success:
        print("✅ TEST PASSED - Full MCP workflow successful")
    else:
        print("❌ TEST FAILED - Check errors above")
    print("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
