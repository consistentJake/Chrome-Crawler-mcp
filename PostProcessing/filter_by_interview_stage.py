#!/usr/bin/env python3
"""
Filter and sort posts by interview_stage from extracted interviews.

Usage:
    python filter_by_interview_stage.py <extracted_json> <processed_json> [output_md]

Example:
    python filter_by_interview_stage.py \
        ../output_20260127_014850/extracted_interviews_20260127_033819.json \
        ../workflows/scraper_output/1point3acres_results_20260127_004826_processed.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from json_to_markdown import (
    format_nested_reply,
    FILTERED_URLS,
)

# Interview stages to filter out
FILTERED_STAGES = ["未知", "N/A", "无有效信息"]

# Interview stage priority for sorting (lower = earlier in pipeline)
STAGE_PRIORITY = {
    # Application / Initial
    "内推后等待": 10,
    "流程咨询": 15,
    "HR Call": 20,
    "HR Phone Screen": 21,
    "HR 面": 22,
    "Recruiter Call": 25,

    # OA
    "OA": 30,
    "OA（CodeSignal）": 31,
    "OA + 后续流程": 32,
    "OA -> 二轮 Coding": 33,
    "OA 后无回复": 35,

    # Take-home
    "Take-home": 40,
    "take-home assignment": 41,
    "Take-home Assignment": 42,
    "Take-Home + VO(5轮)": 45,
    "Take-home + VO（4 轮）": 46,

    # Phone Screen / 店面
    "电话面试": 50,
    "电面": 51,
    "电话面试/店面": 52,
    "手机店面": 53,
    "店面": 55,
    "Technical Phone Screen (TPS)": 56,
    "Initial Interview": 57,
    "Technical Interview（首轮）": 58,

    # Combined stages
    "店面 + VO": 60,
    "店面+VO": 61,
    "店面+Onsite": 62,
    "店面+Onsite(5轮)": 63,
    "电面+Onsite": 64,
    "电面+VO": 65,
    "电话面试 + VO（2 天）": 66,

    # VO / Onsite
    "VO": 70,
    "VO/Onsite": 71,
    "VO/店面": 72,
    "VO（Virtual Onsite）": 73,
    "VO（5 轮）": 74,
    "Onsite": 75,
    "Onsite（5 轮）": 76,
    "Onsite 安排": 77,
    "Onsite SD Q1": 78,
    "重新面试（3 轮）": 79,

    # Specific rounds
    "System Design": 80,
    "Tech Deep Dive": 81,
    "Culture Fit": 82,
    "HM 面": 83,
    "行为/文化面": 84,

    # Post-VO
    "VO后等待": 90,
    "VO 通过后": 91,
    "Team Match": 92,

    # Final / Offer
    "终面/offer": 95,
    "终面/已拿 offer": 96,
    "Offer": 97,
    "Offer 阶段": 98,
    "Offer 比较": 99,

    # Comprehensive
    "全流程": 100,
    "综合": 101,
}


def load_extracted_interviews(path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load extracted interviews and build URL -> extraction data mapping.

    Returns:
        Dict mapping source_url to extraction data (interview_stage, position_type, etc.)
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    url_to_extraction = {}
    for group in data.get("extractions", []):
        for post in group.get("posts", []):
            url = post.get("source_url", "")
            if url:
                url_to_extraction[url] = {
                    "interview_stage": post.get("interview_stage", "未知"),
                    "position_type": post.get("position_type", "未知"),
                    "interview_info": post.get("interview_info", {}),
                    "from_replies": post.get("from_replies", {}),
                    "metadata": post.get("metadata", {}),
                }

    return url_to_extraction


def get_stage_priority(stage: str) -> int:
    """Get sorting priority for an interview stage."""
    return STAGE_PRIORITY.get(stage, 500)  # Unknown stages go last


def filter_and_sort_posts(
    processed_posts: List[Dict[str, Any]],
    url_to_extraction: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Filter out posts with filtered stages and sort by interview_stage.

    Returns:
        List of posts enriched with extraction data, filtered and sorted.
    """
    enriched_posts = []

    for post in processed_posts:
        url = post.get("url", "")

        # Skip filtered URLs
        if url in FILTERED_URLS:
            continue

        # Get extraction data
        extraction = url_to_extraction.get(url, {})
        stage = extraction.get("interview_stage", "未知")

        # Filter out unwanted stages
        if stage in FILTERED_STAGES:
            continue

        # Enrich post with extraction data
        enriched_post = {
            **post,
            "interview_stage": stage,
            "position_type": extraction.get("position_type", "未知"),
            "interview_info": extraction.get("interview_info", {}),
            "extraction_metadata": extraction.get("metadata", {}),
        }
        enriched_posts.append(enriched_post)

    # Sort by interview stage priority
    enriched_posts.sort(key=lambda p: get_stage_priority(p["interview_stage"]))

    return enriched_posts


