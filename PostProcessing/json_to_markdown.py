#!/usr/bin/env python3
"""
Convert combined JSON results from 1point3acres scraper to Markdown format.

Usage:
    python json_to_markdown.py <input_json> [output_md]

Example:
    python json_to_markdown.py ../scraper_output/combined_results_20260121_020225.json output.md
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# URLs to filter out (e.g., welcome/intro posts)
FILTERED_URLS = [
    "https://www.1point3acres.com/bbs/thread-71069-1-1.html",
]


def remove_quote_prefix(content: str) -> str:
    """
    Remove quote prefix patterns from the beginning of content.

    Patterns handled:
        1. "username 发表于 timestamp" - quote attribution
           Examples: "匿名用户 发表于 2026-01-16 13:47:13\n..."
        2. "本帖最后由 xxx 于 xxx 编辑" - edit note
           Examples: "本帖最后由 匿名 于 2025-12-22 15:51 编辑 \n..."

    These patterns can appear together or separately.
    """
    if not content:
        return content

    result = content

    # Keep removing patterns until no more matches
    changed = True
    while changed:
        changed = False

        # Pattern 0: Site watermark - ". 1point3acres" or "1point3acres" at the beginning
        watermark_match = re.match(r'^\.?\s*1point3acres\s*\n?', result)
        if watermark_match:
            result = result[watermark_match.end():].strip()
            changed = True
            continue

        # Pattern 1: Edit note - "本帖最后由 xxx 于 xxx 编辑"
        # Format: 本帖最后由 username 于 date time 编辑
        edit_match = re.match(r'^本帖最后由\s+.+?\s+于\s+[\d\-]+\s+[\d:]+\s*编辑\s*\.?\s*\n?', result)
        if edit_match:
            result = result[edit_match.end():].strip()
            changed = True
            continue

        # Pattern 2: Quote attribution - "username 发表于 timestamp"
        # Also handles various suffixes like ". Χ" or ". 1point3acres"
        quote_match = re.match(r'^.+?\s+发表于\s+[\d\-]+\s+[\d:]+[^\n]*\n?', result)
        if quote_match:
            result = result[quote_match.end():].strip()
            changed = True
            continue

    return result


def clean_content_from_quote(content: str, quote: str) -> str:
    """
    Remove the quote part from the beginning of content.

    Content format: "username 发表于 timestamp\\n<quoted text>\\n<actual reply>"
    Quote format: "username 发表于 timestamp <quoted text>..." (spaces instead of newlines, may be truncated)
    """
    if not quote or not content:
        return content

    # The quote in content has newlines, but quote array has spaces
    # Find where the actual reply starts by looking for the pattern

    # First, check if content starts with username pattern "XXX 发表于"
    match = re.match(r'^.+?\s+发表于\s+[\d\-:\s]+\n', content)
    if match:
        # Content has quote prefix, find where it ends
        # The quote text follows the username line until the actual reply
        after_username = content[match.end():]

        # The quote array contains: "username 发表于 timestamp quoted_text..."
        # Extract just the quoted text part (after timestamp)
        quote_match = re.match(r'^.+?\s+发表于\s+[\d\-:\s]+\s*', quote)
        if quote_match:
            quoted_text = quote[quote_match.end():].rstrip(' .')

            # Find where quoted_text ends in after_username
            if quoted_text and after_username.startswith(quoted_text):
                actual_reply = after_username[len(quoted_text):].strip()
                return actual_reply
            elif quoted_text:
                # Truncated quote - find partial match
                for i in range(len(quoted_text), 10, -1):
                    if after_username.startswith(quoted_text[:i]):
                        # Find next newline after the quote
                        rest = after_username[i:]
                        newline_pos = rest.find('\n')
                        if newline_pos >= 0:
                            return rest[newline_pos:].strip()
                        return rest.strip()

        # Fallback: just remove the first line (username line) and return the rest
        # But we need to identify where the actual reply starts
        # Usually after the quoted content there's a newline
        lines = after_username.split('\n')
        if len(lines) > 1:
            # The first part might be the quoted text, actual reply is after
            return '\n'.join(lines[1:]).strip() if lines[1:] else after_username

    return content


def extract_reply_data(reply: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract data from a single reply, cleaning the content."""
    if not isinstance(reply, dict):
        return None

    content = reply.get('content', '')
    quotes = reply.get('quotes', [])

    # Get the quote if exists
    quote = quotes[0] if quotes else ''

    # Clean content by removing quote
    cleaned_content = clean_content_from_quote(content, quote)

    # Also remove any remaining quote prefix pattern (e.g., "匿名用户 发表于 2026-01-16...")
    cleaned_content = remove_quote_prefix(cleaned_content)

    # Normalize the quote: extract the quoted content (what the person is replying to)
    # Quote format: "username 发表于 timestamp quoted_text..."
    normalized_quote = ""
    if quote:
        # Remove username and timestamp prefix
        match = re.match(r'^.+?\s+发表于\s+[\d\-:\s]+\s*', quote)
        if match:
            normalized_quote = quote[match.end():].strip()
        else:
            normalized_quote = quote.strip()

        # Remove trailing "..." or " ..."
        if normalized_quote.endswith(' ...'):
            normalized_quote = normalized_quote[:-4]
        elif normalized_quote.endswith('...'):
            normalized_quote = normalized_quote[:-3]

    return {
        'content': content,
        'quote': normalized_quote,
        'cleaned_content': cleaned_content,
    }


