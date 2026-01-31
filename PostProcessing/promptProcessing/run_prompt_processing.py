#!/usr/bin/env python3
"""
Interview Information Extraction Tool

Entry point for extracting interview information from forum posts using Claude API.
Can be run standalone or called from the main pipeline orchestrator.

Usage:
    python run_prompt_processing.py <input_json> [options]

Examples:
    python run_prompt_processing.py ./scraper_output/combined_results.json
    python run_prompt_processing.py input.json --config config.yaml
    python run_prompt_processing.py input.json --group-size 2 --model claude-sonnet-4-20250514
    python run_prompt_processing.py input.json --dump-prompt
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for shared imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from shared import create_timestamped_dir, UnifiedConfig

from interview_extractor import InterviewExtractor, ExtractionConfig, load_posts_from_json
from interview_filter import InterviewFilter, FilterConfig
from config_loader import get_config
from markdown_converter import MarkdownConverter, PostGrouper
from prompt_templates import SYSTEM_PROMPT, get_extraction_prompt

# Import process_json for preprocessing
sys.path.insert(0, str(Path(__file__).parent.parent))
from process_json import process_json_file, process_post


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract interview information from forum posts using Claude API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py ../workflows/output/combined_results_processed.json
  python main.py input.json --group-size 2
  python main.py input.json -o results.json --no-intermediate
        """
    )

    parser.add_argument(
        "input_file",
        type=str,
        help="Path to input JSON file containing posts"
    )

    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to config file (default: config.local.yaml or config.yaml)"
    )

    parser.add_argument(
        "-g", "--group-size",
        type=int,
        default=None,
        help="Number of posts per LLM call (overrides config)"
    )

    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help="Maximum number of posts to process (default: all posts)"
    )

    parser.add_argument(
        "-m", "--model",
        type=str,
        default=None,
        choices=["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-haiku-20241022"],
        help="Claude model to use (overrides config)"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output filename (default: auto-generated with timestamp)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory (default: output)"
    )

    parser.add_argument(
        "--no-intermediate",
        action="store_true",
        help="Don't save intermediate files (markdown, raw responses)"
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="LLM temperature (default: 0.1, lower = more consistent)"
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Max output tokens per LLM call (default: 4096)"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between API calls in seconds (default: 1.0)"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Anthropic API key (default: from ANTHROPIC_API_KEY env var)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only convert to markdown, don't call API"
    )

    parser.add_argument(
        "--dump-prompt",
        action="store_true",
        help="Dump the prompt that would be sent to LLM (no API call)"
    )

    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Preprocess input JSON using process_json.py before extraction"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    return parser.parse_args()




