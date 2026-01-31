"""
1Point3Acres Forum Scraper Workflow.

Automates the process of:
1. Navigating to a tag/topic page
2. Extracting all post links
3. Visiting each post and parsing with special parser
4. Supporting pagination across multiple pages
"""

import re
import time
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

from base_workflow import (
    BaseWorkflow,
    WorkflowResult,
    StepResult,
    VerificationResult,
    VerificationStatus
)


class SpeedProfile(Enum):
    """Speed profiles for controlling page load and navigation timing."""
    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"
    CAUTIOUS = "cautious"


# Speed profile configurations (in seconds)
SPEED_PROFILES = {
    SpeedProfile.FAST: {
        "page_load_wait": 1.5,
        "between_posts_wait": 0.5,
        "between_pages_wait": 1.0,
        "description": "Fast scraping with minimal wait times"
    },
    SpeedProfile.NORMAL: {
        "page_load_wait": 3.0,
        "between_posts_wait": 1.5,
        "between_pages_wait": 2.0,
        "description": "Default balanced speed"
    },
    SpeedProfile.SLOW: {
        "page_load_wait": 5.0,
        "between_posts_wait": 2.5,
        "between_pages_wait": 3.0,
        "description": "Slower, more reliable scraping"
    },
    SpeedProfile.CAUTIOUS: {
        "page_load_wait": 8.0,
        "between_posts_wait": 4.0,
        "between_pages_wait": 5.0,
        "description": "Very slow, for unstable connections"
    }
}


@dataclass
class OnePoint3AcresConfig:
    """Configuration for 1point3acres scraper workflow."""

    # Target URL (tag page, forum page, etc.)
    base_url: str

    # Number of pages to scrape (1 = current page only)
    num_pages: int = 1

    # Number of posts to parse per page (None = all posts)
    posts_per_page: Optional[int] = None

    # Speed profile (overrides individual wait times if set)
    speed_profile: Optional[SpeedProfile] = None

    # Wait times (used if speed_profile is None)
    page_load_wait: float = 3.0
    between_posts_wait: float = 1.5
    between_pages_wait: float = 2.0

    # Verification settings
    min_posts_per_page: int = 1
    verify_post_content: bool = True

    # Output settings
    save_individual_posts: bool = True
    save_combined_results: bool = True

    def __post_init__(self):
        """Apply speed profile if specified."""
        if self.speed_profile:
            profile = SPEED_PROFILES[self.speed_profile]
            self.page_load_wait = profile["page_load_wait"]
            self.between_posts_wait = profile["between_posts_wait"]
            self.between_pages_wait = profile["between_pages_wait"]

    @classmethod
    def from_speed_profile(
        cls,
        base_url: str,
        speed: str = "normal",
        num_pages: int = 1,
        posts_per_page: Optional[int] = None,
        **kwargs
    ) -> "OnePoint3AcresConfig":
        """
        Create config from a speed profile name.

        Args:
            base_url: URL to scrape
            speed: Speed profile name ("fast", "normal", "slow", "cautious")
            num_pages: Number of pages to scrape
            posts_per_page: Posts per page to parse
            **kwargs: Additional config options

        Returns:
            OnePoint3AcresConfig instance
        """
        speed_profile = SpeedProfile(speed.lower())
        return cls(
            base_url=base_url,
            num_pages=num_pages,
            posts_per_page=posts_per_page,
            speed_profile=speed_profile,
            **kwargs
        )


