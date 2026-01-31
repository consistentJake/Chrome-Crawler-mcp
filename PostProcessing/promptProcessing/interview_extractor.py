"""
Interview Information Extractor

Uses Claude API to extract structured interview information from forum posts.
"""

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import anthropic
except ImportError:
    anthropic = None
    print("Warning: anthropic package not installed. Run: pip install anthropic")

try:
    import openai
except ImportError:
    openai = None
    print("Warning: openai package not installed. Run: pip install openai")

from markdown_converter import MarkdownConverter, PostGrouper
from prompt_templates import SYSTEM_PROMPT, get_extraction_prompt
from config_loader import get_config, Config


@dataclass
class ExtractionConfig:
    """Configuration for the extraction process."""

    # Grouping settings
    posts_per_group: int = 3

    # API settings
    provider: str = "anthropic"  # "anthropic" or "openai"
    api_key: str = ""
    base_url: Optional[str] = None
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.1

    # Filtering settings
    min_content_length: int = 50

    # Output settings
    output_dir: str = "output"
    save_intermediate: bool = True

    # Rate limiting
    delay_between_calls: float = 1.0  # seconds

    @classmethod
    def from_config(cls, config: Config) -> "ExtractionConfig":
        """Create ExtractionConfig from Config object."""
        return cls(
            posts_per_group=config.posts_per_group,
            provider=config.provider,
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            min_content_length=config.min_content_length,
            output_dir=config.output_dir,
            save_intermediate=config.save_intermediate,
            delay_between_calls=config.delay_between_calls,
        )


@dataclass
class ExtractionResult:
    """Result of extracting information from a group of posts."""

    group_index: int
    posts: List[Dict[str, Any]]
    cross_post_insights: Dict[str, Any]
    raw_response: str = ""
    tokens_used: int = 0
    processing_time: float = 0.0


@dataclass
class BatchExtractionResult:
    """Result of extracting information from all posts."""

    results: List[ExtractionResult] = field(default_factory=list)
    total_posts_processed: int = 0
    total_tokens_used: int = 0
    total_processing_time: float = 0.0
    generated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": {
                "total_posts_processed": self.total_posts_processed,
                "total_tokens_used": self.total_tokens_used,
                "total_processing_time": f"{self.total_processing_time:.2f}s",
                "generated_at": self.generated_at
            },
            "extractions": [
                {
                    "group_index": r.group_index,
                    "posts": r.posts,
                    "cross_post_insights": r.cross_post_insights,
                    "tokens_used": r.tokens_used,
                    "processing_time": f"{r.processing_time:.2f}s"
                }
                for r in self.results
            ]
        }


