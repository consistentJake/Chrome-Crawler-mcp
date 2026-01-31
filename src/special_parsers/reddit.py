"""
Reddit Parser
Extracts structured post and comment data from Reddit pages.

Supports:
- Subreddit listing pages (e.g., /r/Pennystock/new/)
- Individual post pages with comments

Uses HTML parsing approach since Reddit's CSP blocks script injection.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import json
import re
from .base import BaseParser


class RedditParser(BaseParser):
    """
    Parser for Reddit pages.

    Supports:
    - Subreddit listing pages (hot, new, top, etc.)
    - Individual post pages with comments
    - Extracts post titles, links, timestamps, authors, scores
    - Extracts comments with author, content, timestamps

    Uses HTML parsing instead of JavaScript execution to avoid CSP issues.
    """

    name = "reddit"
    description = "Extracts posts and comments from Reddit subreddit and post pages"
    version = "1.0.0"

    def parse(self, browser_client) -> Dict[str, Any]:
        """
        Extract posts/comments from current Reddit page using HTML parsing.

        Args:
            browser_client: BrowserIntegration instance

        Returns:
            Structured Reddit data
        """
        # Get current URL and page info
        url = browser_client.get_current_url()
        page_title = browser_client.get_page_title()

        start_time = datetime.now()

        # Get raw HTML content
        html_content = browser_client.get_current_page_html()

        # Determine page type and use appropriate extraction
        is_post_page = '/comments/' in url

        if is_post_page:
            extraction_result = self._parse_post_page_html(html_content)
        else:
            extraction_result = self._parse_subreddit_listing_html(html_content)

        end_time = datetime.now()

        # Build structured output based on page type
        if is_post_page:
            return self._build_post_page_output(
                extraction_result, url, page_title, start_time, end_time
            )
        else:
            return self._build_subreddit_listing_output(
                extraction_result, url, page_title, start_time, end_time
            )

    def _parse_subreddit_listing_html(self, html_content: str) -> Dict[str, Any]:
        """
        Parse HTML to extract posts from subreddit listing pages.
        Reddit uses shreddit-post custom elements with data attributes.

        Args:
            html_content: Raw HTML content

        Returns:
            Dictionary with posts and metadata
        """
        posts = []

        # Extract subreddit from the HTML
        subreddit = ''
        subreddit_match = re.search(r'subreddit-name="([^"]+)"', html_content)
        if subreddit_match:
            subreddit = subreddit_match.group(1)

        # Find all shreddit-post elements using regex
        # Pattern matches the opening tag with all its attributes
        post_pattern = r'<shreddit-post\s+([^>]+)>'
        post_matches = re.finditer(post_pattern, html_content, re.IGNORECASE)

        for idx, match in enumerate(post_matches):
            attrs_str = match.group(1)

            # Extract attributes using regex
            # Use word boundary \b to avoid matching user-id when looking for id
            def get_attr(name: str) -> str:
                # Use negative lookbehind to avoid partial matches (e.g., user-id for id)
                attr_match = re.search(rf'(?<![a-zA-Z-]){name}="([^"]*)"', attrs_str)
                return attr_match.group(1) if attr_match else ''

            post_id = get_attr('id')
            post_title = get_attr('post-title')

            # Skip if no post ID or title (likely an ad or placeholder)
            if not post_id or not post_title:
                continue

            permalink = get_attr('permalink')
            full_url = f'https://www.reddit.com{permalink}' if permalink else ''

            posts.append({
                'id': post_id,
                'title': post_title,
                'url': full_url,
                'permalink': permalink,
                'author': get_attr('author'),
                'created_timestamp': get_attr('created-timestamp'),
                'comment_count': int(get_attr('comment-count') or '0'),
                'score': int(get_attr('score') or '0'),
                'subreddit': get_attr('subreddit-name') or subreddit,
                'post_type': get_attr('post-type'),
                'domain': get_attr('domain'),
                'index': idx
            })

        return {
            'posts': posts,
            'subreddit': subreddit,
            'total_posts': len(posts)
        }

    def _parse_post_page_html(self, html_content: str) -> Dict[str, Any]:
        """
        Parse HTML to extract post content and comments from a post page.

        Args:
            html_content: Raw HTML content

        Returns:
            Dictionary with main post and comments
        """
        main_post = None
        comments = []

        # Extract subreddit
        subreddit = ''
        subreddit_match = re.search(r'subreddit-name="([^"]+)"', html_content)
        if subreddit_match:
            subreddit = subreddit_match.group(1)

        # Extract main post from shreddit-post element
        post_match = re.search(r'<shreddit-post\s+([^>]+)>', html_content, re.IGNORECASE)
        if post_match:
            attrs_str = post_match.group(1)

            def get_attr(name: str) -> str:
                # Use negative lookbehind to avoid partial matches (e.g., user-id for id)
                attr_match = re.search(rf'(?<![a-zA-Z-]){name}="([^"]*)"', attrs_str)
                return attr_match.group(1) if attr_match else ''

            # Try to extract post body content
            # Reddit stores post content in a div with property="schema:articleBody"
            content = ''
            # Find the articleBody div and extract all text from it
            article_body_match = re.search(
                r'property="schema:articleBody"[^>]*>(.*?)</div>\s*</div>',
                html_content, re.DOTALL
            )
            if article_body_match:
                # Strip HTML tags to get plain text
                raw_content = article_body_match.group(1)
                # Remove HTML tags but preserve some structure
                content = re.sub(r'<[^>]+>', ' ', raw_content)
                # Normalize whitespace
                content = re.sub(r'\s+', ' ', content).strip()

            main_post = {
                'id': get_attr('id'),
                'title': get_attr('post-title'),
                'author': get_attr('author'),
                'created_timestamp': get_attr('created-timestamp'),
                'comment_count': int(get_attr('comment-count') or '0'),
                'score': int(get_attr('score') or '0'),
                'subreddit': get_attr('subreddit-name') or subreddit,
                'content': content
            }

        # Extract comments from shreddit-comment elements
        comment_pattern = r'<shreddit-comment\s+([^>]+)>'
        comment_matches = list(re.finditer(comment_pattern, html_content, re.IGNORECASE))

        max_comments = 5  # Only get top 5 comments as requested
        for idx, match in enumerate(comment_matches[:max_comments]):
            attrs_str = match.group(1)

            def get_attr(name: str) -> str:
                # Use negative lookbehind to avoid partial matches
                attr_match = re.search(rf'(?<![a-zA-Z-]){name}="([^"]*)"', attrs_str)
                return attr_match.group(1) if attr_match else ''

            author = get_attr('author')
            comment_id = get_attr('thingid') or get_attr('id')

            # Skip if no author (likely deleted)
            if not author:
                continue

            # Try to find comment content
            # Reddit stores comment text in div with id="{thingid}-comment-rtjson-content"
            content = ''
            if comment_id:
                # Look for the comment content div
                content_pattern = rf'id="{re.escape(comment_id)}-comment-rtjson-content"[^>]*>(.*?)</div>\s*</div>'
                content_match = re.search(content_pattern, html_content, re.DOTALL)
                if content_match:
                    raw_content = content_match.group(1)
                    # Strip HTML tags
                    content = re.sub(r'<[^>]+>', ' ', raw_content)
                    # Normalize whitespace
                    content = re.sub(r'\s+', ' ', content).strip()

            comments.append({
                'id': comment_id,
                'author': author,
                'content': content,
                'score': int(get_attr('score') or '0'),
                'depth': int(get_attr('depth') or '0'),
                'index': idx
            })

        return {
            'main_post': main_post,
            'comments': comments,
            'subreddit': subreddit,
            'total_comments': len(comment_matches)
        }

    def _build_subreddit_listing_output(
        self, extraction_result: Dict, url: str, page_title: str,
        start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Build output for subreddit listing pages"""
        posts = extraction_result.get('posts', [])
        subreddit = extraction_result.get('subreddit', '')

        return {
            "parser": self.name,
            "parser_version": self.version,
            "page_type": "subreddit_listing",
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "item_count": len(posts),
            "items": posts,
            "metadata": {
                "page_title": page_title,
                "subreddit": subreddit,
                "extraction_time_ms": int((end_time - start_time).total_seconds() * 1000),
                "total_posts_found": extraction_result.get('total_posts', 0)
            }
        }

    def _build_post_page_output(
        self, extraction_result: Dict, url: str, page_title: str,
        start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Build output for individual post pages"""
        main_post = extraction_result.get('main_post', {})
        comments = extraction_result.get('comments', [])

        return {
            "parser": self.name,
            "parser_version": self.version,
            "page_type": "post_detail",
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "item_count": len(comments) + (1 if main_post else 0),
            "items": {
                "main_post": main_post,
                "comments": comments
            },
            "metadata": {
                "page_title": page_title,
                "extraction_time_ms": int((end_time - start_time).total_seconds() * 1000),
                "total_comments_found": extraction_result.get('total_comments', 0),
                "subreddit": extraction_result.get('subreddit', '')
            }
        }

    def get_extraction_js(self) -> str:
        """
        Not used - HTML parsing is used instead of JavaScript execution.
        Required by base class interface.
        """
        return ""

    def validate_page(self, browser_client) -> bool:
        """Check if current page is a valid Reddit page"""
        url = browser_client.get_current_url()
        return 'reddit.com' in url