class OnePoint3AcresWorkflow(BaseWorkflow):
    """
    Workflow for scraping 1point3acres forum posts.

    Supports:
    - Tag pages (e.g., /tag/openai-9407-1.html)
    - Forum pages (e.g., /forum-145-1.html)
    - Multi-page scraping with pagination
    - Individual post parsing with special parser
    """

    @property
    def name(self) -> str:
        return "1point3acres_forum_scraper"

    def __init__(
        self,
        config: OnePoint3AcresConfig,
        client_type: str = "chrome",
        output_dir: Optional[str] = None,
        verbose: bool = True
    ):
        """
        Initialize workflow.

        Args:
            config: Workflow configuration
            client_type: Browser client type
            output_dir: Output directory for results
            verbose: Print progress messages
        """
        super().__init__(
            client_type=client_type,
            output_dir=output_dir or "./1point3acres_output",
            wait_between_steps=config.between_posts_wait,
            verbose=verbose
        )
        self.config = config

        # Results tracking
        self._all_post_links: List[Dict] = []
        self._parsed_posts: List[Dict] = []
        self._pages_processed: int = 0

    def run(self, **kwargs) -> WorkflowResult:
        """
        Execute the 1point3acres scraping workflow.

        Kwargs:
            start_page: Page number to start from (default: auto-detect from URL or 1)
            resume_from_post: Post index to resume from (default: 0)

        Returns:
            WorkflowResult with complete execution details
        """
        start_time = datetime.now()
        self._steps = []
        self._errors = []
        output_files = []

        # Auto-detect start page from URL if not explicitly provided
        if "start_page" not in kwargs:
            start_page = self._extract_page_number_from_url()
        else:
            start_page = kwargs.get("start_page")

        resume_from_post = kwargs.get("resume_from_post", 0)

        try:
            self.log(f"Starting 1point3acres scraper workflow", "INFO")
            self.log(f"Base URL: {self.config.base_url}")
            self.log(f"Pages to scrape: {self.config.num_pages}")
            self.log(f"Posts per page: {self.config.posts_per_page or 'all'}")

            # Process each page
            for page_num in range(start_page, start_page + self.config.num_pages):
                self.log(f"\n{'='*50}")
                self.log(f"Processing page {page_num} of {start_page + self.config.num_pages - 1}")
                self.log(f"{'='*50}")

                # Step 1: Navigate to the page
                page_url = self._get_page_url(page_num)
                nav_result = self.navigate(
                    url=page_url,
                    wait_seconds=self.config.page_load_wait,
                    verify_url_contains="1point3acres"
                )
                self._add_step(nav_result)

                if not nav_result.success:
                    self.log(f"Failed to navigate to page {page_num}", "ERROR")
                    continue

                # Step 2: Extract page content
                content_result = self.get_page_content(
                    min_elements=10,
                    expected_element_types=["a"]
                )
                self._add_step(content_result)

                if not content_result.success:
                    self.log("Failed to extract page content", "ERROR")
                    continue

                # Step 3: Find all post links
                post_links_result = self._find_post_links()
                self._add_step(post_links_result)

                if not post_links_result.success:
                    self.log("Failed to find post links", "ERROR")
                    continue

                post_links = post_links_result.data.get("post_links", [])
                self.log(f"Found {len(post_links)} post links on page {page_num}")

                # Limit posts per page if configured
                if self.config.posts_per_page:
                    post_links = post_links[:self.config.posts_per_page]
                    self.log(f"Limited to first {len(post_links)} posts")

                # Step 4: Process each post
                start_idx = resume_from_post if page_num == start_page else 0
                for idx, post_link in enumerate(post_links[start_idx:], start=start_idx):
                    self.log(f"\n--- Processing post {idx + 1}/{len(post_links)} ---")

                    parse_result = self._process_single_post(
                        post_link=post_link,
                        page_num=page_num,
                        post_idx=idx
                    )
                    self._add_step(parse_result)

                    if parse_result.success:
                        parsed_data = parse_result.data
                        self._parsed_posts.append(parsed_data)

                        # Save individual post if configured
                        if self.config.save_individual_posts:
                            filename = self._generate_post_filename(post_link, page_num, idx)
                            save_result = self.save_results(
                                data=parsed_data,
                                filename=filename,
                                subfolder="posts"
                            )
                            if save_result.success:
                                output_files.append(save_result.data["filepath"])

                    # Wait between posts
                    if idx < len(post_links) - 1:
                        self.wait(self.config.between_posts_wait)

                self._pages_processed += 1

                # Clean up tabs after each page to prevent accumulation
                self._cleanup_domain_tabs()

                # Wait between pages with jitter
                if page_num < start_page + self.config.num_pages - 1:
                    # Add jitter: 0.7x to 1.5x of the configured wait time
                    jitter_multiplier = random.uniform(0.7, 1.5)
                    jittered_wait = self.config.between_pages_wait * jitter_multiplier
                    self.log(f"\nWaiting {jittered_wait:.1f}s before next page (base: {self.config.between_pages_wait}s)...")
                    self.wait(jittered_wait)

            # Save combined results if configured
            if self.config.save_combined_results and self._parsed_posts:
                combined_data = self._create_combined_results()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_result = self.save_results(
                    data=combined_data,
                    filename=f"combined_results_{timestamp}.json"
                )
                if save_result.success:
                    output_files.append(save_result.data["filepath"])

            # Create summary
            summary = {
                "pages_processed": self._pages_processed,
                "total_post_links_found": len(self._all_post_links),
                "posts_successfully_parsed": len(self._parsed_posts),
                "posts_failed": len(self._all_post_links) - len(self._parsed_posts)
            }

            success = self._pages_processed > 0 and len(self._parsed_posts) > 0

            self.log(f"\n{'='*50}")
            self.log(f"Workflow completed!", "SUCCESS" if success else "WARNING")
            self.log(f"Pages processed: {self._pages_processed}")
            self.log(f"Posts parsed: {len(self._parsed_posts)}")
            self.log(f"Output files: {len(output_files)}")

            return self._create_workflow_result(
                success=success,
                start_time=start_time,
                summary=summary,
                output_files=output_files
            )

        except Exception as e:
            import traceback
            self.log(f"Workflow failed with error: {e}", "ERROR")
            self._errors.append(str(e))

            return self._create_workflow_result(
                success=False,
                start_time=start_time,
                summary={"error": str(e), "traceback": traceback.format_exc()},
                output_files=output_files
            )

        finally:
            # Final cleanup: close all remaining tabs related to 1point3acres.com
            self.log("\nFinal cleanup: closing all remaining 1point3acres.com tabs...", "INFO")
            closed = self._cleanup_domain_tabs(keep_one=False)
            if closed > 0:
                self.log(f"Final cleanup closed {closed} tab(s)", "SUCCESS")

            self.close()

    def _extract_page_number_from_url(self) -> int:
        """
        Extract page number from the base URL.

        Returns:
            Page number from URL, or 1 if not found
        """
        base_url = self.config.base_url

        # Pattern: tag-9407-2.html or forum-145-3.html
        pattern = r'(tag|forum)-(\d+)-(\d+)\.html'
        match = re.search(pattern, base_url)

        if match:
            return int(match.group(3))

        # Pattern: /bbs/tag/openai-9407-2.html
        pattern2 = r'/bbs/tag/[^/]+-\d+-(\d+)\.html'
        match2 = re.search(pattern2, base_url)

        if match2:
            return int(match2.group(1))

        # Default to page 1
        return 1

    def _get_page_url(self, page_num: int) -> str:
        """
        Generate URL for a specific page number.

        Handles different URL patterns:
        - tag-{id}-{page}.html
        - forum-{id}-{page}.html
        """
        base_url = self.config.base_url

        # Pattern: tag-9407-1.html or forum-145-1.html
        pattern = r'(tag|forum)-(\d+)-(\d+)\.html'
        match = re.search(pattern, base_url)

        if match:
            page_type, page_id, _ = match.groups()
            return re.sub(pattern, f'{page_type}-{page_id}-{page_num}.html', base_url)

        # Pattern: /bbs/tag/openai-9407-1.html
        pattern2 = r'(/bbs/tag/[^/]+-\d+-)(\d+)(\.html)'
        match2 = re.search(pattern2, base_url)

        if match2:
            prefix, _, suffix = match2.groups()
            return re.sub(pattern2, f'{prefix}{page_num}{suffix}', base_url)

        # Fallback: append page parameter
        if '?' in base_url:
            return f"{base_url}&page={page_num}"
        else:
            return f"{base_url}?page={page_num}"

    def _find_post_links(self) -> StepResult:
        """
        Find all forum post links on the current page.

        Returns:
            StepResult with list of post links
        """
        start_time = time.time()
        verifications = []

        self.log("Finding post links...")

        try:
            # Query for thread links using multiple patterns
            thread_pattern = "thread-*"
            query_result = self.query_elements(
                filters={"tag": "a", "href_pattern": thread_pattern}
            )

            if not query_result.success:
                return StepResult(
                    step_name="find_post_links",
                    success=False,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=query_result.error
                )

            all_matches = query_result.data.get("matches", [])

            # Deduplicate and filter post links
            seen_hrefs = set()
            post_links = []

            for elem in all_matches:
                href = elem.get("attributes", {}).get("href", "")
                text = elem.get("text", "").strip()

                # Skip empty text or pure numbers (reply counts)
                if not text or text.isdigit():
                    continue

                # Skip already seen links
                if href in seen_hrefs:
                    continue

                # Skip non-post links
                if not re.match(r'thread-\d+-\d+-\d+\.html', href):
                    continue

                seen_hrefs.add(href)
                post_links.append({
                    "href": href,
                    "text": text[:100],  # Truncate long titles
                    "web_agent_id": elem.get("web_agent_id"),
                    "full_url": self._make_full_url(href)
                })

            # Store for later reference
            self._all_post_links.extend(post_links)

            # Verify minimum posts
            if len(post_links) >= self.config.min_posts_per_page:
                verifications.append(VerificationResult(
                    name="min_posts",
                    status=VerificationStatus.PASSED,
                    message=f"Found {len(post_links)} posts (min: {self.config.min_posts_per_page})"
                ))
            else:
                verifications.append(VerificationResult(
                    name="min_posts",
                    status=VerificationStatus.WARNING,
                    message=f"Found only {len(post_links)} posts (min: {self.config.min_posts_per_page})"
                ))

            self.log(f"Found {len(post_links)} unique post links", "SUCCESS")

            return StepResult(
                step_name="find_post_links",
                success=True,
                duration_ms=int((time.time() - start_time) * 1000),
                data={"post_links": post_links, "count": len(post_links)},
                verifications=verifications
            )

        except Exception as e:
            return StepResult(
                step_name="find_post_links",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def _process_single_post(
        self,
        post_link: Dict,
        page_num: int,
        post_idx: int
    ) -> StepResult:
        """
        Navigate to and parse a single post, handling multi-page posts.

        Args:
            post_link: Post link dictionary
            page_num: Source page number
            post_idx: Post index on page

        Returns:
            StepResult with parsed post data (combined from all pages if multi-page)
        """
        start_time = time.time()
        verifications = []

        post_url = post_link.get("full_url", "")
        post_title = post_link.get("text", "Unknown")

        self.log(f"Processing: {post_title[:50]}...")

        try:
            # Storage for multi-page post data
            all_pages_data = []
            current_page = 1
            total_pages_found = 0

            # Navigate to first page of the post
            nav_result = self.navigate(
                url=post_url,
                wait_seconds=self.config.page_load_wait,
                verify_url_contains="thread"
            )

            if not nav_result.success:
                return StepResult(
                    step_name="process_post",
                    success=False,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=f"Navigation failed: {nav_result.error}"
                )

            # Verify we're on the right page
            current_url = self.browser.get_current_url()
            if "thread" not in current_url:
                verifications.append(VerificationResult(
                    name="url_verification",
                    status=VerificationStatus.FAILED,
                    message=f"Not on thread page: {current_url}"
                ))
                return StepResult(
                    step_name="process_post",
                    success=False,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error="Failed to navigate to thread page",
                    verifications=verifications
                )

            # Loop to handle multi-page posts
            while True:
                self.log(f"Parsing page {current_page} of post...")

                # Parse current page with special parser
                parse_result = self.parse_page_with_parser(
                    parser_name="1point3acres",
                    verify_min_items=1
                )

                if not parse_result.success:
                    self.log(f"Parse failed on page {current_page}: {parse_result.error}", "WARNING")
                    break

                parsed_data = parse_result.data
                all_pages_data.append(parsed_data)

                # Check pagination info
                pagination = parsed_data.get("pagination", {})
                has_next_page = pagination.get("has_next_page", False)
                next_page_url = pagination.get("next_page_url")
                total_pages = pagination.get("total_pages", 1)

                if total_pages:
                    total_pages_found = max(total_pages_found, total_pages)

                self.log(f"Page {current_page} parsed. Has next page: {has_next_page}")

                # If there's a next page, navigate to it
                if has_next_page and next_page_url:
                    current_page += 1

                    # Build full URL for next page
                    if not next_page_url.startswith("http"):
                        next_page_url = self._make_full_url(next_page_url)

                    self.log(f"Navigating to page {current_page}...")

                    # Navigate to next page
                    nav_result = self.navigate(
                        url=next_page_url,
                        wait_seconds=self.config.page_load_wait,
                        verify_url_contains="thread"
                    )

                    if not nav_result.success:
                        self.log(f"Failed to navigate to page {current_page}", "WARNING")
                        break

                    # Wait a bit before parsing next page
                    self.wait(self.config.between_posts_wait)
                else:
                    # No more pages
                    break

            # Combine data from all pages
            if not all_pages_data:
                return StepResult(
                    step_name="process_post",
                    success=False,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error="No data parsed from any page"
                )

            combined_data = self._combine_multi_page_data(all_pages_data)

            # Verify content if configured
            if self.config.verify_post_content:
                items = combined_data.get("items", {})
                main_post = items.get("main_post", {})
                replies = items.get("replies", [])

                if main_post and main_post.get("content"):
                    verifications.append(VerificationResult(
                        name="has_main_post",
                        status=VerificationStatus.PASSED,
                        message="Main post content extracted"
                    ))
                else:
                    verifications.append(VerificationResult(
                        name="has_main_post",
                        status=VerificationStatus.WARNING,
                        message="Main post content is empty"
                    ))

                verifications.append(VerificationResult(
                    name="reply_count",
                    status=VerificationStatus.PASSED,
                    message=f"Found {len(replies)} replies across {len(all_pages_data)} page(s)"
                ))

            # Add metadata
            combined_data["workflow_metadata"] = {
                "source_page": page_num,
                "post_index": post_idx,
                "original_link": post_link,
                "processed_at": datetime.now().isoformat(),
                "total_pages_in_post": len(all_pages_data),
                "pages_data_count": len(all_pages_data)
            }

            self.log(f"Parsed {combined_data.get('item_count', 0)} items from {len(all_pages_data)} page(s)", "SUCCESS")

            return StepResult(
                step_name="process_post",
                success=True,
                duration_ms=int((time.time() - start_time) * 1000),
                data=combined_data,
                verifications=verifications
            )

        except Exception as e:
            import traceback
            return StepResult(
                step_name="process_post",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )

    def _make_full_url(self, href: str) -> str:
        """Convert relative href to full URL."""
        if href.startswith("http"):
            return href
        return f"https://www.1point3acres.com/bbs/{href}"

    def _cleanup_domain_tabs(self, keep_one: bool = True) -> int:
        """
        Close tabs related to 1point3acres.com to prevent tab accumulation.

        Args:
            keep_one: If True, keep one tab open (the most recent one)

        Returns:
            Number of tabs closed
        """
        try:
            tabs_result = self.browser.manage_tabs(action="list")
            if not tabs_result.get("success"):
                return 0

            tabs = tabs_result.get("tabs", [])

            # Find tabs with 1point3acres.com in the URL
            domain_tabs = []
            for tab in tabs:
                url = tab.get("url", "")
                if "1point3acres.com" in url:
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
                    self.browser.manage_tabs(action="close", index=idx)
                    closed_count += 1
                except Exception:
                    pass

            if closed_count > 0:
                self.log(f"Cleaned up {closed_count} tab(s)", "INFO")

            return closed_count

        except Exception as e:
            self.log(f"Tab cleanup warning: {e}", "WARNING")
            return 0

    def _combine_multi_page_data(self, all_pages_data: List[Dict]) -> Dict:
        """
        Combine data from multiple pages of the same post.

        Args:
            all_pages_data: List of parsed data from each page

        Returns:
            Combined data dictionary
        """
        if not all_pages_data:
            return {}

        if len(all_pages_data) == 1:
            return all_pages_data[0]

        # Use first page as base
        combined = all_pages_data[0].copy()

        # Combine replies from all pages
        all_replies = []
        main_post = None

        for page_idx, page_data in enumerate(all_pages_data):
            items = page_data.get("items", {})

            # Main post should only come from first page
            if page_idx == 0:
                main_post = items.get("main_post")

            # Add replies from all pages
            replies = items.get("replies", [])
            all_replies.extend(replies)

        # Update combined data
        combined["items"] = {
            "main_post": main_post,
            "replies": all_replies
        }
        combined["item_count"] = len(all_replies) + (1 if main_post else 0)

        # Update metadata
        if "metadata" in combined:
            combined["metadata"]["total_replies"] = len(all_replies)
            combined["metadata"]["total_pages"] = len(all_pages_data)

        # Add pagination summary
        combined["pagination_summary"] = {
            "total_pages_parsed": len(all_pages_data),
            "pages_urls": [page_data.get("url") for page_data in all_pages_data]
        }

        return combined

    def _generate_post_filename(self, post_link: Dict, page_num: int, post_idx: int) -> str:
        """Generate a filename for a post."""
        href = post_link.get("href", "")
        # Extract thread ID from href like thread-1160573-1-1.html
        match = re.search(r'thread-(\d+)', href)
        thread_id = match.group(1) if match else str(post_idx)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"post_{thread_id}_{timestamp}.json"

    def _create_combined_results(self) -> Dict:
        """Create combined results from all parsed posts."""
        return {
            "workflow": self.name,
            "config": {
                "base_url": self.config.base_url,
                "num_pages": self.config.num_pages,
                "posts_per_page": self.config.posts_per_page
            },
            "summary": {
                "pages_processed": self._pages_processed,
                "total_posts_parsed": len(self._parsed_posts),
                "generated_at": datetime.now().isoformat()
            },
            "posts": self._parsed_posts
        }


# Convenience function for simple usage
def scrape_1point3acres(
    url: str,
    num_pages: int = 1,
    posts_per_page: Optional[int] = 3,
    speed: str = "normal",
    output_dir: Optional[str] = None,
    verbose: bool = True
) -> WorkflowResult:
    """
    Convenience function to scrape 1point3acres forum.

    Args:
        url: Base URL (tag page or forum page)
        num_pages: Number of pages to scrape
        posts_per_page: Number of posts per page to parse (None = all)
        speed: Speed profile ("fast", "normal", "slow", "cautious")
        output_dir: Output directory
        verbose: Print progress

    Returns:
        WorkflowResult with execution details

    Examples:
        # Fast scraping
        result = scrape_1point3acres(
            url="https://www.1point3acres.com/bbs/tag/openai-9407-1.html",
            num_pages=2,
            posts_per_page=5,
            speed="fast"
        )

        # Slow, reliable scraping
        result = scrape_1point3acres(
            url="https://www.1point3acres.com/bbs/tag/openai-9407-1.html",
            num_pages=2,
            speed="slow"
        )
    """
    config = OnePoint3AcresConfig.from_speed_profile(
        base_url=url,
        speed=speed,
        num_pages=num_pages,
        posts_per_page=posts_per_page
    )

    workflow = OnePoint3AcresWorkflow(
        config=config,
        output_dir=output_dir,
        verbose=verbose
    )

    return workflow.run()


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="1point3acres Forum Scraper")
    parser.add_argument("--url", required=True, help="Base URL to scrape")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages")
    parser.add_argument("--posts", type=int, default=3, help="Posts per page (0 = all)")
    parser.add_argument("--speed", choices=["fast", "normal", "slow", "cautious"],
                        default="normal", help="Speed profile (default: normal)")
    parser.add_argument("--output", default="./output", help="Output directory")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")

    args = parser.parse_args()

    # Convert posts=0 to None (all posts)
    posts_per_page = None if args.posts == 0 else args.posts

    result = scrape_1point3acres(
        url=args.url,
        num_pages=args.pages,
        posts_per_page=posts_per_page,
        speed=args.speed,
        output_dir=args.output,
        verbose=not args.quiet
    )

    print(f"\nWorkflow {'succeeded' if result.success else 'failed'}")
    print(f"Summary: {result.summary}")
    print(f"Output files: {result.output_files}")