class InterviewExtractor:
    """
    Extracts interview information from forum posts using LLM APIs (Anthropic Claude or OpenAI).

    Supports both Anthropic and OpenAI providers with automatic API adaptation.
    """

    def __init__(self, api_key: Optional[str] = None, config: Optional[ExtractionConfig] = None, config_path: Optional[str] = None):
        """
        Initialize the extractor.

        Args:
            api_key: API key (overrides config file)
            config: Extraction configuration (if None, loads from config file)
            config_path: Path to config file (optional)
        """
        # Load config from file if not provided
        if config is None:
            file_config = get_config(config_path)
            self.config = ExtractionConfig.from_config(file_config)
        else:
            self.config = config

        # Determine provider
        self.provider = self.config.provider.lower()

        # Validate provider
        if self.provider not in ["anthropic", "openai"]:
            raise ValueError(f"Unsupported provider: {self.provider}. Must be 'anthropic' or 'openai'")

        # Check if required package is installed
        if self.provider == "anthropic" and anthropic is None:
            raise ImportError("anthropic package is required. Run: pip install anthropic")
        if self.provider == "openai" and openai is None:
            raise ImportError("openai package is required. Run: pip install openai")

        # API key priority: argument > config > env var
        env_var_name = "ANTHROPIC_API_KEY" if self.provider == "anthropic" else "OPENAI_API_KEY"
        self.api_key = api_key or self.config.api_key or os.environ.get(env_var_name)
        if not self.api_key:
            raise ValueError(
                f"API key must be provided via:\n"
                f"  1. --api-key argument\n"
                f"  2. config.yaml file (api.api_key)\n"
                f"  3. {env_var_name} environment variable"
            )

        # Initialize client with optional base_url
        client_kwargs = {"api_key": self.api_key}
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url

        if self.provider == "anthropic":
            self.client = anthropic.Anthropic(**client_kwargs)
        else:  # openai
            self.client = openai.OpenAI(**client_kwargs)

        # Initialize helpers
        self.converter = MarkdownConverter(min_content_length=self.config.min_content_length)
        self.grouper = PostGrouper(group_size=self.config.posts_per_group)

        # Ensure output directory exists
        os.makedirs(self.config.output_dir, exist_ok=True)
        if self.config.save_intermediate:
            os.makedirs(os.path.join(self.config.output_dir, "intermediate"), exist_ok=True)

    def _call_llm_api(self, system_prompt: str, user_prompt: str) -> tuple[str, int, int]:
        """
        Call LLM API (Anthropic or OpenAI) with unified interface.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """
        if self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            response_text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

        else:  # openai
            # Check if this is an o1 model (doesn't support system messages or temperature)
            is_o1_model = self.config.model.startswith("o1")

            if is_o1_model:
                # o1 models: no system message, no temperature
                messages = [
                    {"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}
                ]
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    max_completion_tokens=self.config.max_tokens
                )
            else:
                # Regular OpenAI models: support system messages and temperature
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature
                )

            response_text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

        return response_text, input_tokens, output_tokens

    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response, handling code blocks.

        Args:
            response_text: Raw response from LLM

        Returns:
            Parsed JSON dictionary
        """
        # Try to find JSON in code blocks first
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # Try to parse the entire response as JSON
            json_str = response_text.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON: {e}")
            print(f"Response preview: {response_text[:500]}...")
            return {
                "posts": [],
                "cross_post_insights": {},
                "parse_error": str(e),
                "raw_response": response_text
            }

    def extract_from_group(self, posts: List[Dict[str, Any]], group_index: int) -> ExtractionResult:
        """
        Extract information from a group of posts.

        Args:
            posts: List of post dictionaries
            group_index: Index of this group

        Returns:
            ExtractionResult object
        """
        start_time = time.time()
        print(f"  [Group {group_index}] Starting processing...")

        # Convert to markdown
        print(f"  [Group {group_index}] Converting {len(posts)} posts to markdown...")
        convert_start = time.time()
        markdown_content = self.converter.convert_group(posts, group_index)
        convert_time = time.time() - convert_start
        print(f"  [Group {group_index}] Markdown conversion done ({convert_time:.2f}s)")

        if not markdown_content:
            print(f"  [Group {group_index}] No valid posts after filtering")
            return ExtractionResult(
                group_index=group_index,
                posts=[],
                cross_post_insights={},
                processing_time=time.time() - start_time
            )

        # Generate prompt
        user_prompt = get_extraction_prompt(markdown_content)

        # Save intermediate markdown if configured
        if self.config.save_intermediate:
            md_path = os.path.join(
                self.config.output_dir,
                "intermediate",
                f"group_{group_index}_input.md"
            )
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"  [Group {group_index}] Saved input markdown: {md_path}")

        # Call LLM API
        try:
            print(f"  [Group {group_index}] Calling {self.provider.upper()} API (model: {self.config.model})...")
            api_start = time.time()
            response_text, input_tokens, output_tokens = self._call_llm_api(SYSTEM_PROMPT, user_prompt)
            api_time = time.time() - api_start

            tokens_used = input_tokens + output_tokens
            print(f"  [Group {group_index}] API call completed ({api_time:.2f}s)")
            print(f"  [Group {group_index}] Tokens used: {input_tokens} in + {output_tokens} out = {tokens_used} total")

            # Parse response
            print(f"  [Group {group_index}] Parsing response...")
            parse_start = time.time()
            extracted = self._extract_json_from_response(response_text)
            parse_time = time.time() - parse_start
            print(f"  [Group {group_index}] Parsed {len(extracted.get('posts', []))} posts ({parse_time:.2f}s)")

            # Save intermediate request/response if configured
            if self.config.save_intermediate:
                # Save combined request and response
                combined_path = os.path.join(
                    self.config.output_dir,
                    "intermediate",
                    f"group_{group_index}_request_response.json"
                )
                combined_data = {
                    "request": {
                        "system_prompt": SYSTEM_PROMPT,
                        "user_prompt": user_prompt,
                        "model": self.config.model,
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens
                    },
                    "response": {
                        "raw": response_text,
                        "parsed": extracted,
                        "tokens": {
                            "input": input_tokens,
                            "output": output_tokens,
                            "total": tokens_used
                        }
                    },
                    "timing": {
                        "api_call_seconds": api_time,
                        "parse_seconds": parse_time
                    }
                }
                with open(combined_path, "w", encoding="utf-8") as f:
                    json.dump(combined_data, f, ensure_ascii=False, indent=2)
                print(f"  [Group {group_index}] Saved request/response: {combined_path}")

            total_time = time.time() - start_time
            result = ExtractionResult(
                group_index=group_index,
                posts=extracted.get("posts", []),
                cross_post_insights=extracted.get("cross_post_insights", {}),
                raw_response=response_text,
                tokens_used=tokens_used,
                processing_time=total_time
            )
            print(f"  [Group {group_index}] ✓ Complete: {len(result.posts)} posts extracted, {tokens_used} tokens, {total_time:.2f}s total")
            print()
            return result

        except Exception as e:
            total_time = time.time() - start_time
            print(f"  [Group {group_index}] ✗ Error: {e} ({total_time:.2f}s)")
            print()
            return ExtractionResult(
                group_index=group_index,
                posts=[],
                cross_post_insights={"error": str(e)},
                processing_time=total_time
            )

    def extract_from_posts(
        self,
        posts: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> BatchExtractionResult:
        """
        Extract information from all posts.

        Args:
            posts: List of all post dictionaries
            progress_callback: Optional callback for progress updates

        Returns:
            BatchExtractionResult object
        """
        start_time = time.time()
        results = []

        # Group posts
        groups = self.grouper.group_posts(posts)
        total_groups = len(groups)

        print(f"\n{'='*70}")
        print(f"Starting extraction: {len(posts)} posts in {total_groups} groups")
        print(f"Model: {self.config.model}")
        print(f"Posts per group: {self.config.posts_per_group}")
        print(f"{'='*70}\n")

        for i, group in enumerate(groups, 1):
            group_start = time.time()
            print(f"[{i}/{total_groups}] Processing group {i}...")
            print(f"{'─'*70}")

            result = self.extract_from_group(group, i)
            results.append(result)

            # Calculate progress stats
            elapsed = time.time() - start_time
            avg_time_per_group = elapsed / i
            remaining_groups = total_groups - i
            estimated_remaining = avg_time_per_group * remaining_groups

            cumulative_posts = sum(len(r.posts) for r in results)
            cumulative_tokens = sum(r.tokens_used for r in results)

            print(f"[Progress] {i}/{total_groups} groups done ({i/total_groups*100:.1f}%)")
            print(f"[Progress] Elapsed: {elapsed:.1f}s | Est. remaining: {estimated_remaining:.1f}s")
            print(f"[Progress] Total extracted: {cumulative_posts} posts, {cumulative_tokens} tokens")
            print()

            if progress_callback:
                progress_callback(i, total_groups, result)

            # Rate limiting
            if i < total_groups:
                if self.config.delay_between_calls > 0:
                    print(f"[Rate limit] Waiting {self.config.delay_between_calls}s before next group...\n")
                time.sleep(self.config.delay_between_calls)

        # Compile final result
        total_time = time.time() - start_time
        batch_result = BatchExtractionResult(
            results=results,
            total_posts_processed=sum(len(r.posts) for r in results),
            total_tokens_used=sum(r.tokens_used for r in results),
            total_processing_time=total_time,
            generated_at=datetime.now().isoformat()
        )

        print(f"{'='*70}")
        print(f"Extraction complete!")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average time per group: {total_time/total_groups:.2f}s")
        print(f"{'='*70}\n")

        return batch_result

    def save_results(self, result: BatchExtractionResult, filename: Optional[str] = None) -> str:
        """
        Save extraction results to JSON file.

        Args:
            result: BatchExtractionResult object
            filename: Optional custom filename

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"extracted_interviews_{timestamp}.json"

        filepath = os.path.join(self.config.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

        print(f"Results saved to: {filepath}")
        return filepath


def load_posts_from_json(filepath: str) -> List[Dict[str, Any]]:
    """
    Load posts from a JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        List of post dictionaries
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("posts", [])


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python interview_extractor.py <input_json_file>")
        print("Example: python interview_extractor.py combined_results_processed.json")
        sys.exit(1)

    input_file = sys.argv[1]

    # Load posts
    posts = load_posts_from_json(input_file)
    print(f"Loaded {len(posts)} posts from {input_file}")

    # Configure and run
    config = ExtractionConfig(
        posts_per_group=3,
        model="claude-sonnet-4-20250514",
        save_intermediate=True
    )

    extractor = InterviewExtractor(config=config)
    results = extractor.extract_from_posts(posts)

    # Save
    extractor.save_results(results)
