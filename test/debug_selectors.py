#!/usr/bin/env python3
"""Debug script to test selectors on downloaded HTML"""

import asyncio
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Playwright not available")
    exit(1)


async def debug_selectors():
    """Test various selectors to see what works"""

    html_file = list(Path(__file__).parent.glob("downloaded_full_page_*.html"))[-1]
    print(f"Testing with: {html_file}")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Load HTML
        await page.goto(html_file.absolute().as_uri())

        # Test various selectors
        selectors = [
            '[id^="post_"]',
            '[id^="pid"]',
            '[id^="postnum"]',
            'table[id^="pid"]',
            'div[id^="post_"]',
            '.t_f',
            '[id*="postmessage"]',
        ]

        for selector in selectors:
            count = await page.evaluate('''(selector) => document.querySelectorAll(selector).length''', selector)
            print(f"{selector:30} -> {count} elements")

            if count > 0 and count < 20:
                # Show first few IDs
                ids = await page.evaluate('''(selector) => {
                    const elements = document.querySelectorAll(selector);
                    return Array.from(elements).slice(0, 5).map(el => el.id || "no-id");
                }''', selector)
                print(f"  Sample IDs: {ids}")

        print()

        # Test the actual selector logic from parser
        result = await page.evaluate('''() => {
            let postElements = document.querySelectorAll('[id^="post_"]');
            console.log("post_: " + postElements.length);

            if (postElements.length === 0) {
              postElements = document.querySelectorAll('[id^="pid"]');
              console.log("pid: " + postElements.length);
            }
            if (postElements.length === 0) {
              postElements = document.querySelectorAll('[id^="postnum"]');
              console.log("postnum: " + postElements.length);
            }

            return {
              count: postElements.length,
              firstId: postElements[0]?.id,
              tagName: postElements[0]?.tagName
            };
        }''')

        print("Parser selector logic result:")
        print(f"  Count: {result['count']}")
        print(f"  First ID: {result.get('firstId')}")
        print(f"  Tag name: {result.get('tagName')}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_selectors())
