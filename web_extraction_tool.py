"""
Web Extraction Tool for Claude Code Integration
Combines HTML sanitization with Playwright MCP for intelligent web automation
"""

import json
import time
from typing import Dict, List, Optional, Tuple
from html_sanitizer import HTMLSanitizer, extract_post_links
from helper.PlaywrightMcpClient import MCPPlaywrightClient


class WebExtractionTool:
    """
    Intelligent web extraction tool that combines:
    1. HTML sanitization for efficient LLM processing
    2. Pattern recognition for element identification
    3. Playwright MCP integration for reliable automation
    """
    
    def __init__(self, max_tokens: int = 6000):
        """
        Initialize the web extraction tool.
        
        Args:
            max_tokens: Maximum tokens for sanitized content
        """
        self.sanitizer = HTMLSanitizer(max_tokens=max_tokens)
        self.playwright_client = None
        self.current_page_data = None
    
    def connect_playwright(self, **kwargs) -> bool:
        """
        Connect to Playwright MCP server.
        
        Returns:
            True if connection successful
        """
        try:
            self.playwright_client = MCPPlaywrightClient(**kwargs)
            print("✅ Connected to Playwright MCP server")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Playwright: {e}")
            return False
    
    def navigate_and_analyze(self, url: str, extraction_mode: str = 'links') -> Dict:
        """
        Navigate to URL and analyze page content.
        
        Args:
            url: URL to navigate to
            extraction_mode: What to extract ('links', 'forms', 'content', 'all')
            
        Returns:
            Dict with sanitized content and analysis
        """
        if not self.playwright_client:
            raise RuntimeError("Playwright client not connected. Call connect_playwright() first.")
        
        # Navigate to URL
        nav_result = self.playwright_client.browser_navigate(url)
        if nav_result.get('status') != 'success':
            raise RuntimeError(f"Navigation failed: {nav_result}")
        
        # Get page snapshot
        snapshot_result = self.playwright_client.browser_snapshot()
        if snapshot_result.get('status') != 'success':
            raise RuntimeError(f"Snapshot failed: {snapshot_result}")
        
        # Extract HTML content from snapshot
        html_content = snapshot_result.get('result', '')
        
        # Sanitize and analyze content
        sanitized_result = self.sanitizer.sanitize(html_content, extraction_mode)
        
        # Store current page data
        self.current_page_data = {
            'url': url,
            'sanitized_result': sanitized_result,
            'extraction_mode': extraction_mode
        }
        
        return {
            'url': url,
            'success': True,
            'sanitized_html': sanitized_result['sanitized_html'][:2000] + '...' if len(sanitized_result['sanitized_html']) > 2000 else sanitized_result['sanitized_html'],
            'indexed_text': sanitized_result['indexed_text'],
            'element_count': len(sanitized_result['element_registry']),
            'patterns': sanitized_result['pattern_hints'],
            'statistics': sanitized_result['statistics']
        }
    
    def extract_posts_with_patterns(self) -> List[Dict]:
        """
        Extract forum posts using pattern recognition.
        Specifically designed for forum pages with thread links.
        
        Returns:
            List of detected post information
        """
        if not self.current_page_data:
            raise RuntimeError("No page data available. Call navigate_and_analyze() first.")
        
        # Get current HTML from Playwright
        snapshot_result = self.playwright_client.browser_snapshot()
        html_content = snapshot_result.get('result', '')
        
        # Use our pattern-based post extraction
        posts = extract_post_links(html_content)
        
        # Add Playwright interaction capability to each post
        enhanced_posts = []
        for post in posts:
            enhanced_posts.append({
                'title': post['title'],
                'url': post['url'],
                'element_id': post['element_id'],
                'xpath': post['xpath'],
                'clickable': True,  # Can be clicked via Playwright
                'playwright_locator': f"[data-element-id='{post['element_id']}']"
            })
        
        return enhanced_posts
    
    def click_post_by_index(self, index: int) -> Dict:
        """
        Click a post link by its index in the extracted posts list.
        
        Args:
            index: Index of the post to click
            
        Returns:
            Result of the click action
        """
        if not self.playwright_client:
            raise RuntimeError("Playwright client not connected.")
        
        posts = self.extract_posts_with_patterns()
        if index >= len(posts):
            return {'status': 'error', 'message': f'Index {index} out of range. Found {len(posts)} posts.'}
        
        post = posts[index]
        
        # Try clicking using our injected data-element-id
        click_result = self.playwright_client.browser_click(
            element=f"Post link: {post['title'][:50]}",
            ref=post['playwright_locator']
        )
        
        if click_result.get('status') == 'success':
            return {
                'status': 'success',
                'message': f"Clicked post: {post['title']}",
                'url': post['url']
            }
        else:
            # Fallback: try clicking by href
            href_locator = f"a[href='{post['url']}']"
            click_result = self.playwright_client.browser_click(
                element=f"Post link by href: {post['title'][:50]}",
                ref=href_locator
            )
            return click_result
    
    def get_claude_analysis_prompt(self) -> str:
        """
        Generate a prompt for Claude Code to analyze the current page and identify patterns.
        
        Returns:
            Formatted prompt string
        """
        if not self.current_page_data:
            return "No page data available. Please call navigate_and_analyze() first."
        
        result = self.current_page_data['sanitized_result']
        
        prompt = f"""I've sanitized a web page and found {len(result['element_registry'])} interactive elements. 

The page contains these types of elements:
{json.dumps(result['statistics']['element_types'], indent=2)}

Here are the patterns I detected:
{json.dumps(result['pattern_hints'], indent=2)}

Indexed elements (first 20):
{chr(10).join(result['indexed_text'].split(chr(10))[:20])}

Based on this sanitized content, please help me:
1. Identify the pattern for post/article links
2. Suggest XPath or CSS selectors to reliably find all posts
3. Recommend the best approach to extract all post titles and links

The goal is to create reliable locators that won't miss any posts and can be used with Playwright for automation."""
        
        return prompt
    
    def verify_pattern_completeness(self, suggested_selector: str) -> Dict:
        """
        Verify that a suggested CSS/XPath selector captures all intended elements.
        
        Args:
            suggested_selector: CSS selector or XPath to test
            
        Returns:
            Dict with verification results
        """
        if not self.playwright_client:
            raise RuntimeError("Playwright client not connected.")
        
        # Use Playwright to count elements matching the selector
        count_script = f"""
        () => {{
            const selector = "{suggested_selector}";
            if (selector.startsWith('//')) {{
                // XPath selector
                const result = document.evaluate(
                    selector, 
                    document, 
                    null, 
                    XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, 
                    null
                );
                return result.snapshotLength;
            }} else {{
                // CSS selector
                return document.querySelectorAll(selector).length;
            }}
        }}
        """
        
        eval_result = self.playwright_client.browser_evaluate(count_script)
        
        if eval_result.get('status') == 'success':
            count = eval_result.get('result', 0)
            
            # Compare with our detected patterns
            our_post_count = len([elem for elem in self.current_page_data['sanitized_result']['element_registry'] 
                                if elem['tag'] == 'a' and 'thread-' in elem['attributes'].get('href', '')])
            
            return {
                'status': 'success',
                'selector': suggested_selector,
                'matched_count': count,
                'our_detected_count': our_post_count,
                'completeness_ratio': count / max(our_post_count, 1),
                'recommendation': 'good' if abs(count - our_post_count) <= 2 else 'needs_refinement'
            }
        else:
            return {'status': 'error', 'message': f'Failed to evaluate selector: {eval_result}'}
    
    def extract_with_custom_selector(self, css_selector: str) -> List[Dict]:
        """
        Extract elements using a custom CSS selector.
        
        Args:
            css_selector: CSS selector to find elements
            
        Returns:
            List of extracted element data
        """
        if not self.playwright_client:
            raise RuntimeError("Playwright client not connected.")
        
        extraction_script = f"""
        () => {{
            const elements = document.querySelectorAll("{css_selector}");
            return Array.from(elements).map((el, index) => ({{
                index: index,
                text: el.textContent.trim(),
                href: el.href || el.getAttribute('href'),
                tag: el.tagName.toLowerCase(),
                id: el.id,
                classes: el.className
            }}));
        }}
        """
        
        eval_result = self.playwright_client.browser_evaluate(extraction_script)
        
        if eval_result.get('status') == 'success':
            return eval_result.get('result', [])
        else:
            raise RuntimeError(f'Failed to extract elements: {eval_result}')
    
    def close(self):
        """Clean up connections"""
        if self.playwright_client:
            self.playwright_client.close()
            print("🔌 Disconnected from Playwright")


