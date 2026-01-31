#!/usr/bin/env python3
"""
WebAgent Pipeline Orchestrator

Main entry point for running the complete web scraping and extraction pipeline.
Coordinates the scraper and prompt processing stages.

Usage:
    python main.py [options]
    python main.py --url "https://www.1point3acres.com/bbs/tag-9407-1.html"
    python main.py --config config.local.yaml
    python main.py --dry-run  # Test without API calls

Examples:
    # Run full pipeline with default config
    python main.py

    # Run with custom URL
    python main.py --url "https://www.1point3acres.com/bbs/tag-9407-1.html" --pages 2

    # Run extraction only on existing scraper output
    python main.py --extract-only ./scraper_output/combined_results_20250122_120000.json

    # Dry run (no API calls)
    python main.py --dry-run
"""

import argparse
import glob
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared import UnifiedConfig, create_timestamped_dir


def find_latest_scraper_output(output_dir: str) -> str:
    """Find the most recent combined results file from scraper output."""
    pattern = os.path.join(output_dir, "combined_results_*.json")
    files = glob.glob(pattern)

    if not files:
        raise FileNotFoundError(f"No scraper output found in {output_dir}")

    # Sort by modification time, get newest
    latest = max(files, key=os.path.getmtime)
    return latest


def run_scraper(config: UnifiedConfig, url_override: str = None,
                pages_override: int = None, posts_override: int = None,
                verbose: bool = True) -> str:
    """
    Run the web scraper.

    Args:
        config: UnifiedConfig instance
        url_override: Override URL from command line
        pages_override: Override number of pages
        posts_override: Override posts per page
        verbose: Print progress

    Returns:
        Path to the combined results JSON file
    """
    # Import here to avoid circular imports
    sys.path.insert(0, str(PROJECT_ROOT / "workflows"))
    from onepoint3acres_workflow import OnePoint3AcresWorkflow, OnePoint3AcresConfig

    # Get scraper settings from config
    scraper_config = config.scraper

    url = url_override or scraper_config.get("url", "")
    if not url:
        raise ValueError("No URL specified. Set scraper.url in config or use --url")

    num_pages = pages_override or scraper_config.get("num_pages", 1)
    posts_per_page = posts_override or scraper_config.get("posts_per_page")
    speed = scraper_config.get("speed", "normal")
    output_dir = scraper_config.get("output", {}).get("directory", "./scraper_output")

    if verbose:
        print("=" * 60)
        print("STAGE 1: WEB SCRAPING")
        print("=" * 60)
        print(f"URL: {url}")
        print(f"Pages: {num_pages}")
        print(f"Posts per page: {posts_per_page or 'all'}")
        print(f"Speed: {speed}")
        print(f"Output: {output_dir}")
        print()

    # Create workflow config
    workflow_config = OnePoint3AcresConfig.from_speed_profile(
        base_url=url,
        speed=speed,
        num_pages=num_pages,
        posts_per_page=posts_per_page,
        min_posts_per_page=scraper_config.get("verification", {}).get("min_posts_per_page", 1),
        verify_post_content=scraper_config.get("verification", {}).get("verify_post_content", True),
        save_individual_posts=scraper_config.get("output", {}).get("save_individual_posts", True),
        save_combined_results=scraper_config.get("output", {}).get("save_combined_results", True),
    )

    # Run workflow
    workflow = OnePoint3AcresWorkflow(
        config=workflow_config,
        client_type=scraper_config.get("runtime", {}).get("client_type", "chrome"),
        output_dir=output_dir,
        verbose=verbose,
    )

    result = workflow.run()

    if not result.success:
        raise RuntimeError(f"Scraper failed: {result.summary}")

    # Find the output file
    if result.output_files:
        # Get the combined results file
        combined_files = [f for f in result.output_files if "combined_results" in f]
        if combined_files:
            return combined_files[0]

    # Fallback: find latest combined results
    return find_latest_scraper_output(output_dir)


