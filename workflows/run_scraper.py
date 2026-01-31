#!/usr/bin/env python3
"""
Unified Web Scraper - Auto-detects site and uses appropriate parser.

Supports:
- 1point3acres.com - Forum posts with replies
- reddit.com - Subreddit posts with comments

Usage:
    # Reddit - scrape top 5 posts from a subreddit:
    python run_scraper.py "https://www.reddit.com/r/Pennystock/new/" --posts 5

    # 1point3acres - scrape posts from a tag page:
    python run_scraper.py "https://www.1point3acres.com/bbs/tag-9407-1.html" --posts 5

    # Use a config file:
    python run_scraper.py --config my_config.yaml
"""

import sys
import re
import time
import random
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

# Setup paths
WORKFLOWS_DIR = Path(__file__).parent
PROJECT_DIR = WORKFLOWS_DIR.parent
sys.path.insert(0, str(WORKFLOWS_DIR))
sys.path.insert(0, str(PROJECT_DIR / "src"))
sys.path.insert(0, str(PROJECT_DIR / "helper"))
sys.path.insert(0, str(PROJECT_DIR))

from browser_integration import BrowserIntegration
from special_parsers import get_parser_for_url, PARSER_REGISTRY


# Speed profiles (in seconds)
SPEED_PROFILES = {
    "fast": {
        "page_load_wait": 2.0,
        "between_posts_wait": 1.0,
        "between_pages_wait": 1.5,
        "description": "Fast scraping with minimal wait times"
    },
    "normal": {
        "page_load_wait": 3.0,
        "between_posts_wait": 1.5,
        "between_pages_wait": 2.0,
        "description": "Default balanced speed"
    },
    "slow": {
        "page_load_wait": 5.0,
        "between_posts_wait": 2.5,
        "between_pages_wait": 3.0,
        "description": "Slower, more reliable scraping"
    },
    "cautious": {
        "page_load_wait": 8.0,
        "between_posts_wait": 4.0,
        "between_pages_wait": 5.0,
        "description": "Very slow, for unstable connections"
    }
}


def detect_site(url: str) -> Optional[str]:
    """Detect which site the URL belongs to."""
    for name, config in PARSER_REGISTRY.items():
        for pattern in config["patterns"]:
            if re.search(pattern, url, re.IGNORECASE):
                return name
    return None


def is_listing_page(url: str, site: str) -> bool:
    """Determine if URL is a listing/hub page or a detail page."""
    if site == "reddit":
        # Reddit post pages have /comments/ in URL
        return "/comments/" not in url
    elif site == "1point3acres":
        # 1point3acres thread pages have thread- in URL
        return "thread-" not in url
    return True