def _dump_prompt(input_file: str, config: ExtractionConfig, max_posts: int = None, preprocess: bool = False):
    """
    Generate and save prompts without making API calls.

    Args:
        input_file: Path to input JSON file
        config: Extraction configuration
        max_posts: Maximum number of posts to process (None = all)
        preprocess: Whether to preprocess using process_json.py
    """
    # Load posts
    posts = load_posts_from_json(input_file)
    total_posts = len(posts)

    # Apply max-posts limit if specified
    if max_posts is not None and max_posts < total_posts:
        posts = posts[:max_posts]
        print(f"Loaded {total_posts} posts from {input_file}, using first {len(posts)}")
    else:
        print(f"Loaded {len(posts)} posts from {input_file}")

    # Optionally preprocess posts using process_json.py
    if preprocess:
        print("Preprocessing posts using process_json.py...")
        preprocessed_posts = []
        for i, post in enumerate(posts):
            processed = process_post(post)
            if processed:
                preprocessed_posts.append(processed)
        posts = preprocessed_posts
        print(f"Preprocessed {len(posts)} posts")

    # Initialize helpers
    converter = MarkdownConverter(min_content_length=config.min_content_length)
    grouper = PostGrouper(group_size=config.posts_per_group)

    # Group and convert
    groups = grouper.group_posts(posts)
    print(f"Created {len(groups)} groups (group size: {config.posts_per_group})")

    # Ensure output directory exists
    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs(os.path.join(config.output_dir, "prompts"), exist_ok=True)

    for i, group in enumerate(groups, 1):
        markdown = converter.convert_group(group, i)
        if markdown:
            # Generate the user prompt
            user_prompt = get_extraction_prompt(markdown)

            # Create the full prompt structure
            prompt_data = {
                "group_index": i,
                "system_prompt": SYSTEM_PROMPT,
                "user_prompt": user_prompt,
                "model": config.model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            }

            # Save prompt to file
            prompt_path = os.path.join(config.output_dir, "prompts", f"group_{i}_prompt.json")
            with open(prompt_path, "w", encoding="utf-8") as f:
                json.dump(prompt_data, f, ensure_ascii=False, indent=2)

            # Also save a human-readable version
            readable_path = os.path.join(config.output_dir, "prompts", f"group_{i}_prompt.md")
            with open(readable_path, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("SYSTEM PROMPT:\n")
                f.write("=" * 80 + "\n")
                f.write(SYSTEM_PROMPT + "\n\n")
                f.write("=" * 80 + "\n")
                f.write("USER PROMPT:\n")
                f.write("=" * 80 + "\n")
                f.write(user_prompt + "\n")
                
            # Also save markdown for review
            md_path = os.path.join(config.output_dir, "markdown", f"group_{i}.md")
            os.makedirs(os.path.dirname(md_path), exist_ok=True)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown)

            valid_in_group = markdown.count("## 帖子")
            print(f"  Group {i}: {valid_in_group} valid posts -> {prompt_path}")
        else:
            print(f"  Group {i}: No valid posts (all filtered)")

    print(f"\nPrompt generation complete!")
    print(f"  Prompt files saved to: {os.path.join(config.output_dir, 'prompts')}")
    print(f"  Markdown files saved to: {os.path.join(config.output_dir, 'markdown')}")


def progress_callback(current: int, total: int, result):
    """Callback for progress updates during extraction."""
    posts_extracted = len(result.posts)
    print(f"    -> Extracted {posts_extracted} posts, {result.tokens_used} tokens, {result.processing_time:.2f}s")


def apply_keyword_filter(posts: list, config: UnifiedConfig, verbose: bool = True) -> list:
    """
    Apply keyword-based filtering to posts.

    Args:
        posts: List of post dictionaries
        config: UnifiedConfig instance
        verbose: Print progress messages

    Returns:
        Filtered list of posts
    """
    from shared import should_skip_by_keywords, get_post_title, get_main_content

    skip_keywords = config.skip_keywords
    filtered = []
    skipped_count = 0

    for post in posts:
        title = get_post_title(post) or ""
        content = get_main_content(post) or ""

        if should_skip_by_keywords(title, skip_keywords):
            skipped_count += 1
            continue
        if should_skip_by_keywords(content, skip_keywords):
            skipped_count += 1
            continue

        filtered.append(post)

    if verbose and skipped_count > 0:
        print(f"  Keyword filter: {skipped_count} posts skipped, {len(filtered)} remaining")

    return filtered


