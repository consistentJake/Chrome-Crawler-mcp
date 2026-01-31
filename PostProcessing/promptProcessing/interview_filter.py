"""
Interview Filter

Uses LLM to filter posts and identify interview-related content before extraction.
This is a pre-filtering step that uses a lighter/cheaper model with larger batch sizes.
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from filter_prompt_templates import (
    FILTER_SYSTEM_PROMPT,
    get_filter_prompt,
    prepare_post_summary,
)


@dataclass
class FilterConfig:
    """Configuration for LLM-based filtering."""

    # API settings
    provider: str = "anthropic"
    api_key: str = ""
    base_url: Optional[str] = None
    model: str = "claude-3-5-haiku-20241022"
    max_tokens: int = 2048
    temperature: float = 0.0

    # Processing settings
    posts_per_batch: int = 20
    confidence_threshold: float = 0.7
    delay_between_calls: float = 0.5

    # Output settings
    output_dir: str = "output"
    save_results: bool = True
    results_filename: str = "filter_results.json"

    @classmethod
    def from_unified_config(cls, config: "UnifiedConfig") -> "FilterConfig":
        """
        Create FilterConfig from UnifiedConfig.

        Falls back to extraction API settings if filter-specific settings are not provided.
        """
        llm_filter = config.llm_filter_config
        filter_api = llm_filter.get("api", {})
        filter_processing = llm_filter.get("processing", {})
        filter_output = llm_filter.get("output", {})

        # API settings with fallback to extraction settings
        provider = filter_api.get("provider") or config.api_provider
        api_key = filter_api.get("api_key") or config.api_key
        base_url = filter_api.get("base_url") or config.api_base_url
        model = filter_api.get("model") or "claude-3-5-haiku-20241022"
        max_tokens = filter_api.get("max_tokens", 2048)
        temperature = filter_api.get("temperature", 0.0)

        return cls(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            posts_per_batch=filter_processing.get("posts_per_batch", 20),
            confidence_threshold=filter_processing.get("confidence_threshold", 0.7),
            delay_between_calls=filter_processing.get("delay_between_calls", 0.5),
            output_dir=config.extraction_output_dir,
            save_results=filter_output.get("save_results", True),
            results_filename=filter_output.get("results_filename", "filter_results.json"),
        )


@dataclass
class PostFilterResult:
    """Result for a single filtered post."""

    post_index: int
    original_index: int  # Index in original posts list
    title: str
    is_interview_related: bool
    confidence: float
    reason: str


@dataclass
class BatchFilterResult:
    """Result for a batch of filtered posts."""

    batch_index: int
    posts: List[PostFilterResult]
    raw_response: str = ""
    tokens_used: int = 0
    processing_time: float = 0.0


@dataclass
class FilteringResult:
    """Complete filtering result with summary."""

    batch_results: List[BatchFilterResult] = field(default_factory=list)
    kept_posts: List[Dict[str, Any]] = field(default_factory=list)
    kept_post_indices: List[int] = field(default_factory=list)
    filtered_post_indices: List[int] = field(default_factory=list)
    total_posts: int = 0
    posts_kept: int = 0
    posts_filtered: int = 0
    total_tokens_used: int = 0
    total_processing_time: float = 0.0
    generated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        filter_rate = (self.posts_filtered / self.total_posts * 100) if self.total_posts > 0 else 0

        return {
            "summary": {
                "total_posts": self.total_posts,
                "posts_kept": self.posts_kept,
                "posts_filtered": self.posts_filtered,
                "filter_rate": f"{filter_rate:.1f}%",
                "total_tokens_used": self.total_tokens_used,
                "total_processing_time": f"{self.total_processing_time:.2f}s",
                "generated_at": self.generated_at,
            },
            "kept_post_indices": self.kept_post_indices,
            "filtered_post_indices": self.filtered_post_indices,
            "batch_details": [
                {
                    "batch_index": br.batch_index,
                    "posts": [
                        {
                            "post_index": p.post_index,
                            "original_index": p.original_index,
                            "title": p.title,
                            "is_interview_related": p.is_interview_related,
                            "confidence": p.confidence,
                            "reason": p.reason,
                        }
                        for p in br.posts
                    ],
                    "tokens_used": br.tokens_used,
                    "processing_time": f"{br.processing_time:.2f}s",
                }
                for br in self.batch_results
            ],
        }


class InterviewFilter:
    """
    Filters posts using LLM to identify interview-related content.

    This is a pre-filtering step before the main extraction process.
    Uses a lighter/cheaper model with larger batch sizes for efficiency.
    """

    def __init__(self, config: FilterConfig):
        """
        Initialize the filter.

        Args:
            config: Filter configuration
        """
        self.config = config
        self.provider = config.provider.lower()

        # Validate provider
        if self.provider not in ["anthropic", "openai"]:
            raise ValueError(f"Unsupported provider: {self.provider}")

        # Check required packages
        if self.provider == "anthropic" and anthropic is None:
            raise ImportError("anthropic package required. Run: pip install anthropic")
        if self.provider == "openai" and openai is None:
            raise ImportError("openai package required. Run: pip install openai")

        # Get API key
        env_var_name = "ANTHROPIC_API_KEY" if self.provider == "anthropic" else "OPENAI_API_KEY"
        self.api_key = config.api_key or os.environ.get(env_var_name)
        if not self.api_key:
            raise ValueError(
                f"API key required. Set in config or {env_var_name} environment variable."
            )

        # Initialize client
        client_kwargs = {"api_key": self.api_key}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url

        if self.provider == "anthropic":
            self.client = anthropic.Anthropic(**client_kwargs)
        else:
            self.client = openai.OpenAI(**client_kwargs)

    def _call_llm_api(self, system_prompt: str, user_prompt: str) -> Tuple[str, int, int]:
        """
        Call LLM API with unified interface.

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
                messages=[{"role": "user", "content": user_prompt}],
            )
            response_text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
        else:
            # OpenAI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
            response_text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

        return response_text, input_tokens, output_tokens

    def _parse_filter_response(
        self, response_text: str, batch_post_summaries: List[Dict[str, Any]]
    ) -> List[PostFilterResult]:
        """
        Parse JSON response from LLM.

        Args:
            response_text: Raw LLM response
            batch_post_summaries: Original post summaries for fallback

        Returns:
            List of PostFilterResult
        """
        # Try to extract JSON from code blocks
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = response_text.strip()

        try:
            data = json.loads(json_str)
            posts_data = data.get("posts", [])

            results = []
            for post_data in posts_data:
                # Find corresponding original index
                post_index = post_data.get("post_index", 0)
                original_index = -1
                title = post_data.get("title", "")

                # Match with batch summaries
                for summary in batch_post_summaries:
                    if summary["index"] == post_index:
                        original_index = summary.get("original_index", post_index)
                        if not title:
                            title = summary["title"]
                        break

                results.append(
                    PostFilterResult(
                        post_index=post_index,
                        original_index=original_index,
                        title=title,
                        is_interview_related=post_data.get("is_interview_related", True),
                        confidence=post_data.get("confidence", 0.5),
                        reason=post_data.get("reason", ""),
                    )
                )

            return results

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse filter response: {e}")
            # Return all posts as interview-related (safe fallback)
            return [
                PostFilterResult(
                    post_index=s["index"],
                    original_index=s.get("original_index", s["index"]),
                    title=s["title"],
                    is_interview_related=True,
                    confidence=0.0,
                    reason="Parse error - kept as fallback",
                )
                for s in batch_post_summaries
            ]

    def filter_batch(
        self, posts: List[Dict[str, Any]], batch_index: int, start_index: int = 0
    ) -> BatchFilterResult:
        """
        Filter a single batch of posts.

        Args:
            posts: List of posts in this batch
            batch_index: Index of this batch
            start_index: Starting index for post numbering

        Returns:
            BatchFilterResult
        """
        start_time = time.time()
        print(f"  [Batch {batch_index}] Processing {len(posts)} posts...")

        # Prepare summaries with original indices
        summaries = []
        for i, post in enumerate(posts):
            summary = prepare_post_summary(post, i)
            summary["original_index"] = start_index + i
            summaries.append(summary)

        # Generate prompt
        user_prompt = get_filter_prompt(summaries)

        # Call LLM
        try:
            response_text, input_tokens, output_tokens = self._call_llm_api(
                FILTER_SYSTEM_PROMPT, user_prompt
            )
            tokens_used = input_tokens + output_tokens

            # Parse response
            post_results = self._parse_filter_response(response_text, summaries)

            processing_time = time.time() - start_time
            print(
                f"  [Batch {batch_index}] Done: {len(post_results)} results, "
                f"{tokens_used} tokens, {processing_time:.2f}s"
            )

            return BatchFilterResult(
                batch_index=batch_index,
                posts=post_results,
                raw_response=response_text,
                tokens_used=tokens_used,
                processing_time=processing_time,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            print(f"  [Batch {batch_index}] Error: {e}")

            # Return all posts as interview-related (safe fallback)
            fallback_results = [
                PostFilterResult(
                    post_index=s["index"],
                    original_index=s["original_index"],
                    title=s["title"],
                    is_interview_related=True,
                    confidence=0.0,
                    reason=f"API error - kept as fallback: {str(e)}",
                )
                for s in summaries
            ]

            return BatchFilterResult(
                batch_index=batch_index,
                posts=fallback_results,
                raw_response=str(e),
                tokens_used=0,
                processing_time=processing_time,
            )

    def filter_posts(
        self, posts: List[Dict[str, Any]], verbose: bool = True
    ) -> Tuple[List[Dict[str, Any]], FilteringResult]:
        """
        Filter all posts and return kept posts with results.

        Args:
            posts: List of all posts to filter
            verbose: Print progress messages

        Returns:
            Tuple of (kept_posts, FilteringResult)
        """
        start_time = time.time()
        total_posts = len(posts)

        if verbose:
            print(f"\n{'='*70}")
            print(f"LLM Filter: Processing {total_posts} posts")
            print(f"Model: {self.config.model}")
            print(f"Batch size: {self.config.posts_per_batch}")
            print(f"Confidence threshold: {self.config.confidence_threshold}")
            print(f"{'='*70}\n")

        # Split into batches
        batches = []
        for i in range(0, total_posts, self.config.posts_per_batch):
            batch = posts[i : i + self.config.posts_per_batch]
            batches.append((batch, i))

        total_batches = len(batches)
        batch_results = []
        all_post_results: Dict[int, PostFilterResult] = {}

        # Process each batch
        for batch_idx, (batch, start_idx) in enumerate(batches, 1):
            if verbose:
                print(f"[{batch_idx}/{total_batches}] Filtering batch...")

            result = self.filter_batch(batch, batch_idx, start_idx)
            batch_results.append(result)

            # Collect results
            for pr in result.posts:
                all_post_results[pr.original_index] = pr

            # Rate limiting
            if batch_idx < total_batches and self.config.delay_between_calls > 0:
                time.sleep(self.config.delay_between_calls)

        # Determine which posts to keep
        kept_indices = []
        filtered_indices = []
        kept_posts = []

        for i, post in enumerate(posts):
            pr = all_post_results.get(i)
            if pr is None:
                # Post not in results - keep it
                kept_indices.append(i)
                kept_posts.append(post)
            elif pr.is_interview_related:
                kept_indices.append(i)
                kept_posts.append(post)
            elif pr.confidence < self.config.confidence_threshold:
                # Low confidence that it's NOT interview-related - keep it
                kept_indices.append(i)
                kept_posts.append(post)
            else:
                filtered_indices.append(i)

        total_time = time.time() - start_time
        total_tokens = sum(br.tokens_used for br in batch_results)

        filtering_result = FilteringResult(
            batch_results=batch_results,
            kept_posts=kept_posts,
            kept_post_indices=kept_indices,
            filtered_post_indices=filtered_indices,
            total_posts=total_posts,
            posts_kept=len(kept_posts),
            posts_filtered=len(filtered_indices),
            total_tokens_used=total_tokens,
            total_processing_time=total_time,
            generated_at=datetime.now().isoformat(),
        )

        if verbose:
            print(f"\n{'='*70}")
            print(f"LLM Filter Complete!")
            print(f"  Total posts: {total_posts}")
            print(f"  Posts kept: {len(kept_posts)} ({len(kept_posts)/total_posts*100:.1f}%)")
            print(f"  Posts filtered: {len(filtered_indices)} ({len(filtered_indices)/total_posts*100:.1f}%)")
            print(f"  Total tokens: {total_tokens}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"{'='*70}\n")

        return kept_posts, filtering_result

    def save_results(self, result: FilteringResult, output_dir: Optional[str] = None) -> str:
        """
        Save filtering results to JSON file.

        Args:
            result: FilteringResult to save
            output_dir: Output directory (defaults to config.output_dir)

        Returns:
            Path to saved file
        """
        output_dir = output_dir or self.config.output_dir
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, self.config.results_filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

        print(f"Filter results saved to: {filepath}")
        return filepath