def build_reply_hierarchy(replies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build hierarchical structure of replies based on quotes.

    Returns:
        Dict with 'main_content' and 'replies' (list of hierarchical reply nodes)
    """
    if not replies:
        return {'main_content': '', 'replies': []}

    # Extract data from all replies
    replies_data = []
    for reply in replies:
        reply_data = extract_reply_data(reply)
        if reply_data:
            replies_data.append(reply_data)

    if not replies_data:
        return {'main_content': '', 'replies': []}

    # First reply is the main content
    main_content = replies_data[0]['cleaned_content']

    if len(replies_data) == 1:
        return {'main_content': main_content, 'replies': []}

    # Build parent->children mapping based on quotes
    contents = []
    parent2children = {}

    for rd in replies_data[1:]:
        if rd['quote'] and rd['cleaned_content']:
            parent2children.setdefault(rd['quote'], []).append(rd['cleaned_content'])
        contents.append(rd['cleaned_content'])

    # Fix truncated quotes - map them to full content
    current_quotes = list(parent2children.keys())
    quotes_to_del = set()
    for quote in current_quotes:
        for content in contents:
            if content.startswith(quote) and content != quote and quote:
                # Merge children lists if target already exists
                if content in parent2children:
                    parent2children[content].extend(parent2children[quote])
                else:
                    parent2children[content] = parent2children[quote]
                quotes_to_del.add(quote)
                break  # Only map to first matching content

    for quote in quotes_to_del:
        if quote in parent2children:
            del parent2children[quote]

    # Build tree structure
    class ReplyNode:
        def __init__(self, content: str):
            self.content = content
            self.parent = None
            self.children = []

        def to_dict(self) -> Dict[str, Any]:
            result = {"content": self.content}
            if self.children:
                result["children"] = [child.to_dict() for child in self.children]
            return result

    # Create all nodes
    content2node = {}
    for rd in replies_data[1:]:
        node = ReplyNode(rd["cleaned_content"])
        content2node[rd["cleaned_content"]] = node

    # Link children to parents
    for content, children in parent2children.items():
        if content in content2node:
            for child_content in children:
                if child_content in content2node:
                    content2node[content].children.append(content2node[child_content])
                    content2node[child_content].parent = content2node[content]

    # Find root nodes (no parent)
    root_nodes = [node for node in content2node.values() if not node.parent]

    return {
        'main_content': main_content,
        'replies': [node.to_dict() for node in root_nodes]
    }


def format_nested_reply(reply_node: Dict[str, Any], depth: int = 0) -> List[str]:
    """Format a reply node with nested children using indentation."""
    lines = []
    indent = "  " * depth

    content = reply_node.get("content", "").strip()
    # Clean up content - preserve newlines but trim each line
    content_lines = content.split('\n')
    content_lines = [line.strip() for line in content_lines if line.strip()]

    if content_lines:
        # First line with bullet
        lines.append(f"{indent}- {content_lines[0]}")
        # Additional lines with proper indentation
        for line in content_lines[1:]:
            lines.append(f"{indent}  {line}")

    # Process children with increased depth
    children = reply_node.get("children", [])
    for child in children:
        lines.extend(format_nested_reply(child, depth + 1))

    return lines


def get_post_published_time(post_data: dict) -> str:
    """Extract the published time from the first reply (main post)."""
    items = post_data.get("items", {})
    main_post = items.get("main_post")
    if main_post and isinstance(main_post, dict):
        return main_post.get("timestamp", "")
    replies = items.get("replies", [])
    if replies:
        return replies[0].get("timestamp", "")
    return ""


def convert_post_to_markdown(post_data: dict) -> str:
    """Convert a single post entry to markdown format."""
    lines = []

    # URL as header
    url = post_data.get("url", "Unknown URL")
    lines.append(f"## [{url}]({url})")
    lines.append("")

    # Metadata
    metadata = post_data.get("metadata", {})
    thread_title = metadata.get("thread_title", "").strip()
    if thread_title:
        lines.append(f"### {thread_title}")
        lines.append("")

    tags = metadata.get("thread_tags", [])
    if tags:
        lines.append(f"**Tags:** {', '.join(tags)}")
        lines.append("")

    # Published time
    published_time = get_post_published_time(post_data)
    if published_time:
        lines.append(f"**Published:** {published_time}")
        lines.append("")

    lines.append("---")
    lines.append("")

    items = post_data.get("items", {})
    replies = items.get("replies", [])

    # Combine main_post and replies for hierarchy building
    all_replies = []
    main_post = items.get("main_post")
    if main_post and isinstance(main_post, dict):
        all_replies.append(main_post)
    all_replies.extend(replies)

    # Build hierarchical structure
    hierarchy = build_reply_hierarchy(all_replies)

    # Main post content
    main_content = hierarchy.get('main_content', '')
    if main_content:
        lines.append("### Main Post")
        lines.append("")
        lines.append(main_content)
        lines.append("")

    # Replies with nested structure
    reply_nodes = hierarchy.get('replies', [])
    if reply_nodes:
        lines.append(f"### Replies ({len(reply_nodes)})")
        lines.append("")
        for reply_node in reply_nodes:
            reply_lines = format_nested_reply(reply_node)
            lines.extend(reply_lines)
        lines.append("")

    return "\n".join(lines)


def json_to_markdown(input_path: str, output_path: str = None) -> str:
    """
    Convert JSON results file to Markdown format.

    Args:
        input_path: Path to the input JSON file
        output_path: Path to the output Markdown file (optional)

    Returns:
        Path to the generated Markdown file
    """
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Default output path
    if output_path is None:
        output_path = input_file.with_suffix(".md")

    output_file = Path(output_path)

    # Load JSON data
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build markdown content
    md_lines = []

    # Title and summary
    workflow = data.get("workflow", "Unknown Workflow")
    md_lines.append(f"# {workflow}")
    md_lines.append("")

    # Configuration
    config = data.get("config", {})
    if config:
        md_lines.append("## Configuration")
        md_lines.append("")
        md_lines.append(f"- **Base URL:** {config.get('base_url', 'N/A')}")
        md_lines.append(f"- **Pages:** {config.get('num_pages', 'N/A')}")
        md_lines.append("")

    # Summary
    summary = data.get("summary", {})
    if summary:
        md_lines.append("## Summary")
        md_lines.append("")
        md_lines.append(f"- **Pages Processed:** {summary.get('pages_processed', 'N/A')}")
        md_lines.append(f"- **Total Posts Parsed:** {summary.get('total_posts_parsed', 'N/A')}")
        md_lines.append(f"- **Generated At:** {summary.get('generated_at', 'N/A')}")
        md_lines.append("")

    md_lines.append("---")
    md_lines.append("")
    md_lines.append("# Posts")
    md_lines.append("")

    # Process each post (filter out unwanted URLs)
    posts = data.get("posts", [])
    filtered_posts = [p for p in posts if p.get("url") not in FILTERED_URLS]
    filtered_count = len(posts) - len(filtered_posts)

    for post_data in filtered_posts:
        md_lines.append(convert_post_to_markdown(post_data))
        md_lines.append("")

    # Write output
    markdown_content = "\n".join(md_lines)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"Converted {len(filtered_posts)} posts to Markdown (filtered out {filtered_count})")
    print(f"Output written to: {output_file}")

    return str(output_file)


def process_post_to_hierarchy(post_data: dict) -> Optional[Dict[str, Any]]:
    """
    Process a single post and return hierarchical JSON structure.

    Returns:
        Dict with url, title, tags, published_time, main_content, and hierarchical replies
    """
    url = post_data.get("url", "")
    if url in FILTERED_URLS:
        return None

    metadata = post_data.get("metadata", {})
    thread_title = metadata.get("thread_title", "").strip()
    tags = metadata.get("thread_tags", [])

    # Get published time from main post
    published_time = get_post_published_time(post_data)

    items = post_data.get("items", {})
    replies = items.get("replies", [])

    # Combine main_post and replies for hierarchy building
    all_replies = []
    main_post = items.get("main_post")
    if main_post and isinstance(main_post, dict):
        all_replies.append(main_post)
    all_replies.extend(replies)

    # Build hierarchical structure
    hierarchy = build_reply_hierarchy(all_replies)

    return {
        "url": url,
        "title": thread_title,
        "tags": tags,
        "published_time": published_time,
        "main_content": hierarchy.get("main_content", ""),
        "replies": hierarchy.get("replies", [])
    }


def json_to_processed_json(input_path: str, output_path: str = None) -> str:
    """
    Convert JSON results to a cleaned JSON with hierarchical reply structure.

    Args:
        input_path: Path to the input JSON file
        output_path: Path to the output JSON file (optional)

    Returns:
        Path to the generated JSON file
    """
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Default output path
    if output_path is None:
        output_path = input_file.parent / f"{input_file.stem}_processed.json"

    output_file = Path(output_path)

    # Load JSON data
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build processed structure
    processed = {
        "config": data.get("config", {}),
        "summary": data.get("summary", {}),
        "posts": []
    }

    # Process each post
    posts = data.get("posts", [])
    for post_data in posts:
        processed_post = process_post_to_hierarchy(post_data)
        if processed_post:
            processed["posts"].append(processed_post)

    # Update summary
    processed["summary"]["posts_after_filter"] = len(processed["posts"])

    # Write output
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

    print(f"Processed {len(processed['posts'])} posts to JSON")
    print(f"JSON output written to: {output_file}")

    return str(output_file)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        # Generate both markdown and processed JSON
        md_result = json_to_markdown(input_path, output_path)
        print(f"Success! Markdown: {md_result}")

        # Also generate processed JSON
        json_result = json_to_processed_json(input_path)
        print(f"Success! JSON: {json_result}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
