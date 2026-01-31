"""
Markdown Converter Module

Converts JSON post data to structured Markdown format for LLM processing.
Uses hierarchical reply structure with proper parent/child relationships.
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared import (
    SKIP_KEYWORDS,
    LOW_VALUE_PATTERNS,
    is_low_value_content,
    get_post_title,
    get_main_content,
    get_replies,
    get_post_url,
)


def remove_quote_prefix(content: str) -> str:
    """
    Remove quote prefix patterns from the beginning of content.

    Patterns handled:
        1. "username 发表于 timestamp" - quote attribution
        2. "本帖最后由 xxx 于 xxx 编辑" - edit note
        3. "1point3acres" - site watermark
    """
    if not content:
        return content

    result = content

    # Keep removing patterns until no more matches
    changed = True
    while changed:
        changed = False

        # Pattern 0: Site watermark
        watermark_match = re.match(r'^\.?\s*1point3acres\s*\n?', result)
        if watermark_match:
            result = result[watermark_match.end():].strip()
            changed = True
            continue

        # Pattern 1: Edit note
        edit_match = re.match(r'^本帖最后由\s+.+?\s+于\s+[\d\-]+\s+[\d:]+\s*编辑\s*\.?\s*\n?', result)
        if edit_match:
            result = result[edit_match.end():].strip()
            changed = True
            continue

        # Pattern 2: Quote attribution
        quote_match = re.match(r'^.+?\s+发表于\s+[\d\-]+\s+[\d:]+[^\n]*\n?', result)
        if quote_match:
            result = result[quote_match.end():].strip()
            changed = True
            continue

    return result


def clean_content_from_quote(content: str, quote: str) -> str:
    """Remove the quote part from the beginning of content."""
    if not quote or not content:
        return content

    # First, check if content starts with username pattern
    match = re.match(r'^.+?\s+发表于\s+[\d\-:\s]+\n', content)
    if match:
        after_username = content[match.end():]
        quote_match = re.match(r'^.+?\s+发表于\s+[\d\-:\s]+\s*', quote)
        if quote_match:
            quoted_text = quote[quote_match.end():].rstrip(' .')
            if quoted_text and after_username.startswith(quoted_text):
                actual_reply = after_username[len(quoted_text):].strip()
                return actual_reply
            elif quoted_text:
                for i in range(len(quoted_text), 10, -1):
                    if after_username.startswith(quoted_text[:i]):
                        rest = after_username[i:]
                        newline_pos = rest.find('\n')
                        if newline_pos >= 0:
                            return rest[newline_pos:].strip()
                        return rest.strip()

        lines = after_username.split('\n')
        if len(lines) > 1:
            return '\n'.join(lines[1:]).strip() if lines[1:] else after_username

    return content


def extract_reply_data(reply: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract data from a single reply, cleaning the content."""
    if not isinstance(reply, dict):
        return None

    content = reply.get('content', '')
    quotes = reply.get('quotes', [])

    quote = quotes[0] if quotes else ''
    cleaned_content = clean_content_from_quote(content, quote)
    cleaned_content = remove_quote_prefix(cleaned_content)

    # Normalize the quote
    normalized_quote = ""
    if quote:
        match = re.match(r'^.+?\s+发表于\s+[\d\-:\s]+\s*', quote)
        if match:
            normalized_quote = quote[match.end():].strip()
        else:
            normalized_quote = quote.strip()

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

    replies_data = []
    for reply in replies:
        reply_data = extract_reply_data(reply)
        if reply_data:
            replies_data.append(reply_data)

    if not replies_data:
        return {'main_content': '', 'replies': []}

    main_content = replies_data[0]['cleaned_content']

    if len(replies_data) == 1:
        return {'main_content': main_content, 'replies': []}

    # Build parent->children mapping
    contents = []
    parent2children = {}

    for rd in replies_data[1:]:
        if rd['quote'] and rd['cleaned_content']:
            parent2children.setdefault(rd['quote'], []).append(rd['cleaned_content'])
        contents.append(rd['cleaned_content'])

    # Fix truncated quotes
    current_quotes = list(parent2children.keys())
    quotes_to_del = set()
    for quote in current_quotes:
        for content in contents:
            if content.startswith(quote) and content != quote and quote:
                if content in parent2children:
                    parent2children[content].extend(parent2children[quote])
                else:
                    parent2children[content] = parent2children[quote]
                quotes_to_del.add(quote)
                break

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

    content2node = {}
    for rd in replies_data[1:]:
        node = ReplyNode(rd["cleaned_content"])
        content2node[rd["cleaned_content"]] = node

    for content, children in parent2children.items():
        if content in content2node:
            for child_content in children:
                if child_content in content2node:
                    content2node[content].children.append(content2node[child_content])
                    content2node[child_content].parent = content2node[content]

    root_nodes = [node for node in content2node.values() if not node.parent]

    return {
        'main_content': main_content,
        'replies': [node.to_dict() for node in root_nodes]
    }