def run_extraction(
    input_file: str,
    config: Optional[UnifiedConfig] = None,
    dry_run: bool = False,
    dump_prompt: bool = False,
    max_posts: Optional[int] = None,
    verbose: bool = True,
) -> Optional[str]:
    """
    Run the extraction pipeline programmatically.

    This function can be called from the main pipeline orchestrator.

    Args:
        input_file: Path to input JSON file containing scraped posts
        config: UnifiedConfig instance (loads from file if None)
        dry_run: Only convert to markdown, don't call API
        dump_prompt: Dump prompts without calling API
        max_posts: Maximum number of posts to process
        verbose: Print progress messages

    Returns:
        Path to output file, or None if dry_run/dump_prompt mode
    """
    # Validate input file
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Load config if not provided
    if config is None:
        config = UnifiedConfig.load()

    # Create timestamped output directory
    base_output_dir = config.extraction_output_dir
    timestamped_output_dir = create_timestamped_dir(base_output_dir)

    if verbose:
        print(f"Output directory: {timestamped_output_dir}")

    # Build ExtractionConfig from UnifiedConfig
    extraction_config = ExtractionConfig(
        posts_per_group=config.posts_per_group,
        provider=config.api_provider,
        api_key=config.api_key,
        base_url=config.api_base_url,
        model=config.api_model,
        max_tokens=config.api_max_tokens,
        temperature=config.api_temperature,
        output_dir=timestamped_output_dir,
        save_intermediate=config.save_intermediate,
        delay_between_calls=config.delay_between_calls,
        min_content_length=config.min_content_length,
    )

    # Dry run mode
    if dry_run:
        if verbose:
            print("=== DRY RUN MODE ===")
        _dry_run(input_file, extraction_config, max_posts=max_posts)
        return None

    # Dump prompt mode
    if dump_prompt:
        if verbose:
            print("=== PROMPT GENERATION MODE (No API calls) ===")
        _dump_prompt(input_file, extraction_config, max_posts=max_posts)
        return None

    # Full extraction
    if verbose:
        print("=== Interview Information Extraction Pipeline ===")
        print()

    # Load posts
    posts = load_posts_from_json(input_file)
    total_posts = len(posts)

    # Apply max-posts limit if specified
    if max_posts is not None and max_posts < total_posts:
        posts = posts[:max_posts]
        if verbose:
            print(f"Loaded {total_posts} posts from {input_file}, using first {len(posts)}")
    else:
        if verbose:
            print(f"Loaded {len(posts)} posts from {input_file}")

    initial_post_count = len(posts)

    # ===== STAGE 1: Keyword Filtering =====
    if config.keyword_filter_enabled:
        if verbose:
            print("\n[Stage 1] Keyword Filtering")
        posts = apply_keyword_filter(posts, config, verbose=verbose)
        if verbose:
            print(f"  After keyword filter: {len(posts)} posts")

    # ===== STAGE 2: LLM Filtering =====
    filtering_result = None
    if config.llm_filter_stage_enabled and config.llm_filter_enabled:
        if verbose:
            print("\n[Stage 2] LLM-based Filtering")

        try:
            filter_config = FilterConfig.from_unified_config(config)
            filter_config.output_dir = timestamped_output_dir

            llm_filter = InterviewFilter(filter_config)
            posts, filtering_result = llm_filter.filter_posts(posts, verbose=verbose)

            if filter_config.save_results:
                llm_filter.save_results(filtering_result, timestamped_output_dir)

        except Exception as e:
            if verbose:
                print(f"  Warning: LLM filtering failed: {e}")
                print("  Continuing with all posts...")

    # ===== STAGE 3: Extraction =====
    if not config.extraction_stage_enabled:
        if verbose:
            print("\n[Stage 3] Extraction: SKIPPED (disabled in config)")
            print(f"\nPipeline complete. {len(posts)} posts passed filtering.")

            if filtering_result:
                print(f"  Initial posts: {initial_post_count}")
                print(f"  After filters: {len(posts)}")
                print(f"  Filter results saved to: {timestamped_output_dir}")

        return None

    if verbose:
        print("\n[Stage 3] LLM Extraction")
        print()

    # Check API key
    api_key = extraction_config.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "API key not found! Set it in config.yaml, "
            "ANTHROPIC_API_KEY env var, or pass via --api-key"
        )

    # Initialize extractor
    extractor = InterviewExtractor(
        api_key=api_key,
        config=extraction_config
    )

    # Run extraction
    results = extractor.extract_from_posts(
        posts,
        progress_callback=progress_callback if verbose else None
    )

    # Save results
    output_path = extractor.save_results(results)

    # Print summary
    if verbose:
        print()
        print("=== Pipeline Complete ===")
        print(f"  Initial posts: {initial_post_count}")
        print(f"  Posts after filtering: {len(posts)}")
        print(f"  Posts extracted: {results.total_posts_processed}")
        print(f"  Total tokens used: {results.total_tokens_used}")
        print(f"  Total time: {results.total_processing_time:.2f}s")
        print(f"  Results saved to: {output_path}")

    return output_path


