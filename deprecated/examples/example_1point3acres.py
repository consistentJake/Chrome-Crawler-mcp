#!/usr/bin/env python3
"""
Example: 1Point3Acres Forum Scraper Workflow

This example demonstrates how to use the OnePoint3AcresWorkflow to:
1. Scrape forum posts from a tag page
2. Parse individual posts with the special parser
3. Save results to JSON files

Prerequisites:
- Chrome browser running with remote debugging enabled
- Chrome MCP server available
"""

import sys
from pathlib import Path

# Add workflows directory to path
WORKFLOWS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(WORKFLOWS_DIR))

from onepoint3acres_workflow import (
    OnePoint3AcresWorkflow,
    OnePoint3AcresConfig,
    scrape_1point3acres
)


def example_simple_usage():
    """
    Simple usage with the convenience function.

    This is the easiest way to get started.
    """
    print("=" * 60)
    print("Example 1: Simple Usage with Convenience Function")
    print("=" * 60)

    result = scrape_1point3acres(
        url="https://www.1point3acres.com/bbs/tag/openai-9407-1.html",
        num_pages=1,           # Scrape 1 page
        posts_per_page=3,      # Parse first 3 posts
        output_dir="./output/simple_example",
        verbose=True
    )

    print("\n--- Results ---")
    print(f"Success: {result.success}")
    print(f"Duration: {result.total_duration_ms}ms")
    print(f"Summary: {result.summary}")
    print(f"Output files: {result.output_files}")

    if result.errors:
        print(f"Errors: {result.errors}")

    return result


def example_advanced_usage():
    """
    Advanced usage with full configuration.

    This shows how to customize all workflow settings.
    """
    print("\n" + "=" * 60)
    print("Example 2: Advanced Usage with Full Configuration")
    print("=" * 60)

    # Create detailed configuration
    config = OnePoint3AcresConfig(
        base_url="https://www.1point3acres.com/bbs/tag/openai-9407-1.html",
        num_pages=2,               # Scrape 2 pages
        posts_per_page=5,          # 5 posts per page

        # Timing configuration
        page_load_wait=3.0,        # Wait 3s after page load
        between_posts_wait=1.5,    # Wait 1.5s between posts
        between_pages_wait=2.0,    # Wait 2s between pages

        # Verification settings
        min_posts_per_page=1,      # Expect at least 1 post per page
        verify_post_content=True,  # Verify parsed content

        # Output settings
        save_individual_posts=True,    # Save each post to separate file
        save_combined_results=True     # Save combined results
    )

    # Create workflow instance
    workflow = OnePoint3AcresWorkflow(
        config=config,
        client_type="chrome",          # Use Chrome MCP client
        output_dir="./output/advanced_example",
        verbose=True
    )

    # Run the workflow
    result = workflow.run(
        start_page=1,          # Start from page 1
        resume_from_post=0     # Start from first post
    )

    print("\n--- Results ---")
    print(f"Success: {result.success}")
    print(f"Duration: {result.total_duration_ms}ms")
    print(f"Summary: {result.summary}")

    # Print step details
    print("\n--- Step Details ---")
    for step in result.steps[:10]:  # Show first 10 steps
        status = "✅" if step.success else "❌"
        print(f"  {status} {step.step_name} ({step.duration_ms}ms)")
        for v in step.verifications:
            v_status = "✓" if v.status.value == "passed" else "⚠"
            print(f"      {v_status} {v.name}: {v.message}")

    print(f"\n  ... and {len(result.steps) - 10} more steps" if len(result.steps) > 10 else "")

    return result


def example_multi_tag_scraping():
    """
    Example of scraping multiple tags/topics.
    """
    print("\n" + "=" * 60)
    print("Example 3: Multi-Tag Scraping")
    print("=" * 60)

    # List of tags to scrape
    tags = [
        ("openai", "https://www.1point3acres.com/bbs/tag/openai-9407-1.html"),
        ("anthropic", "https://www.1point3acres.com/bbs/tag/anthropic-11578-1.html"),
        # Add more tags as needed
    ]

    all_results = []

    for tag_name, tag_url in tags[:1]:  # Only run first one for demo
        print(f"\n>>> Scraping tag: {tag_name}")

        result = scrape_1point3acres(
            url=tag_url,
            num_pages=1,
            posts_per_page=2,
            output_dir=f"./output/multi_tag/{tag_name}",
            verbose=True
        )

        all_results.append({
            "tag": tag_name,
            "success": result.success,
            "posts_parsed": result.summary.get("posts_successfully_parsed", 0)
        })

    print("\n--- Multi-Tag Summary ---")
    for r in all_results:
        status = "✅" if r["success"] else "❌"
        print(f"  {status} {r['tag']}: {r['posts_parsed']} posts")


def example_resume_from_failure():
    """
    Example of resuming a workflow from a specific point.

    Useful when a previous run failed partway through.
    """
    print("\n" + "=" * 60)
    print("Example 4: Resume from Failure")
    print("=" * 60)

    config = OnePoint3AcresConfig(
        base_url="https://www.1point3acres.com/bbs/tag/openai-9407-1.html",
        num_pages=1,
        posts_per_page=5
    )

    workflow = OnePoint3AcresWorkflow(
        config=config,
        output_dir="./output/resume_example",
        verbose=True
    )

    # Resume from page 1, post 2 (skipping first 2 posts)
    result = workflow.run(
        start_page=1,
        resume_from_post=2
    )

    print("\n--- Results ---")
    print(f"Success: {result.success}")
    print(f"Posts parsed: {result.summary.get('posts_successfully_parsed', 0)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="1point3acres Workflow Examples")
    parser.add_argument(
        "--example",
        choices=["simple", "advanced", "multi", "resume", "all"],
        default="simple",
        help="Which example to run"
    )

    args = parser.parse_args()

    if args.example == "simple" or args.example == "all":
        example_simple_usage()

    if args.example == "advanced" or args.example == "all":
        example_advanced_usage()

    if args.example == "multi" or args.example == "all":
        example_multi_tag_scraping()

    if args.example == "resume" or args.example == "all":
        example_resume_from_failure()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
