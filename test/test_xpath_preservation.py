#!/usr/bin/env python3
"""Test to verify XPath is generated from original HTML structure"""

from html_sanitizer import HTMLSanitizer

# Test HTML with hidden elements that will be removed during sanitization
test_html = """
<html>
<body>
    <nav>
        <script>console.log('test')</script>
        <a href="/hidden-ad" style="display:none">Hidden Ad</a>
        <a href="/home" class="nav-link">Home</a>
        <div style="display:none">Hidden Content</div>
        <a href="/about" class="nav-link">About</a>
        <style>.test { color: red; }</style>
        <a href="/contact" class="nav-link">Contact</a>
    </nav>
</body>
</html>
"""

print("=== Testing XPath Preservation ===\n")

# Sanitize the HTML
sanitizer = HTMLSanitizer(max_tokens=4000)
result = sanitizer.sanitize(test_html, extraction_mode='links')

print("Element Registry:")
print("-" * 80)
for elem in result['element_registry']:
    print(f"[{elem['index']}] {elem['tag']} - {elem['text']}")
    print(f"    web_agent_id: {elem['web_agent_id']}")
    print(f"    XPath: {elem['locators']['xpath']}")
    print(f"    href: {elem['attributes'].get('href', 'N/A')}")
    print()

print("\n=== Expected Behavior ===")
print("The XPath should reflect positions in ORIGINAL HTML (with hidden elements):")
print("- 'Home' should be //nav/a[2] (because hidden ad link is a[1])")
print("- 'About' should be //nav/a[3]")
print("- 'Contact' should be //nav/a[4]")
print("\nThese XPaths will work correctly on the original website!")

print("\n=== Sanitized HTML (for LLM) ===")
print(result['sanitized_html'][:500])
print("\nNote: Scripts, styles, and hidden elements are removed for LLM efficiency,")
print("but XPath in registry still targets the original structure.")
