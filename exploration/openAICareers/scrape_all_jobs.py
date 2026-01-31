#!/usr/bin/env python3
"""
Scrape all OpenAI job postings from the jobs JSON file.

This script:
1. Reads the openai_jobs.json file
2. Opens each job page using BrowserIntegration (Chrome MCP)
3. Downloads and extracts content from each page
4. Saves all extractions to a single combined JSON file
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add src and helper directories to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "helper"))
sys.path.insert(0, str(PROJECT_ROOT))

from bs4 import BeautifulSoup
from browser_integration import BrowserIntegration
from utils import extract_job_content


class OpenAIJobScraper:
    """Scrapes OpenAI job postings using BrowserIntegration."""

    def __init__(self, output_dir: Path):
        """
        Initialize the scraper.

        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_html_dir = output_dir / "jobs"
        self.jobs_html_dir.mkdir(parents=True, exist_ok=True)

        # Initialize browser integration (Chrome MCP)
        print("[INFO] Initializing Chrome MCP browser integration...")
        self.browser = BrowserIntegration(client_type="chrome")
        print("[INFO] Browser integration initialized.")

    def navigate_to_url(self, url: str, wait_seconds: float = 2.0) -> bool:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            wait_seconds: Seconds to wait after navigation

        Returns:
            True if navigation was successful
        """
        result = self.browser.playwright_client.browser_navigate(url)
        if result.get("status") != "success":
            print(f"[ERROR] Navigation failed: {result.get('message', 'Unknown error')}")
            return False

        # Wait for page load
        time.sleep(wait_seconds)
        return True

    def get_page_html(self) -> Optional[str]:
        """
        Get the current page HTML.

        Returns:
            HTML content or None if failed
        """
        try:
            return self.browser.get_current_page_html()
        except Exception as e:
            print(f"[ERROR] Failed to get page HTML: {e}")
            return None


    def save_html(self, html_content: str, job_title: str) -> Path:
        """
        Save HTML content to a file.

        Args:
            html_content: HTML content to save
            job_title: Job title for filename

        Returns:
            Path to saved file
        """
        # Clean job title for filename
        clean_title = re.sub(r'[^\w\s-]', '', job_title).strip()
        clean_title = re.sub(r'[-\s]+', '-', clean_title).lower()[:80]

        filename = f"{clean_title}.html"
        filepath = self.jobs_html_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return filepath

    def scrape_job(self, job_info: Dict, index: int, total: int) -> Optional[Dict]:
        """
        Scrape a single job posting.

        Args:
            job_info: Job info dict with title, url, team
            index: Current job index
            total: Total number of jobs

        Returns:
            Extracted job data or None if failed
        """
        url = job_info.get('url')
        title = job_info.get('title', 'Unknown')
        team = job_info.get('team', 'Unknown')

        print(f"\n[{index + 1}/{total}] Processing: {title}")
        print(f"    Team: {team}")
        print(f"    URL: {url}")

        # Navigate to job page
        if not self.navigate_to_url(url, wait_seconds=2.0):
            print(f"    [FAILED] Could not navigate to page")
            return None

        # Get page HTML
        html_content = self.get_page_html()
        if not html_content:
            print(f"    [FAILED] Could not get page HTML")
            return None

        # Save HTML file
        html_path = self.save_html(html_content, title)
        print(f"    [SAVED] HTML: {html_path.name}")

        # Extract job content using utility function
        extracted_data = extract_job_content(html_content)

        # Merge with original job info
        job_data = {
            'original_info': job_info,
            'extracted': extracted_data,
            'html_file': str(html_path.relative_to(self.output_dir)),
            'scraped_at': datetime.now().isoformat()
        }

        print(f"    [EXTRACTED] Title: {extracted_data.get('title', 'N/A')}")
        print(f"    [EXTRACTED] Compensation: {extracted_data.get('compensation', 'N/A')}")

        return job_data

    def scrape_all_jobs(self, jobs: List[Dict], start_index: int = 0, limit: Optional[int] = None) -> List[Dict]:
        """
        Scrape all jobs from the list.

        Args:
            jobs: List of job info dicts
            start_index: Index to start from (for resuming)
            limit: Maximum number of jobs to scrape (None for all)

        Returns:
            List of extracted job data
        """
        total = len(jobs)
        if limit:
            jobs = jobs[start_index:start_index + limit]
        else:
            jobs = jobs[start_index:]

        print(f"\n{'='*60}")
        print(f"Starting to scrape {len(jobs)} jobs (from index {start_index})")
        print(f"{'='*60}")

        results = []
        failed_jobs = []

        for i, job_info in enumerate(jobs):
            actual_index = start_index + i

            try:
                job_data = self.scrape_job(job_info, actual_index, total)
                if job_data:
                    results.append(job_data)
                else:
                    failed_jobs.append({
                        'index': actual_index,
                        'job': job_info,
                        'error': 'Scrape returned None'
                    })
            except Exception as e:
                print(f"    [ERROR] Exception: {e}")
                failed_jobs.append({
                    'index': actual_index,
                    'job': job_info,
                    'error': str(e)
                })

            # Small delay between requests to be nice to the server
            if i < len(jobs) - 1:
                time.sleep(1.0)

        print(f"\n{'='*60}")
        print(f"Scraping complete: {len(results)}/{len(jobs)} successful")
        if failed_jobs:
            print(f"Failed jobs: {len(failed_jobs)}")
        print(f"{'='*60}")

        return results, failed_jobs

    def close(self):
        """Close the browser integration."""
        if self.browser:
            self.browser.close()


def main():
    """Main function to scrape all OpenAI job postings."""
    # Paths
    script_dir = Path(__file__).parent
    input_file = script_dir / "openai_jobs.json"
    output_dir = script_dir
    output_file = output_dir / "all_jobs_extracted.json"

    # Read input JSON
    print(f"Reading jobs from: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    jobs = data.get('jobs', [])
    print(f"Found {len(jobs)} jobs to process")

    # Initialize scraper
    scraper = OpenAIJobScraper(output_dir)

    try:
        # Scrape all jobs (you can adjust start_index and limit for testing)
        # For testing, start with first 5 jobs:
        # results, failed = scraper.scrape_all_jobs(jobs, start_index=0, limit=5)

        # For full scrape:
        results, failed = scraper.scrape_all_jobs(jobs, start_index=0, limit=None)

        # Build final output
        final_output = {
            'source_file': str(input_file),
            'scraped_at': datetime.now().isoformat(),
            'total_jobs_in_source': len(jobs),
            'total_jobs_scraped': len(results),
            'total_jobs_failed': len(failed),
            'jobs': results,
            'failed_jobs': failed
        }

        # Save combined results
        print(f"\nSaving combined results to: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*60}")
        print("SCRAPING COMPLETE!")
        print(f"{'='*60}")
        print(f"Total jobs scraped: {len(results)}")
        print(f"Total jobs failed: {len(failed)}")
        print(f"Results saved to: {output_file}")
        print(f"HTML files saved to: {output_dir / 'jobs'}")

    finally:
        # Always close the browser
        scraper.close()


if __name__ == '__main__':
    main()
