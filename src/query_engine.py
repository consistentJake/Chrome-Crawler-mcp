"""
Query Engine for Web Extraction MCP
Natural language and structured querying of extracted elements
"""

import re
from typing import Dict, List, Optional


class QueryEngine:
    """Natural language and structured querying of extracted elements"""

    def __init__(self):
        """Initialize query engine"""
        pass

    def query_elements(
        self,
        elements: List[Dict],
        query: Optional[str] = None,
        filters: Optional[Dict] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Query elements using natural language or structured filters.

        Args:
            elements: List of element dictionaries
            query: Natural language query (e.g., "Find all forum post links")
            filters: Structured filters (tag, href_pattern, text_contains, etc.)
            limit: Maximum number of results to return

        Returns:
            List of matching elements
        """
        matches = elements

        # Apply structured filters first
        if filters:
            matches = self._apply_filters(matches, filters)

        # Apply natural language query
        if query:
            matches = self._apply_natural_language_query(matches, query)

        # Apply limit
        if limit is not None:
            matches = matches[:limit]

        return matches

    def _apply_filters(self, elements: List[Dict], filters: Dict) -> List[Dict]:
        """
        Apply structured filters to elements.

        Supported filters:
        - tag: Element tag name
        - href_pattern: Pattern for href attribute
        - text_contains: Text content contains string
        - text_matches: Text content matches regex
        - class_contains: Class attribute contains string
        - id_equals: ID attribute equals string
        - attribute_exists: Check if attribute exists
        """
        matches = elements

        # Filter by tag
        if "tag" in filters:
            tag = filters["tag"]
            matches = [e for e in matches if e.get("tag") == tag]

        # Filter by href pattern
        if "href_pattern" in filters:
            pattern = filters["href_pattern"]
            matches = [
                e for e in matches
                if self._match_pattern(e.get("attributes", {}).get("href", ""), pattern)
            ]

        # Filter by text contains
        if "text_contains" in filters:
            text = filters["text_contains"].lower()
            matches = [
                e for e in matches
                if text in e.get("text", "").lower()
            ]

        # Filter by text matches regex
        if "text_matches" in filters:
            pattern = filters["text_matches"]
            regex = re.compile(pattern, re.IGNORECASE)
            matches = [
                e for e in matches
                if regex.search(e.get("text", ""))
            ]

        # Filter by class contains
        if "class_contains" in filters:
            class_text = filters["class_contains"]
            matches = [
                e for e in matches
                if self._class_contains(e.get("attributes", {}).get("class", []), class_text)
            ]

        # Filter by ID equals
        if "id_equals" in filters:
            id_value = filters["id_equals"]
            matches = [
                e for e in matches
                if e.get("attributes", {}).get("id") == id_value
            ]

        # Filter by attribute exists
        if "attribute_exists" in filters:
            attr = filters["attribute_exists"]
            matches = [
                e for e in matches
                if attr in e.get("attributes", {})
            ]

        # Filter by index range
        if "index_min" in filters:
            min_idx = filters["index_min"]
            matches = [e for e in matches if e.get("index", 0) >= min_idx]

        if "index_max" in filters:
            max_idx = filters["index_max"]
            matches = [e for e in matches if e.get("index", 0) <= max_idx]

        return matches

    def _apply_natural_language_query(
        self,
        elements: List[Dict],
        query: str
    ) -> List[Dict]:
        """
        Apply natural language query to filter elements.

        Supports queries like:
        - "Find all forum post links"
        - "Get the next page button"
        - "Find login button"
        - "Get all product links"
        """
        query_lower = query.lower()

        # Extract intent and keywords
        intent = self._extract_intent(query_lower)
        keywords = self._extract_keywords(query_lower)

        # Apply intent-based filtering
        if intent == "navigation":
            # Look for navigation-related elements
            nav_keywords = ["next", "previous", "prev", "page", "more", "load"]
            elements = [
                e for e in elements
                if any(kw in e.get("text", "").lower() for kw in nav_keywords)
                or any(kw in e.get("attributes", {}).get("href", "").lower() for kw in nav_keywords)
            ]

        elif intent == "forum_posts":
            # Look for forum post patterns
            elements = [
                e for e in elements
                if e.get("tag") == "a"
                and self._is_forum_post_link(e)
            ]

        elif intent == "products":
            # Look for product-related elements
            product_keywords = ["product", "item", "buy", "price", "cart"]
            elements = [
                e for e in elements
                if any(kw in e.get("text", "").lower() for kw in product_keywords)
                or any(kw in str(e.get("attributes", {}).get("class", [])).lower() for kw in product_keywords)
            ]

        elif intent == "form_controls":
            # Look for form controls
            form_tags = ["input", "button", "select", "textarea"]
            elements = [e for e in elements if e.get("tag") in form_tags]

        # Filter by keywords if no specific intent matched
        if keywords and intent == "generic":
            elements = [
                e for e in elements
                if any(kw in e.get("text", "").lower() for kw in keywords)
                or any(kw in str(e.get("attributes", {})).lower() for kw in keywords)
            ]

        return elements

    def _extract_intent(self, query: str) -> str:
        """Extract intent from natural language query"""
        if any(word in query for word in ["next", "previous", "pagination", "page"]):
            return "navigation"
        elif any(word in query for word in ["forum", "post", "thread", "topic"]):
            return "forum_posts"
        elif any(word in query for word in ["product", "item", "shop", "buy"]):
            return "products"
        elif any(word in query for word in ["button", "input", "form", "submit", "login"]):
            return "form_controls"
        else:
            return "generic"

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from natural language query"""
        # Remove common words
        stop_words = {
            "find", "get", "all", "the", "a", "an", "is", "are", "for",
            "with", "that", "this", "from", "to", "in", "on", "at"
        }

        words = re.findall(r'\w+', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords

    def _match_pattern(self, value: str, pattern: str) -> bool:
        """
        Match value against pattern.

        Supports:
        - Wildcards: * (any characters)
        - Regex: starts with 'regex:'
        - Exact match: plain string
        """
        if not value:
            return False

        # Regex pattern
        if pattern.startswith("regex:"):
            regex_pattern = pattern[6:]
            return bool(re.search(regex_pattern, value, re.IGNORECASE))

        # Wildcard pattern
        if "*" in pattern:
            regex_pattern = pattern.replace("*", ".*")
            return bool(re.match(f"^{regex_pattern}$", value, re.IGNORECASE))

        # Exact match (case-insensitive)
        return value.lower() == pattern.lower()

    def _class_contains(self, class_attr, target: str) -> bool:
        """Check if class attribute contains target class"""
        if isinstance(class_attr, list):
            return any(target.lower() in c.lower() for c in class_attr)
        elif isinstance(class_attr, str):
            return target.lower() in class_attr.lower()
        return False

    def _is_forum_post_link(self, element: Dict) -> bool:
        """Check if element is likely a forum post link"""
        href = element.get("attributes", {}).get("href", "")

        # Common forum post patterns
        post_patterns = [
            r'thread-\d+-\d+-\d+\.html',  # Discuz: thread-{id}-1-1.html
            r'viewtopic\.php\?.*t=\d+',    # phpBB
            r'topic/\d+',                  # Modern forums
            r'threads/[^/]+\.\d+',         # XenForo
            r'discussion/\d+',             # Vanilla
            r't/[^/]+/\d+',                # Discourse
        ]

        return any(re.search(pattern, href, re.IGNORECASE) for pattern in post_patterns)

    def find_by_text(
        self,
        elements: List[Dict],
        text: str,
        exact: bool = False
    ) -> List[Dict]:
        """
        Find elements by text content.

        Args:
            elements: List of elements
            text: Text to search for
            exact: Whether to match exactly

        Returns:
            Matching elements
        """
        if exact:
            return [e for e in elements if e.get("text", "").strip() == text.strip()]
        else:
            text_lower = text.lower()
            return [e for e in elements if text_lower in e.get("text", "").lower()]

    def find_by_locator(
        self,
        elements: List[Dict],
        locator_type: str,
        locator_value: str
    ) -> List[Dict]:
        """
        Find elements by locator.

        Args:
            elements: List of elements
            locator_type: Type of locator (data_id, xpath, class, href, id)
            locator_value: Locator value

        Returns:
            Matching elements
        """
        matches = []
        for element in elements:
            locators = element.get("locators", {})
            if locators.get(locator_type) == locator_value:
                matches.append(element)

        return matches


if __name__ == "__main__":
    # Test query engine
    print("Testing Query Engine...")

    # Sample elements
    elements = [
        {
            "index": 0,
            "tag": "a",
            "text": "How to use Playwright MCP",
            "attributes": {"href": "thread-12345-1-1.html", "class": ["post-link"]},
            "locators": {"data_id": "[data-element-id='elem-0']"}
        },
        {
            "index": 1,
            "tag": "a",
            "text": "Next Page",
            "attributes": {"href": "/page/2", "class": ["pagination-next"]},
            "locators": {"data_id": "[data-element-id='elem-1']"}
        },
        {
            "index": 2,
            "tag": "button",
            "text": "Login",
            "attributes": {"type": "submit", "class": ["btn", "btn-primary"]},
            "locators": {"data_id": "[data-element-id='elem-2']"}
        },
        {
            "index": 3,
            "tag": "a",
            "text": "Understanding AI Safety",
            "attributes": {"href": "thread-67890-1-1.html", "class": ["post-link"]},
            "locators": {"data_id": "[data-element-id='elem-3']"}
        }
    ]

    engine = QueryEngine()

    # Test 1: Natural language query for forum posts
    print("\n1. Find all forum post links:")
    results = engine.query_elements(elements, query="Find all forum post links")
    print(f"   Found {len(results)} results:")
    for r in results:
        print(f"   - {r['text']}")

    # Test 2: Natural language query for navigation
    print("\n2. Find the next page button:")
    results = engine.query_elements(elements, query="Get the next page button")
    print(f"   Found {len(results)} results:")
    for r in results:
        print(f"   - {r['text']}")

    # Test 3: Structured filter by tag
    print("\n3. Find all buttons:")
    results = engine.query_elements(elements, filters={"tag": "button"})
    print(f"   Found {len(results)} results:")
    for r in results:
        print(f"   - {r['text']}")

    # Test 4: Structured filter by href pattern
    print("\n4. Find links with thread pattern:")
    results = engine.query_elements(
        elements,
        filters={"tag": "a", "href_pattern": "thread-*"}
    )
    print(f"   Found {len(results)} results:")
    for r in results:
        print(f"   - {r['text']} -> {r['attributes']['href']}")

    # Test 5: Find by text
    print("\n5. Find by exact text 'Login':")
    results = engine.find_by_text(elements, "Login", exact=True)
    print(f"   Found {len(results)} results:")
    for r in results:
        print(f"   - {r['tag']}: {r['text']}")

    print("\n✅ Query engine test passed!")
