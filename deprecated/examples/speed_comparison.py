#!/usr/bin/env python3
"""
Speed Profile Comparison Demo

Demonstrates the different speed profiles and their performance characteristics.
"""

import sys
import time
from pathlib import Path

WORKFLOWS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(WORKFLOWS_DIR))

from onepoint3acres_workflow import (
    OnePoint3AcresConfig,
    SpeedProfile,
    SPEED_PROFILES
)


def print_speed_profiles():
    """Print all available speed profiles and their settings."""
    print("\n" + "="*70)
    print("AVAILABLE SPEED PROFILES")
    print("="*70)

    for profile_name, profile in SPEED_PROFILES.items():
        print(f"\n{profile_name.value.upper()}")
        print(f"  Description: {profile['description']}")
        print(f"  Page Load:   {profile['page_load_wait']}s")
        print(f"  Post Wait:   {profile['between_posts_wait']}s")
        print(f"  Page Wait:   {profile['between_pages_wait']}s")

        # Calculate estimated time for 1 page with 10 posts
        total_time = (
            profile['page_load_wait'] +  # Initial page load
            (10 * profile['between_posts_wait']) +  # Wait between posts
            (10 * profile['page_load_wait'])  # Loading each post
        )
        print(f"  Est. Time:   ~{total_time:.1f}s for 10 posts on 1 page")


def demonstrate_speed_profile(speed: str, num_posts: int = 2):
    """
    Demonstrate a specific speed profile.

    Args:
        speed: Speed profile name
        num_posts: Number of posts to scrape for demo
    """
    from onepoint3acres_workflow import scrape_1point3acres

    print(f"\n{'='*70}")
    print(f"TESTING: {speed.upper()} SPEED PROFILE")
    print(f"{'='*70}")

    start_time = time.time()

    result = scrape_1point3acres(
        url="https://www.1point3acres.com/bbs/tag-9407-2.html",
        num_pages=1,
        posts_per_page=num_posts,
        speed=speed,
        output_dir=f"./speed_test_{speed}",
        verbose=False
    )

    duration = time.time() - start_time

    print(f"\nResults for {speed} profile:")
    print(f"  Duration:      {duration:.1f}s")
    print(f"  Posts Parsed:  {result.summary.get('posts_successfully_parsed', 0)}")
    print(f"  Success:       {'✅' if result.success else '❌'}")

    return duration


def compare_all_profiles():
    """Compare all speed profiles."""
    print("\n" + "="*70)
    print("SPEED PROFILE COMPARISON (2 posts each)")
    print("="*70)

    results = {}

    for profile_name in ["fast", "normal", "slow"]:
        try:
            duration = demonstrate_speed_profile(profile_name, num_posts=2)
            results[profile_name] = duration
            time.sleep(2)  # Brief pause between tests
        except Exception as e:
            print(f"❌ Error testing {profile_name}: {e}")
            results[profile_name] = None

    # Print comparison
    print("\n" + "="*70)
    print("COMPARISON SUMMARY")
    print("="*70)

    if all(v is not None for v in results.values()):
        fastest = min(results.values())

        for profile, duration in results.items():
            if duration:
                speed_ratio = duration / fastest
                print(f"{profile:10} -> {duration:5.1f}s ({speed_ratio:.1f}x slower than fastest)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Speed Profile Comparison")
    parser.add_argument("--list", action="store_true", help="List all speed profiles")
    parser.add_argument("--test", choices=["fast", "normal", "slow", "cautious"],
                        help="Test a specific speed profile")
    parser.add_argument("--compare", action="store_true", help="Compare all profiles")
    parser.add_argument("--posts", type=int, default=2, help="Number of posts to test")

    args = parser.parse_args()

    if args.list:
        print_speed_profiles()

    elif args.test:
        demonstrate_speed_profile(args.test, args.posts)

    elif args.compare:
        compare_all_profiles()

    else:
        # Default: show list
        print_speed_profiles()
        print("\n" + "="*70)
        print("Run with --compare to test all profiles")
        print("Run with --test <profile> to test a specific profile")
        print("="*70)