class MarkdownConverter:
    """Converts forum post data to Markdown format."""

    def __init__(self, min_content_length: int = 50):
        """
        Initialize the converter.

        Args:
            min_content_length: Minimum character length for main content
        """
        self.min_content_length = min_content_length

    def should_skip_post(self, post: Dict[str, Any]) -> bool:
        """
        Check if a post should be skipped based on keywords.

        Args:
            post: Post dictionary

        Returns:
            True if post should be skipped
        """
        title = get_post_title(post)
        main_content = get_main_content(post)

        # Check title and content for skip keywords
        for keyword in SKIP_KEYWORDS:
            if keyword in title or keyword in main_content:
                return True

        # Check if main content is too short
        if len(main_content) < self.min_content_length:
            return True

        return False

    def _is_low_value_reply(self, content: str) -> bool:
        """Check if a reply is low-value (just thanks, etc.)."""
        return is_low_value_content(content, LOW_VALUE_PATTERNS, min_length=10)

    def _format_nested_reply(self, reply_node: Dict[str, Any], depth: int = 0) -> List[str]:
        """
        Format a reply node with nested children using indentation.

        Args:
            reply_node: Reply node dict with 'content' and optional 'children'
            depth: Indentation depth

        Returns:
            List of formatted lines
        """
        lines = []
        indent = "  " * depth

        content = reply_node.get("content", "").strip()

        # Skip low-value replies
        if self._is_low_value_reply(content):
            return lines

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
            lines.extend(self._format_nested_reply(child, depth + 1))

        return lines

    def _get_published_time(self, post: Dict[str, Any]) -> str:
        """Extract the published time from the first reply (main post)."""
        items = post.get("items", {})
        main_post = items.get("main_post")
        if main_post and isinstance(main_post, dict):
            return main_post.get("timestamp", "")
        replies = items.get("replies", [])
        if replies:
            return replies[0].get("timestamp", "")
        return ""

    def convert_post(self, post: Dict[str, Any], post_index: int) -> Optional[str]:
        """
        Convert a single post to Markdown format.

        Args:
            post: Post dictionary
            post_index: Index of the post in the group

        Returns:
            Markdown formatted string or None if should be skipped
        """
        if self.should_skip_post(post):
            return None

        lines = []

        # Title - use shared helper function
        title = get_post_title(post) or "未知标题"
        # Clean up the title
        title = title.replace("[找工就业]", "").replace("[面试经验]", "").replace("[工作信息]", "").replace("[其他]", "").strip()
        title = " ".join(title.split())  # Normalize whitespace

        lines.append(f"## 帖子 {post_index}: {title}")
        lines.append("")

        # Source URL - use shared helper function
        url = get_post_url(post)
        if url:
            lines.append(f"**来源**: {url}")
            lines.append("")

        # Published time
        published_time = self._get_published_time(post)
        if published_time:
            lines.append(f"**发布时间**: {published_time}")
            lines.append("")

        # Build hierarchical structure from all replies
        items = post.get("items", {})
        replies = items.get("replies", [])

        all_replies = []
        main_post = items.get("main_post")
        if main_post and isinstance(main_post, dict):
            all_replies.append(main_post)
        all_replies.extend(replies)

        # Build hierarchy
        hierarchy = build_reply_hierarchy(all_replies)

        # Add main content
        main_content = hierarchy.get('main_content', '')
        if main_content:
            lines.append("### 主楼内容")
            lines.append("")
            lines.append(main_content)
            lines.append("")

        # Process hierarchical replies
        reply_nodes = hierarchy.get('replies', [])
        if reply_nodes:
            # Filter out low-value replies
            valid_replies = [r for r in reply_nodes if not self._is_low_value_reply(r.get("content", ""))]
            if valid_replies:
                lines.append("### 回复讨论")
                lines.append("")
                for reply_node in valid_replies:
                    reply_lines = self._format_nested_reply(reply_node)
                    lines.extend(reply_lines)
                lines.append("")

        return "\n".join(lines)

    def convert_group(self, posts: List[Dict[str, Any]], group_index: int = 1) -> str:
        """
        Convert a group of posts to Markdown format.

        Args:
            posts: List of post dictionaries
            group_index: Index of this group

        Returns:
            Markdown formatted string
        """
        lines = []
        lines.append(f"# 面经帖子组 {group_index}")
        lines.append("")
        lines.append("以下是需要提取面试信息的帖子内容：")
        lines.append("")
        lines.append("---")
        lines.append("")

        valid_post_count = 0
        for i, post in enumerate(posts, 1):
            converted = self.convert_post(post, i)
            if converted:
                valid_post_count += 1
                lines.append(converted)
                lines.append("")
                lines.append("---")
                lines.append("")

        if valid_post_count == 0:
            return ""

        return "\n".join(lines)


class PostGrouper:
    """Groups posts for batch processing."""

    def __init__(self, group_size: int = 3):
        """
        Initialize the grouper.

        Args:
            group_size: Number of posts per group (2-3 recommended)
        """
        self.group_size = group_size

    def group_posts(self, posts: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group posts into batches.

        Args:
            posts: List of all posts

        Returns:
            List of post groups
        """
        return [
            posts[i:i + self.group_size]
            for i in range(0, len(posts), self.group_size)
        ]


if __name__ == "__main__":
    # Test with sample data
    import json

    sample_post = {
        "url": "https://example.com/thread-123",
        "thread_title": "[面试经验] 测试帖子标题",
        "replies": [
            {
                "mainPageContent": "这是主楼内容，包含面试题目的详细描述..."
            },
            {
                "content": "感谢楼主分享，请问这题是60min还是75min？"
            },
            {
                "content": "已加米"
            },
            {
                "content": "60min，我上周刚面完",
                "children": [
                    {"content": "请问有follow up吗？"}
                ]
            }
        ]
    }

    converter = MarkdownConverter()
    result = converter.convert_post(sample_post, 1)
    print(result)