def convert_enriched_post_to_markdown(post: Dict[str, Any]) -> str:
    """Convert an enriched post to markdown format."""
    lines = []

    # URL as header
    url = post.get("url", "Unknown URL")
    lines.append(f"## [{url}]({url})")
    lines.append("")

    # Title
    title = post.get("title", "").strip()
    if title:
        # Clean up title (remove prefixes like [面试经验])
        clean_title = title.replace("[面试经验]\n", "").replace("[找工就业]\n", "").replace("[工作信息]\n", "").strip()
        lines.append(f"### {clean_title}")
        lines.append("")

    # Interview stage and position type (from extraction)
    stage = post.get("interview_stage", "")
    position = post.get("position_type", "")
    if stage:
        lines.append(f"**Interview Stage:** {stage}")
    if position and position != "未知":
        lines.append(f"**Position Type:** {position}")
    lines.append("")

    # Tags
    tags = post.get("tags", [])
    if tags:
        lines.append(f"**Tags:** {', '.join(tags)}")
        lines.append("")

    # Published time
    published_time = post.get("published_time", "")
    if published_time:
        lines.append(f"**Published:** {published_time}")
        lines.append("")

    # Interview info from extraction
    interview_info = post.get("interview_info", {})
    if interview_info:
        lines.append("**Interview Details:**")
        if interview_info.get("题目类型"):
            lines.append(f"- 题目类型: {interview_info['题目类型']}")
        if interview_info.get("时长") and interview_info["时长"] != "N/A":
            lines.append(f"- 时长: {interview_info['时长']}")
        if interview_info.get("题目描述") and interview_info["题目描述"] != "无有效信息":
            lines.append(f"- 题目描述: {interview_info['题目描述']}")
        if interview_info.get("具体要求"):
            lines.append(f"- 具体要求: {', '.join(interview_info['具体要求'])}")
        if interview_info.get("考察重点"):
            lines.append(f"- 考察重点: {', '.join(interview_info['考察重点'])}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Main content
    main_content = post.get("main_content", "")
    if main_content:
        lines.append("### Main Post")
        lines.append("")
        lines.append(main_content)
        lines.append("")

    # Replies
    reply_nodes = post.get("replies", [])
    if reply_nodes:
        lines.append(f"### Replies ({len(reply_nodes)})")
        lines.append("")
        for reply_node in reply_nodes:
            reply_lines = format_nested_reply(reply_node)
            lines.extend(reply_lines)
        lines.append("")

    return "\n".join(lines)


def convert_to_markdown(
    enriched_posts: List[Dict[str, Any]],
    output_path: str,
) -> str:
    """Convert enriched posts to markdown file."""
    md_lines = []

    # Title
    md_lines.append("# Interview Experiences by Stage")
    md_lines.append("")
    md_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append(f"**Total Posts:** {len(enriched_posts)}")
    md_lines.append("")

    # Summary by stage
    stage_counts = {}
    for post in enriched_posts:
        stage = post.get("interview_stage", "Unknown")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    md_lines.append("## Summary by Interview Stage")
    md_lines.append("")
    for stage in sorted(stage_counts.keys(), key=get_stage_priority):
        md_lines.append(f"- **{stage}:** {stage_counts[stage]} posts")
    md_lines.append("")

    md_lines.append("---")
    md_lines.append("")
    md_lines.append("# Posts")
    md_lines.append("")

    # Group posts by stage
    current_stage = None
    for post in enriched_posts:
        stage = post.get("interview_stage", "Unknown")
        if stage != current_stage:
            current_stage = stage
            md_lines.append(f"# Stage: {stage}")
            md_lines.append("")

        md_lines.append(convert_enriched_post_to_markdown(post))
        md_lines.append("")

    # Write output
    markdown_content = "\n".join(md_lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    return output_path


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    extracted_path = sys.argv[1]
    processed_path = sys.argv[2]

    # Default output path
    if len(sys.argv) > 3:
        output_path = sys.argv[3]
    else:
        processed_file = Path(processed_path)
        output_path = processed_file.parent / f"{processed_file.stem}_filtered_by_stage.md"

    # Load data
    print(f"Loading extracted interviews from: {extracted_path}")
    url_to_extraction = load_extracted_interviews(extracted_path)
    print(f"  Found {len(url_to_extraction)} extractions")

    print(f"Loading processed posts from: {processed_path}")
    with open(processed_path, "r", encoding="utf-8") as f:
        processed_data = json.load(f)
    posts = processed_data.get("posts", [])
    print(f"  Found {len(posts)} posts")

    # Filter and sort
    print(f"Filtering (excluding stages: {FILTERED_STAGES})...")
    enriched_posts = filter_and_sort_posts(posts, url_to_extraction)
    print(f"  {len(enriched_posts)} posts after filtering")

    # Convert to markdown
    print(f"Converting to markdown: {output_path}")
    convert_to_markdown(enriched_posts, str(output_path))

    print(f"\nSuccess! Output written to: {output_path}")

    # Print stage summary
    stage_counts = {}
    for post in enriched_posts:
        stage = post.get("interview_stage", "Unknown")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    print("\nPosts by interview stage:")
    for stage in sorted(stage_counts.keys(), key=get_stage_priority):
        print(f"  {stage}: {stage_counts[stage]}")


if __name__ == "__main__":
    main()