def demo_usage():
    """Demonstrate the tool usage"""
    # Initialize tool
    tool = WebExtractionTool(max_tokens=8000)
    
    # Connect to Playwright
    if not tool.connect_playwright():
        print("❌ Failed to connect to Playwright. Make sure Playwright MCP server is running.")
        return
    
    try:
        # Test with the local test file (convert to file:// URL)
        import os
        test_file = os.path.abspath('test/page.html')
        file_url = f'file://{test_file}'
        
        print(f"\n📖 Analyzing page: {file_url}")
        
        # Analyze the page
        analysis = tool.navigate_and_analyze(file_url, extraction_mode='links')
        
        print(f"\n📊 Analysis Results:")
        print(f"   • Found {analysis['element_count']} interactive elements")
        print(f"   • Estimated tokens: {analysis['statistics']['estimated_tokens']}")
        print(f"   • Element types: {analysis['statistics']['element_types']}")
        
        # Extract posts using pattern recognition
        posts = tool.extract_posts_with_patterns()
        print(f"\n🔗 Found {len(posts)} forum posts:")
        for i, post in enumerate(posts[:5]):  # Show first 5
            print(f"   {i+1}. {post['title'][:60]} -> {post['url']}")
        
        # Generate prompt for Claude Code
        claude_prompt = tool.get_claude_analysis_prompt()
        print(f"\n🤖 Claude Code Analysis Prompt:")
        print(claude_prompt[:500] + "..." if len(claude_prompt) > 500 else claude_prompt)
        
        # Test a selector
        test_selector = "a[href*='thread-']"
        verification = tool.verify_pattern_completeness(test_selector)
        print(f"\n🔍 Selector Verification for '{test_selector}':")
        print(f"   • Matched elements: {verification.get('matched_count', 0)}")
        print(f"   • Our detected: {verification.get('our_detected_count', 0)}")
        print(f"   • Completeness: {verification.get('completeness_ratio', 0):.1%}")
        print(f"   • Recommendation: {verification.get('recommendation', 'unknown')}")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
    
    finally:
        tool.close()


if __name__ == "__main__":
    demo_usage()