#!/usr/bin/env python3
"""
Test script to verify multi-page post parsing.
Tests with: https://www.1point3acres.com/bbs/thread-1160582-1-1.html
"""

import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflows.onepoint3acres_workflow import scrape_1point3acres

def test_multipage_post():
    """Test parsing a multi-page post."""

    # Test URL - this post has 2 pages
    test_url = "https://www.1point3acres.com/bbs/thread-1160582-1-1.html"

    print("="*60)
    print("Testing Multi-Page Post Parsing")
    print("="*60)
    print(f"URL: {test_url}")
    print()

    # We'll process just this one post by creating a minimal workflow
    # that directly targets the post URL
    from workflows.onepoint3acres_workflow import OnePoint3AcresWorkflow, OnePoint3AcresConfig

    # Create a config that targets just this post
    # We'll manually process it
    config = OnePoint3AcresConfig(
        base_url=test_url,
        num_pages=1,
        posts_per_page=1,
        page_load_wait=3.0,
        between_posts_wait=1.5
    )

    workflow = OnePoint3AcresWorkflow(
        config=config,
        output_dir="./test_output",
        verbose=True
    )

    try:
        # Manually process the single post
        post_link = {
            "href": "thread-1160582-1-1.html",
            "text": "Test Multi-Page Post",
            "full_url": test_url
        }

        result = workflow._process_single_post(
            post_link=post_link,
            page_num=1,
            post_idx=0
        )

        if result.success:
            print("\n" + "="*60)
            print("SUCCESS!")
            print("="*60)

            data = result.data
            pagination_summary = data.get("pagination_summary", {})
            total_pages = pagination_summary.get("total_pages_parsed", 1)

            print(f"\nTotal pages parsed: {total_pages}")
            print(f"Total items: {data.get('item_count', 0)}")

            items = data.get("items", {})
            main_post = items.get("main_post", {})
            replies = items.get("replies", [])

            print(f"Main post: {'Yes' if main_post else 'No'}")
            print(f"Replies: {len(replies)}")

            if pagination_summary:
                print(f"\nPages URLs:")
                for url in pagination_summary.get("pages_urls", []):
                    print(f"  - {url}")

            print(f"\nDuration: {result.duration_ms}ms")

            # Save result
            workflow.save_results(
                data=data,
                filename="test_multipage_result.json",
                subfolder="test"
            )
            print("\nResult saved to: test_output/test/test_multipage_result.json")

        else:
            print("\n" + "="*60)
            print("FAILED!")
            print("="*60)
            print(f"Error: {result.error}")

    except Exception as e:
        import traceback
        print(f"\nException occurred: {e}")
        traceback.print_exc()
    finally:
        workflow.close()

if __name__ == "__main__":
    test_multipage_post()
