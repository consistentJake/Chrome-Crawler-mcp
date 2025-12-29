#!/usr/bin/env python3
"""
Find what pagination links actually exist on the page
"""

import json
import sys
import time

sys.path.append('/Users/zhenkai/Documents/personal/Projects/WebAgent/helper')
from ChromeMcpClient import MCPChromeClient

def main():
    client = MCPChromeClient()

    try:
        print("=" * 70)
        print("Navigating to page 1")
        print("=" * 70)
        client.chrome_navigate("https://www.1point3acres.com/bbs/tag-9407-1.html")
        time.sleep(3)

        # Find ALL links on the page
        print("\n" + "=" * 70)
        print("Finding ALL links with 'tag-9407' in href")
        print("=" * 70)

        find_all_links = """
        var links = document.querySelectorAll('a');
        var results = [];
        for (var i = 0; i < links.length; i++) {
            var href = links[i].href || '';
            if (href.includes('tag-9407') || href.includes('tag/9407')) {
                results.push({
                    text: links[i].textContent.trim(),
                    href: href,
                    outerHTML: links[i].outerHTML.substring(0, 150)
                });
            }
        }
        return JSON.stringify({
            count: results.length,
            links: results.slice(0, 20)  // First 20 results
        });
        """

        result = client.browser_evaluate(f"() => {{ {find_all_links} }}")

        if result.get("status") == "success":
            content = result.get("result", {}).get("content", [])
            if content:
                text = content[0].get("text", "{}")
                try:
                    data = json.loads(text)
                    print(f"\nFound {data.get('count', 0)} links containing 'tag-9407'")

                    links = data.get('links', [])
                    for i, link in enumerate(links):
                        print(f"\n[{i}] Text: '{link['text']}'")
                        print(f"    Href: {link['href']}")
                        print(f"    HTML: {link['outerHTML'][:100]}...")
                except Exception as e:
                    print(f"Error parsing: {e}")
                    print(f"Raw: {text}")

        # Specifically look for pagination/page number links
        print("\n" + "=" * 70)
        print("Looking for numeric pagination links")
        print("=" * 70)

        find_pagination = """
        var links = document.querySelectorAll('a');
        var pageLinks = [];
        for (var i = 0; i < links.length; i++) {
            var text = links[i].textContent.trim();
            var href = links[i].href || '';

            // Look for numeric text (page numbers)
            if (text.match(/^[0-9]+$/) && href.includes('tag')) {
                pageLinks.push({
                    pageNumber: text,
                    href: href,
                    outerHTML: links[i].outerHTML
                });
            }
        }
        return JSON.stringify({
            count: pageLinks.length,
            pages: pageLinks
        });
        """

        result = client.browser_evaluate(f"() => {{ {find_pagination} }}")

        if result.get("status") == "success":
            content = result.get("result", {}).get("content", [])
            if content:
                text = content[0].get("text", "{}")
                try:
                    data = json.loads(text)
                    print(f"\nFound {data.get('count', 0)} numeric pagination links")

                    pages = data.get('pages', [])
                    for page in pages:
                        print(f"\nPage {page['pageNumber']}:")
                        print(f"  Href: {page['href']}")
                        print(f"  HTML: {page['outerHTML'][:150]}")

                        # If it's page 3, try clicking it
                        if page['pageNumber'] == '3':
                            print("\n  *** THIS IS PAGE 3! ***")
                            page3_href = page['href']
                except Exception as e:
                    print(f"Error: {e}")
                    print(f"Raw: {text}")

        # Get the page HTML to examine
        print("\n" + "=" * 70)
        print("Getting page HTML for manual inspection")
        print("=" * 70)

        html_result = client.get_html_content()
        if html_result.get("status") == "success":
            result_data = html_result.get("result", {})
            content = result_data.get("content", [])
            if content:
                outer_data = json.loads(content[0].get("text", "{}"))
                inner_text = outer_data.get("data", {}).get("content", [{}])[0].get("text", "{}")
                inner_data = json.loads(inner_text)
                html = inner_data.get("htmlContent", "")

                # Save HTML to file for inspection
                with open("/tmp/page1_debug.html", "w", encoding="utf-8") as f:
                    f.write(html)

                print("HTML saved to: /tmp/page1_debug.html")

                # Search for page 3 references in HTML
                import re
                page3_refs = re.findall(r'<a[^>]*tag[^>]*3[^>]*>.*?</a>', html, re.DOTALL)
                print(f"\nFound {len(page3_refs)} potential page 3 links in HTML")
                for i, ref in enumerate(page3_refs[:5]):
                    print(f"\n[{i}] {ref[:200]}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        client.close()

if __name__ == "__main__":
    main()
