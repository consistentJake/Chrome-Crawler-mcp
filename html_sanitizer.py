"""
HTML Sanitization Module for Web Extraction
Inspired by Feilian's approach, optimized for Claude Code integration
"""

import re
import html
from typing import Dict, List, Set, Optional, Tuple
from bs4 import BeautifulSoup, Comment, Tag, NavigableString
from urllib.parse import unquote
import hashlib


class HTMLSanitizer:
    """
    HTML sanitization tool optimized for AI-driven web extraction.
    
    Features:
    - Token-efficient sanitization for LLM context limits
    - Structure-aware pattern preservation
    - Interactive element identification for Playwright MCP
    - Security-aware content filtering
    """
    
    # HTML elements to completely remove
    REMOVE_ELEMENTS = {
        'script', 'style', 'noscript', 'head', 'title', 'meta', 'link',
        'svg', 'path', 'iframe', 'object', 'embed', 'applet',
        'audio', 'video', 'source', 'track', 'canvas',
        'template', 'slot', 'shadow'
    }
    
    # Interactive elements to preserve structure but simplify
    INTERACTIVE_ELEMENTS = {
        'a', 'button', 'input', 'select', 'textarea', 'form',
        'label', 'fieldset', 'legend', 'details', 'summary'
    }
    
    # Content elements worth preserving
    CONTENT_ELEMENTS = {
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'div', 'span', 'article', 'section',
        'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th',
        'blockquote', 'pre', 'code', 'em', 'strong', 'b', 'i'
    }
    
    # Attributes to preserve
    PRESERVE_ATTRIBUTES = {
        'href', 'src', 'alt', 'title', 'class', 'id',
        'type', 'name', 'value', 'placeholder',
        'role', 'aria-label', 'data-testid'
    }
    
    def __init__(self, max_tokens: int = 8000, preserve_structure: bool = True):
        """
        Initialize sanitizer.
        
        Args:
            max_tokens: Approximate maximum tokens for output
            preserve_structure: Whether to maintain HTML structure
        """
        self.max_tokens = max_tokens
        self.preserve_structure = preserve_structure
        self.element_registry: List[Dict] = []
        self._element_counter = 0
    
    def sanitize(self, html_content: str, extraction_mode: str = 'links') -> Dict[str, any]:
        """
        Sanitize HTML content for AI processing.
        
        Args:
            html_content: Raw HTML content
            extraction_mode: Type of extraction ('links', 'forms', 'content', 'all')
            
        Returns:
            Dict containing sanitized HTML, element registry, and metadata
        """
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        self._remove_unwanted_elements(soup)
        
        # Remove comments and clean up
        self._remove_comments(soup)
        
        # Sanitize attributes
        self._sanitize_attributes(soup)
        
        # Build element registry for interactive elements
        self._build_element_registry(soup, extraction_mode)
        
        # Apply token limits
        sanitized_soup = self._apply_token_limits(soup)
        
        # Generate different output formats
        return {
            'sanitized_html': str(sanitized_soup),
            'indexed_text': self._generate_indexed_text(),
            'element_registry': self.element_registry,
            'pattern_hints': self._extract_pattern_hints(),
            'statistics': self._get_statistics()
        }
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup) -> None:
        """Remove script, style, and other unwanted elements"""
        for tag_name in self.REMOVE_ELEMENTS:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # Remove hidden elements
        for tag in soup.find_all(style=re.compile(r'display\s*:\s*none', re.I)):
            tag.decompose()
    
    def _remove_comments(self, soup: BeautifulSoup) -> None:
        """Remove HTML comments"""
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
    
    def _sanitize_attributes(self, soup: BeautifulSoup) -> None:
        """Keep only essential attributes"""
        for tag in soup.find_all():
            if hasattr(tag, 'attrs'):
                # Keep only essential attributes
                attrs_to_keep = {}
                for attr, value in tag.attrs.items():
                    if attr in self.PRESERVE_ATTRIBUTES:
                        # Clean href attributes
                        if attr == 'href' and value:
                            value = self._clean_href(value)
                        if value:  # Only keep non-empty values
                            attrs_to_keep[attr] = value
                
                tag.attrs = attrs_to_keep
    
    def _clean_href(self, href: str) -> Optional[str]:
        """Clean and validate href attributes"""
        if not href:
            return None
        
        # Remove javascript: and other dangerous protocols
        if href.lower().startswith(('javascript:', 'data:', 'vbscript:')):
            return None
        
        # URL decode
        try:
            href = unquote(href)
        except:
            pass
        
        return href.strip()
    
    def _build_element_registry(self, soup: BeautifulSoup, extraction_mode: str) -> None:
        """Build registry of interactable elements only"""
        self.element_registry = []
        self._element_counter = 0

        # Find all potential interactable elements
        # We check all elements and filter by interactability
        for tag in soup.find_all(True):  # Find all tags
            if self._is_visible_element(tag) and self._is_interactable_element(tag):
                element_info = self._create_element_info(tag)
                if element_info:
                    self.element_registry.append(element_info)
    
    def _is_visible_element(self, tag: Tag) -> bool:
        """Check if element is likely visible"""
        # Check for hidden attribute
        if tag.get('hidden'):
            return False

        # Check for hidden attributes
        style = tag.get('style', '')
        if re.search(r'display\s*:\s*none|visibility\s*:\s*hidden', style, re.I):
            return False

        # Check for hidden class patterns
        class_str = ' '.join(tag.get('class', []))
        if re.search(r'hidden|invisible|sr-only|visually-hidden', class_str, re.I):
            return False

        return True

    def _is_interactable_element(self, tag: Tag) -> bool:
        """
        Check if element is interactable and should get a web_agent_id.

        Criteria:
        1. Links: <a> with href (excluding javascript:, #, mailto:)
        2. Buttons: <button>, <input type="submit/button/reset">
        3. Form Inputs: <input>, <textarea>, <select>
        4. Custom Interactive: Elements with onclick, role="button/link", tabindex >= 0
        """
        tag_name = tag.name.lower()

        # 1. Links with valid href
        if tag_name == 'a':
            href = tag.get('href', '').strip()
            if href and not href.startswith(('javascript:', 'mailto:', '#')):
                return True
            return False

        # 2. Buttons
        if tag_name == 'button':
            return True

        if tag_name == 'input':
            input_type = tag.get('type', 'text').lower()
            # Button-like inputs
            if input_type in ['submit', 'button', 'reset']:
                return True
            # Form inputs (text, password, email, etc.)
            if input_type in ['text', 'password', 'email', 'search', 'tel', 'url',
                            'number', 'date', 'time', 'datetime-local', 'month',
                            'week', 'color', 'range', 'file', 'checkbox', 'radio']:
                return True
            return False

        # 3. Form elements
        if tag_name in ['textarea', 'select']:
            return True

        # 4. Custom interactive elements
        # Has onclick handler
        if tag.get('onclick'):
            return True

        # Has button or link role
        role = tag.get('role', '').lower()
        if role in ['button', 'link']:
            return True

        # Has positive tabindex (focusable)
        tabindex = tag.get('tabindex')
        if tabindex is not None:
            try:
                if int(tabindex) >= 0:
                    return True
            except ValueError:
                pass

        return False
    
    def _create_element_info(self, tag: Tag) -> Optional[Dict]:
        """Create element information for registry"""
        # Generate unique web agent ID
        web_agent_id = f"wa-{self._element_counter}"
        self._element_counter += 1

        # Inject data-web-agent-id for later targeting
        tag['data-web-agent-id'] = web_agent_id

        # Extract text content
        text = self._get_clean_text(tag)

        # Build locator information
        locators = self._build_locators(tag, web_agent_id)

        element_info = {
            'index': len(self.element_registry),
            'web_agent_id': web_agent_id,
            'tag': tag.name,
            'text': text[:100],  # Truncate long text
            'attributes': {
                attr: tag.get(attr) for attr in ['href', 'class', 'id', 'type', 'name', 'placeholder', 'value']
                if tag.get(attr)
            },
            'locators': locators
        }

        return element_info
    
    def _get_clean_text(self, tag: Tag) -> str:
        """Extract and clean text content"""
        text = tag.get_text(strip=True)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    def _build_locators(self, tag: Tag, web_agent_id: str) -> Dict[str, str]:
        """Build multiple locator strategies for the element"""
        locators = {
            'data_id': f'[data-web-agent-id="{web_agent_id}"]',
        }

        # Add other locator strategies
        if tag.get('id'):
            locators['id'] = f'#{tag["id"]}'

        if tag.get('class'):
            classes = ' '.join(tag['class'])
            locators['class'] = f'.{".".join(tag["class"][:2])}'  # Use first 2 classes

        # Generate XPath
        locators['xpath'] = self._generate_xpath(tag)

        # For links, add href-based locator
        if tag.name == 'a' and tag.get('href'):
            locators['href'] = f'a[href="{tag["href"]}"]'

        # For inputs, add name-based locator
        if tag.name == 'input' and tag.get('name'):
            locators['name'] = f'input[name="{tag["name"]}"]'

        return locators
    
    def _generate_xpath(self, tag: Tag) -> str:
        """Generate XPath for element"""
        path_parts = []
        current = tag
        
        while current and current.parent and current.name != 'html':
            siblings = [sibling for sibling in current.parent.children 
                       if hasattr(sibling, 'name') and sibling.name == current.name]
            
            if len(siblings) > 1:
                index = siblings.index(current) + 1
                path_parts.append(f'{current.name}[{index}]')
            else:
                path_parts.append(current.name)
            
            current = current.parent
        
        return '//' + '/'.join(reversed(path_parts)) if path_parts else f'//{tag.name}'
    
    def _apply_token_limits(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Apply token limits by intelligently pruning content"""
        current_content = str(soup)
        estimated_tokens = len(current_content) // 4  # Rough estimation
        
        if estimated_tokens <= self.max_tokens:
            return soup
        
        # Remove excessive whitespace and empty elements
        self._clean_whitespace(soup)
        
        # If still too long, truncate while preserving structure
        if len(str(soup)) // 4 > self.max_tokens:
            soup = self._truncate_preserving_structure(soup)
        
        return soup
    
    def _clean_whitespace(self, soup: BeautifulSoup) -> None:
        """Clean up excessive whitespace"""
        for text_node in soup.find_all(string=True):
            if isinstance(text_node, NavigableString):
                cleaned = ' '.join(text_node.split())
                text_node.replace_with(cleaned)
    
    def _truncate_preserving_structure(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Truncate content while preserving important structure"""
        # Keep elements with data-web-agent-id (our registered elements)
        important_elements = soup.find_all(attrs={'data-web-agent-id': True})

        # Create minimal soup with just important elements
        new_soup = BeautifulSoup('<html><body></body></html>', 'html.parser')
        body = new_soup.find('body')

        for element in important_elements:
            # Clone element and its essential parent structure
            # Filter out 'name' from attrs to avoid conflict with tag name
            attrs = {k: v for k, v in element.attrs.items() if k != 'name'}
            clone = new_soup.new_tag(element.name, **attrs)
            clone.string = element.get_text()[:50]  # Truncate text
            body.append(clone)

        return new_soup
    
    def _generate_indexed_text(self) -> str:
        """Generate indexed text format for LLM consumption with web_agent_id"""
        lines = []
        for element in self.element_registry:
            attrs = []
            # Add web_agent_id
            attrs.append(f'id="{element["web_agent_id"]}"')

            if element['attributes'].get('href'):
                attrs.append(f'href="{element["attributes"]["href"]}"')
            if element['attributes'].get('type'):
                attrs.append(f'type="{element["attributes"]["type"]}"')
            if element['attributes'].get('placeholder'):
                attrs.append(f'placeholder="{element["attributes"]["placeholder"]}"')

            attr_str = ' ' + ' '.join(attrs) if attrs else ''
            text = element['text'][:50] if element['text'] else ''

            line = f"[{element['index']}] <{element['tag']}{attr_str}>{text}</{element['tag']}>"
            lines.append(line)

        return '\n'.join(lines)
    
    def _extract_pattern_hints(self) -> Dict[str, List[str]]:
        """Extract common patterns for Claude Code to analyze"""
        patterns = {
            'link_patterns': [],
            'class_patterns': [],
            'structure_patterns': []
        }
        
        # Analyze href patterns
        hrefs = [elem['attributes'].get('href') for elem in self.element_registry 
                if elem.get('tag') == 'a' and elem['attributes'].get('href')]
        
        patterns['link_patterns'] = list(set(hrefs))[:10]  # Sample of unique patterns
        
        # Analyze class patterns
        classes = []
        for elem in self.element_registry:
            class_attr = elem['attributes'].get('class')
            if class_attr:
                if isinstance(class_attr, list):
                    classes.extend(class_attr)
                else:
                    classes.extend(class_attr.split())
        
        # Most common classes
        class_counts = {}
        for cls in classes:
            class_counts[cls] = class_counts.get(cls, 0) + 1
        
        patterns['class_patterns'] = sorted(class_counts.keys(), 
                                          key=lambda x: class_counts[x], 
                                          reverse=True)[:5]
        
        return patterns
    
    def _get_statistics(self) -> Dict[str, any]:
        """Get sanitization statistics"""
        return {
            'total_elements': len(self.element_registry),
            'element_types': {
                elem['tag']: sum(1 for e in self.element_registry if e['tag'] == elem['tag'])
                for elem in self.element_registry
            },
            'estimated_tokens': len(str(self._generate_indexed_text())) // 4
        }


# Example usage function
def extract_post_links(html_content: str) -> List[Dict[str, str]]:
    """
    Extract post links from forum HTML using sanitization + pattern recognition.
    
    Args:
        html_content: Raw HTML from forum page
        
    Returns:
        List of post links with titles and URLs
    """
    # Sanitize HTML focusing on links
    sanitizer = HTMLSanitizer(max_tokens=4000)
    result = sanitizer.sanitize(html_content, extraction_mode='links')
    
    # Extract potential post links based on common forum patterns
    post_links = []
    
    for element in result['element_registry']:
        if element['tag'] == 'a' and element['attributes'].get('href'):
            href = element['attributes']['href']
            text = element['text'].strip()
            
            # Common forum post patterns
            post_patterns = [
                r'thread-\d+-\d+-\d+\.html',  # Discuz style: thread-{id}-1-1.html
                r'viewtopic\.php\?.*t=\d+',    # phpBB style
                r'topic/\d+',                  # Modern forum style
                r'threads/[^/]+\.\d+',         # XenForo style
            ]
            
            for pattern in post_patterns:
                if re.search(pattern, href, re.I):
                    post_links.append({
                        'title': text,
                        'url': href,
                        'web_agent_id': element['web_agent_id'],
                        'xpath': element['locators']['xpath']
                    })
                    break
    
    return post_links


if __name__ == "__main__":
    # Test with the provided page
    import sys
    
    if len(sys.argv) > 1:
        html_file = sys.argv[1]
    else:
        html_file = '/home/zhenkai/personal/Projects/WebAgent/test/page.html'
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except UnicodeDecodeError:
        with open(html_file, 'r', encoding='gbk') as f:
            html_content = f.read()
    
    # Test sanitization
    sanitizer = HTMLSanitizer(max_tokens=6000)
    result = sanitizer.sanitize(html_content, extraction_mode='links')
    
    print("=== Sanitization Results ===")
    print(f"Total elements found: {result['statistics']['total_elements']}")
    print(f"Estimated tokens: {result['statistics']['estimated_tokens']}")
    print(f"Element types: {result['statistics']['element_types']}")
    
    print("\n=== Pattern Hints ===")
    for pattern_type, patterns in result['pattern_hints'].items():
        print(f"{pattern_type}: {patterns}")
    
    print("\n=== Post Link Extraction ===")
    post_links = extract_post_links(html_content)
    print(f"Found {len(post_links)} potential post links:")
    for i, link in enumerate(post_links[:10]):  # Show first 10
        print(f"{i+1}. {link['title'][:60]} -> {link['url']}")
    
    print("\n=== Indexed Text Sample ===")
    print(result['indexed_text'][:1000] + "..." if len(result['indexed_text']) > 1000 else result['indexed_text'])