def main():
    """Main entry point."""
    args = parse_args()

    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)

    # Load config from file
    try:
        file_config = get_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Determine base output directory
    base_output_dir = args.output_dir if args.output_dir != "output" else file_config.output_dir

    # Create timestamped output directory for intermediate files
    timestamped_output_dir = create_timestamped_dir(base_output_dir)
    print(f"Output directory: {timestamped_output_dir}")

    # Build configuration, merging file config with command line overrides
    config = ExtractionConfig(
        posts_per_group=args.group_size if args.group_size is not None else file_config.posts_per_group,
        provider=file_config.provider,  # Provider from config file only
        api_key=args.api_key or file_config.api_key,
        base_url=file_config.base_url,
        model=args.model if args.model is not None else file_config.model,
        max_tokens=args.max_tokens if args.max_tokens != 4096 else file_config.max_tokens,
        temperature=args.temperature if args.temperature != 0.1 else file_config.temperature,
        output_dir=timestamped_output_dir,  # Use timestamped directory
        save_intermediate=not args.no_intermediate if args.no_intermediate else file_config.save_intermediate,
        delay_between_calls=args.delay if args.delay != 1.0 else file_config.delay_between_calls,
        min_content_length=file_config.min_content_length,
    )

    # Check API key (unless dry run or dump-prompt)
    if not args.dry_run and not args.dump_prompt:
        api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: API key not found!")
            print("Set it in one of these ways:")
            print("  1. In config.yaml or config.local.yaml: api.api_key")
            print("  2. Environment variable: export ANTHROPIC_API_KEY='your-key'")
            print("  3. Command line: --api-key 'your-key'")
            sys.exit(1)

    if args.verbose:
        print("Configuration:")
        print(f"  Input file: {args.input_file}")
        print(f"  Group size: {config.posts_per_group}")
        print(f"  Model: {config.model}")
        print(f"  Temperature: {config.temperature}")
        print(f"  Output directory: {config.output_dir}")
        print(f"  Save intermediate: {config.save_intermediate}")
        print()

    # Dry run mode
    if args.dry_run:
        print("=== DRY RUN MODE ===")
        _dry_run(args.input_file, config, max_posts=args.max_posts)
        return

    # Dump prompt mode
    if args.dump_prompt:
        print("=== PROMPT GENERATION MODE (No API calls) ===")
        _dump_prompt(args.input_file, config, max_posts=args.max_posts, preprocess=args.preprocess)
        return

    # Full extraction
    print("=== Interview Information Extraction ===")
    print()

    try:
        # Initialize extractor
        extractor = InterviewExtractor(
            api_key=args.api_key,
            config=config
        )

        # Load posts
        posts = load_posts_from_json(args.input_file)
        total_posts = len(posts)

        # Apply max-posts limit if specified
        if args.max_posts is not None and args.max_posts < total_posts:
            posts = posts[:args.max_posts]
            print(f"Loaded {total_posts} posts from {args.input_file}, using first {len(posts)}")
        else:
            print(f"Loaded {len(posts)} posts from {args.input_file}")
        print()

        # Run extraction
        results = extractor.extract_from_posts(
            posts,
            progress_callback=progress_callback if args.verbose else None
        )

        # Save results
        output_path = extractor.save_results(results, args.output)

        # Print summary
        print()
        print("=== Extraction Complete ===")
        print(f"  Posts processed: {results.total_posts_processed}")
        print(f"  Total tokens used: {results.total_tokens_used}")
        print(f"  Total time: {results.total_processing_time:.2f}s")
        print(f"  Results saved to: {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