class UnifiedScraper:
    """Unified scraper that works with multiple sites."""

    def __init__(
        self,
        output_dir: str = "./scraper_output",
        speed: str = "normal",
        verbose: bool = True
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.speed = SPEED_PROFILES.get(speed, SPEED_PROFILES["normal"])
        self.verbose = verbose
        self.browser: Optional[BrowserIntegration] = None

    def log(self, message: str, level: str = "INFO"):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "")
            print(f"[{timestamp}] {prefix} {message}")

    def get_browser(self) -> BrowserIntegration:
        """Get or create browser instance."""
        if self.browser is None:
            self.browser = BrowserIntegration(client_type="chrome")
        return self.browser

    def close(self):
        """Close browser."""
        if self.browser:
            self.browser.close()
            self.browser = None

    def _cleanup_reddit_tabs(self, keep_one: bool = True) -> int:
        """
        Close tabs related to reddit.com to prevent tab accumulation.

        Args:
            keep_one: If True, keep one tab open (the most recent one)

        Returns:
            Number of tabs closed
        """
        try:
            browser = self.get_browser()
            tabs_result = browser.manage_tabs(action="list")
            if not tabs_result.get("success"):
                return 0

            tabs = tabs_result.get("tabs", [])

            # Find tabs with reddit.com in the URL
            domain_tabs = []
            for tab in tabs:
                url = tab.get("url", "")
                if "reddit.com" in url:
                    domain_tabs.append(tab["index"])

            if not domain_tabs:
                return 0

            # If keep_one is True, don't close the last (most recent) tab
            tabs_to_close = domain_tabs[:-1] if keep_one and len(domain_tabs) > 1 else domain_tabs

            if not tabs_to_close:
                return 0

            # Close tabs in reverse order to avoid index shifting issues
            closed_count = 0
            for idx in reversed(tabs_to_close):
                try:
                    browser.manage_tabs(action="close", index=idx)
                    closed_count += 1
                except Exception:
                    pass

            if closed_count > 0:
                self.log(f"Cleaned up {closed_count} tab(s)", "INFO")

            return closed_count

        except Exception as e:
            self.log(f"Tab cleanup warning: {e}", "WARNING")
            return 0

    def navigate(self, url: str, wait_seconds: Optional[float] = None) -> bool:
        """Navigate to URL and wait."""
        wait = wait_seconds or self.speed["page_load_wait"]
        browser = self.get_browser()
        result = browser.playwright_client.browser_navigate(url)
        time.sleep(wait)
        return result.get("status") == "success"

    def parse_current_page(self) -> Optional[Dict]:
        """Parse current page using auto-detected parser."""
        browser = self.get_browser()
        url = browser.get_current_url()
        parser = get_parser_for_url(url)
        if not parser:
            return None
        return parser.parse(browser)

    def scrape_reddit(self, url: str, num_posts: int = 5) -> Dict:
        """
        Scrape Reddit subreddit listing and individual posts.

        Args:
            url: Subreddit listing URL
            num_posts: Number of posts to scrape

        Returns:
            Combined results dict
        """
        results = {
            "site": "reddit",
            "source_url": url,
            "scraped_at": datetime.now().isoformat(),
            "posts": [],
            "summary": {}
        }

        # Step 1: Navigate to listing page
        self.log(f"Navigating to: {url}")
        if not self.navigate(url):
            self.log("Failed to navigate to listing page", "ERROR")
            return results

        # Step 2: Parse listing page to get post links
        self.log("Parsing listing page...")
        listing_data = self.parse_current_page()

        if not listing_data:
            self.log("Failed to parse listing page", "ERROR")
            return results

        # Get posts from listing (items is a list for subreddit pages)
        posts = listing_data.get("items", [])
        if isinstance(posts, dict):
            # If it's a post detail page, items is a dict
            posts = []

        self.log(f"Found {len(posts)} posts on listing page")

        # Limit to requested number
        posts_to_scrape = posts[:num_posts]
        self.log(f"Scraping top {len(posts_to_scrape)} posts")

        # Step 3: Visit each post and parse
        for idx, post in enumerate(posts_to_scrape):
            post_url = post.get("url", "")
            post_title = post.get("title", "Unknown")[:50]

            self.log(f"\n--- Post {idx + 1}/{len(posts_to_scrape)} ---")
            self.log(f"Title: {post_title}...")

            if not post_url:
                self.log("No URL for post, skipping", "WARNING")
                continue

            # Navigate to post
            if not self.navigate(post_url):
                self.log(f"Failed to navigate to post", "WARNING")
                continue

            # Parse post page
            post_data = self.parse_current_page()

            if post_data:
                # Add listing metadata
                post_data["listing_metadata"] = {
                    "index": idx,
                    "listing_score": post.get("score"),
                    "listing_comment_count": post.get("comment_count")
                }
                results["posts"].append(post_data)

                items = post_data.get("items", {})
                comment_count = len(items.get("comments", [])) if isinstance(items, dict) else 0
                self.log(f"Parsed post + {comment_count} comments", "SUCCESS")
            else:
                self.log("Failed to parse post", "WARNING")

            # Clean up tabs after visiting each post
            self._cleanup_reddit_tabs()

            # Wait between posts
            if idx < len(posts_to_scrape) - 1:
                jitter = random.uniform(0.8, 1.2)
                time.sleep(self.speed["between_posts_wait"] * jitter)

        # Final cleanup: close all remaining reddit.com tabs
        self.log("\nFinal cleanup: closing all remaining reddit.com tabs...")
        closed = self._cleanup_reddit_tabs(keep_one=False)
        if closed > 0:
            self.log(f"Final cleanup closed {closed} tab(s)", "SUCCESS")

        # Summary
        results["summary"] = {
            "posts_found": len(posts),
            "posts_scraped": len(results["posts"]),
            "source_url": url
        }

        return results

    def scrape_1point3acres(self, url: str, num_pages: int = 1, posts_per_page: Optional[int] = None) -> Dict:
        """
        Scrape 1point3acres forum posts.

        Args:
            url: Forum/tag page URL
            num_pages: Number of pages to scrape
            posts_per_page: Posts per page to scrape

        Returns:
            Combined results dict
        """
        results = {
            "site": "1point3acres",
            "source_url": url,
            "scraped_at": datetime.now().isoformat(),
            "posts": [],
            "summary": {}
        }

        # Import the existing workflow for 1point3acres
        from onepoint3acres_workflow import OnePoint3AcresWorkflow, OnePoint3AcresConfig

        config = OnePoint3AcresConfig.from_speed_profile(
            base_url=url,
            speed="normal",
            num_pages=num_pages,
            posts_per_page=posts_per_page,
            min_posts_per_page=1,
            verify_post_content=True,
            save_individual_posts=False,  # We'll handle saving
            save_combined_results=False
        )

        workflow = OnePoint3AcresWorkflow(
            config=config,
            client_type="chrome",
            output_dir=str(self.output_dir),
            verbose=self.verbose
        )

        result = workflow.run()

        # Extract posts from workflow result
        if result.success:
            results["posts"] = workflow._parsed_posts
            results["summary"] = result.summary

        return results

    def scrape(self, url: str, num_posts: int = 5, **kwargs) -> Dict:
        """
        Main scrape method - auto-detects site and scrapes accordingly.

        Args:
            url: URL to scrape
            num_posts: Number of posts to scrape
            **kwargs: Additional site-specific options

        Returns:
            Combined results dict
        """
        site = detect_site(url)

        if not site:
            self.log(f"Unknown site for URL: {url}", "ERROR")
            return {"error": "Unknown site", "url": url}

        self.log(f"Detected site: {site}")

        try:
            if site == "reddit":
                return self.scrape_reddit(url, num_posts=num_posts)
            elif site == "1point3acres":
                return self.scrape_1point3acres(
                    url,
                    num_pages=kwargs.get("num_pages", 1),
                    posts_per_page=num_posts
                )
            else:
                self.log(f"Site '{site}' not yet supported for full scraping", "ERROR")
                return {"error": f"Site '{site}' not supported", "url": url}
        finally:
            self.close()

    def save_results(self, results: Dict, filename: Optional[str] = None) -> str:
        """Save results to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            site = results.get("site", "unknown")
            filename = f"{site}_results_{timestamp}.json"

        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return str(filepath.absolute())


def main():
    parser = argparse.ArgumentParser(
        description="Unified Web Scraper - Auto-detects site and uses appropriate parser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Scrape top 5 Reddit posts:
    python run_scraper.py "https://www.reddit.com/r/Pennystock/new/" --posts 5

    # Scrape 1point3acres forum:
    python run_scraper.py "https://www.1point3acres.com/bbs/tag-9407-1.html" --posts 5

    # Fast scraping:
    python run_scraper.py "https://www.reddit.com/r/stocks/hot/" --posts 10 --speed fast

    # Use config file:
    python run_scraper.py --config config.yaml

Supported Sites:
    - reddit.com     - Subreddit listings and post details
    - 1point3acres   - Forum posts and replies

Speed Profiles:
    fast     - Minimal wait times (2.0s page, 1.0s posts)
    normal   - Balanced speed (3.0s page, 1.5s posts) [default]
    slow     - More reliable (5.0s page, 2.5s posts)
    cautious - Very slow (8.0s page, 4.0s posts)
        """
    )
    parser.add_argument("url", nargs='?', help="URL to scrape")
    parser.add_argument("--config", "-c", metavar="FILE", help="Load settings from config file")
    parser.add_argument("--posts", type=int, default=5, help="Number of posts to scrape (default: 5)")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages (for 1point3acres)")
    parser.add_argument("--speed", choices=["fast", "normal", "slow", "cautious"],
                        default="normal", help="Speed profile (default: normal)")
    parser.add_argument("--output", default="./scraper_output", help="Output directory")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")

    args = parser.parse_args()

    # Handle config file mode
    if args.config:
        from config_loader import ConfigLoader
        config = ConfigLoader.load(args.config)
        url = config.get("url")
        if not url:
            print("❌ Config file must specify 'url'")
            return 1
        args.url = url
        args.posts = config.get("posts", config.get("num_posts", args.posts))
        args.pages = config.get("pages", config.get("num_pages", args.pages))
        args.speed = config.get("speed", args.speed)
        args.output = config.get("output", {}).get("directory", args.output)

    # Validate URL
    if not args.url:
        parser.error("URL is required (provide as argument or in config file)")

    # Detect site
    site = detect_site(args.url)
    if not site:
        print(f"❌ Unknown site for URL: {args.url}")
        return 1

    speed_settings = SPEED_PROFILES[args.speed]

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    Web Scraper                               ║
╠══════════════════════════════════════════════════════════════╣
║  Site:   {site}
║  URL:    {args.url[:50]}{"..." if len(args.url) > 50 else ""}
║  Posts:  {args.posts}
║  Speed:  {args.speed} ({speed_settings['description']})
║  Output: {args.output}
╚══════════════════════════════════════════════════════════════╝
""")

    # Create scraper and run
    scraper = UnifiedScraper(
        output_dir=args.output,
        speed=args.speed,
        verbose=not args.quiet
    )

    start_time = datetime.now()
    results = scraper.scrape(
        url=args.url,
        num_posts=args.posts,
        num_pages=args.pages
    )
    duration = (datetime.now() - start_time).total_seconds()

    # Save results
    filepath = scraper.save_results(results)

    # Print summary
    posts_scraped = len(results.get("posts", []))
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                      RESULTS                                 ║
╠══════════════════════════════════════════════════════════════╣
║  Status:       {"✅ SUCCESS" if posts_scraped > 0 else "❌ FAILED"}
║  Duration:     {duration:.1f} seconds
║  Posts Scraped: {posts_scraped}
║  Output:       {filepath}
╚══════════════════════════════════════════════════════════════╝
""")

    return 0 if posts_scraped > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