def run_extraction(config: UnifiedConfig, input_file: str,
                   dump_prompt: bool = False,
                   max_posts: int = None, verbose: bool = True) -> str:
    """
    Run the extraction pipeline.

    Args:
        config: UnifiedConfig instance
        input_file: Path to scraper output JSON
        dump_prompt: Save prompts without calling API
        max_posts: Maximum posts to process
        verbose: Print progress

    Returns:
        Path to extraction output file
    """
    # Import here to avoid circular imports
    sys.path.insert(0, str(PROJECT_ROOT / "PostProcessing" / "promptProcessing"))
    from run_prompt_processing import run_extraction as _run_extraction

    if verbose:
        print()
        print("=" * 60)
        print("STAGE 2: INTERVIEW EXTRACTION")
        print("=" * 60)
        print(f"Input: {input_file}")
        print(f"Dump prompt only: {dump_prompt}")
        print()

    return _run_extraction(
        input_file=input_file,
        config=config,
        dump_prompt=dump_prompt,
        max_posts=max_posts,
        verbose=verbose,
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="WebAgent Pipeline - Scrape and extract interview information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    # Run with config.yaml
  python main.py --url "URL" --pages 2              # Override URL and pages
  python main.py --extract-only output.json         # Skip scraping
  python main.py --dump-prompt                      # Generate prompts without API calls
  python main.py --scrape-only                      # Only run scraper
        """
    )

    # Config
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to config file (default: config.local.yaml or config.yaml)"
    )

    # Scraper overrides
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="URL to scrape (overrides config)"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="Number of pages to scrape (overrides config)"
    )
    parser.add_argument(
        "--posts",
        type=int,
        default=None,
        help="Posts per page to parse (overrides config)"
    )

    # Extraction overrides
    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help="Maximum posts to process in extraction"
    )

    # Mode flags
    parser.add_argument(
        "--scrape-only",
        action="store_true",
        help="Only run scraper, skip extraction"
    )
    parser.add_argument(
        "--extract-only",
        type=str,
        default=None,
        metavar="FILE",
        help="Skip scraping, run extraction on existing file"
    )
    parser.add_argument(
        "--dump-prompt",
        action="store_true",
        help="Extraction: generate and save prompts without making API calls"
    )

    # Output
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    verbose = not args.quiet

    # Load configuration
    try:
        config = UnifiedConfig.load(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if verbose:
        print()
        print("=" * 60)
        print("WEBAGENT PIPELINE")
        print("=" * 60)
        print()

    scraper_output = None
    extraction_output = None

    try:
        # Check for predefined combined file in config
        predefined_file = config.scraper.get("output", {}).get("predefined_combined_file")
        skip_scraper = config.scraper.get("skip_scraper", False)

        # Stage 1: Scraping
        if args.extract_only:
            # Skip scraping, use provided file
            scraper_output = args.extract_only
            if not os.path.exists(scraper_output):
                print(f"Error: Input file not found: {scraper_output}")
                sys.exit(1)
            if verbose:
                print(f"Skipping scraper, using: {scraper_output}")
        elif skip_scraper and predefined_file:
            # Skip scraping when skip_scraper=true and predefined file is set
            if os.path.exists(predefined_file):
                scraper_output = predefined_file
                if verbose:
                    print(f"skip_scraper=true, using predefined file: {predefined_file}")
                    print("Skipping scraping stage...")
            else:
                print(f"Error: skip_scraper=true but predefined file not found: {predefined_file}")
                sys.exit(1)
        elif predefined_file and os.path.exists(predefined_file):
            # Skip scraping, use predefined file from config (legacy behavior)
            scraper_output = predefined_file
            if verbose:
                print(f"Found predefined combined file in config: {predefined_file}")
                print("Skipping scraping stage...")
        else:
            # Run scraper
            if predefined_file and not os.path.exists(predefined_file):
                if verbose:
                    print(f"Warning: Predefined file not found: {predefined_file}")
                    print("Running scraper instead...")
            
            scraper_output = run_scraper(
                config=config,
                url_override=args.url,
                pages_override=args.pages,
                posts_override=args.posts,
                verbose=verbose,
            )
            if verbose:
                print(f"\nScraper output: {scraper_output}")

        # Stage 2: Extraction
        if args.scrape_only:
            if verbose:
                print("\nSkipping extraction (--scrape-only)")
        else:
            # Check for dump_prompt_only in config or command line
            dump_prompt = args.dump_prompt or config.pipeline.get("dump_prompt_only", False)
            
            extraction_output = run_extraction(
                config=config,
                input_file=scraper_output,
                dump_prompt=dump_prompt,
                max_posts=args.max_posts,
                verbose=verbose,
            )

        # Summary
        if verbose:
            print()
            print("=" * 60)
            print("PIPELINE COMPLETE")
            print("=" * 60)
            if scraper_output:
                print(f"Scraper output: {scraper_output}")
            if extraction_output:
                print(f"Extraction output: {extraction_output}")

    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
