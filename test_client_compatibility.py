#!/usr/bin/env python3
"""
Integration test to verify API compatibility between ChromeMcpClient and PlaywrightMcpClient.
Tests that both clients have the same output format for common methods.
"""

import time
import sys
import os
import json
from typing import Dict, Any, List

# Add the helper directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'helper'))

from ChromeMcpClient import MCPChromeClient
from PlaywrightMcpClient import MCPPlaywrightClient


class ClientCompatibilityTest:
    """Test suite to verify client compatibility"""

    def __init__(self):
        self.chrome_client = None
        self.playwright_client = None
        self.test_results = []
        self.format_issues = []

    def print_section_header(self, title):
        """Print a formatted section header"""
        print("\n" + "=" * 80)
        print(f"{title:^80}")
        print("=" * 80)

    def print_test_header(self, test_name):
        """Print a formatted test header"""
        print("\n" + "-" * 80)
        print(f"TEST: {test_name}")
        print("-" * 80)

    def compare_response_format(self, method_name: str, chrome_result: Dict[str, Any],
                                playwright_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare response formats from both clients.

        Returns:
            Dict with comparison results
        """
        comparison = {
            "method": method_name,
            "chrome_status": chrome_result.get("status"),
            "playwright_status": playwright_result.get("status"),
            "format_match": True,
            "issues": []
        }

        # Check if both have 'status' field
        if "status" not in chrome_result:
            comparison["issues"].append("Chrome result missing 'status' field")
            comparison["format_match"] = False

        if "status" not in playwright_result:
            comparison["issues"].append("Playwright result missing 'status' field")
            comparison["format_match"] = False

        # Check if both have 'result' field (when successful)
        if chrome_result.get("status") == "success" and "result" not in chrome_result:
            comparison["issues"].append("Chrome success response missing 'result' field")
            comparison["format_match"] = False

        if playwright_result.get("status") == "success" and "result" not in playwright_result:
            comparison["issues"].append("Playwright success response missing 'result' field")
            comparison["format_match"] = False

        # Check result structure (both should have content array with type and text)
        if chrome_result.get("status") == "success" and playwright_result.get("status") == "success":
            chrome_res = chrome_result.get("result", {})
            playwright_res = playwright_result.get("result", {})

            # Check if both have similar structure
            chrome_has_content = "content" in chrome_res
            playwright_has_content = "content" in playwright_res

            if chrome_has_content != playwright_has_content:
                comparison["issues"].append(
                    f"Content field presence mismatch: Chrome={chrome_has_content}, Playwright={playwright_has_content}"
                )
                comparison["format_match"] = False

            # Check content structure if both have it
            if chrome_has_content and playwright_has_content:
                chrome_content = chrome_res.get("content", [])
                playwright_content = playwright_res.get("content", [])

                if isinstance(chrome_content, list) and isinstance(playwright_content, list):
                    if len(chrome_content) > 0 and len(playwright_content) > 0:
                        # Check first item structure
                        chrome_item = chrome_content[0]
                        playwright_item = playwright_content[0]

                        if not (isinstance(chrome_item, dict) and "type" in chrome_item and "text" in chrome_item):
                            comparison["issues"].append("Chrome content item missing 'type' or 'text' fields")
                            comparison["format_match"] = False

                        if not (isinstance(playwright_item, dict) and "type" in playwright_item and "text" in playwright_item):
                            comparison["issues"].append("Playwright content item missing 'type' or 'text' fields")
                            comparison["format_match"] = False
                else:
                    comparison["issues"].append("Content is not a list in one or both clients")
                    comparison["format_match"] = False

        return comparison

    def print_comparison_result(self, comparison: Dict[str, Any]):
        """Print comparison result"""
        print(f"\nMethod: {comparison['method']}")
        print(f"Chrome Status: {comparison['chrome_status']}")
        print(f"Playwright Status: {comparison['playwright_status']}")
        print(f"Format Match: {'✓ YES' if comparison['format_match'] else '✗ NO'}")

        if comparison['issues']:
            print(f"\nIssues Found:")
            for issue in comparison['issues']:
                print(f"  - {issue}")

    def extract_text_from_result(self, result: Dict[str, Any]) -> str:
        """Extract text content from result for display"""
        if result.get("status") != "success":
            return f"Error: {result.get('message', 'Unknown error')}"

        res = result.get("result", {})
        content = res.get("content", [])

        if isinstance(content, list) and len(content) > 0:
            text = content[0].get("text", "")
            # Truncate if too long
            if len(text) > 200:
                return text[:200] + "..."
            return text
        return str(res)

    def test_navigation(self):
        """Test browser_navigate method"""
        self.print_test_header("browser_navigate")

        test_url = "https://www.example.com"

        print(f"\n[Chrome] Navigating to {test_url}...")
        chrome_result = self.chrome_client.browser_navigate(test_url)
        print(f"Result: {self.extract_text_from_result(chrome_result)}")

        time.sleep(2)

        print(f"\n[Playwright] Navigating to {test_url}...")
        playwright_result = self.playwright_client.browser_navigate(test_url)
        print(f"Result: {self.extract_text_from_result(playwright_result)}")

        time.sleep(2)

        comparison = self.compare_response_format("browser_navigate", chrome_result, playwright_result)
        self.print_comparison_result(comparison)
        self.test_results.append(comparison)

        if not comparison["format_match"]:
            self.format_issues.append(comparison)

    def test_evaluate(self):
        """Test browser_evaluate method"""
        self.print_test_header("browser_evaluate")

        js_code = "() => { return document.title; }"

        print(f"\n[Chrome] Evaluating: {js_code}")
        chrome_result = self.chrome_client.browser_evaluate(js_code)
        print(f"Result: {self.extract_text_from_result(chrome_result)}")

        print(f"\n[Playwright] Evaluating: {js_code}")
        playwright_result = self.playwright_client.browser_evaluate(js_code)
        print(f"Result: {self.extract_text_from_result(playwright_result)}")

        comparison = self.compare_response_format("browser_evaluate", chrome_result, playwright_result)
        self.print_comparison_result(comparison)
        self.test_results.append(comparison)

        if not comparison["format_match"]:
            self.format_issues.append(comparison)

    def test_content_equality(self):
        """Test that both clients return the same content for critical API calls"""
        self.print_test_header("Content Equality Tests")

        # Test 1: Get page title
        print("\n[Test 1] Getting page title...")
        chrome_title_result = self.chrome_client.browser_evaluate("() => document.title")
        playwright_title_result = self.playwright_client.browser_evaluate("() => document.title")

        chrome_title = self.extract_text_from_result(chrome_title_result)
        playwright_title = self.extract_text_from_result(playwright_title_result)

        print(f"  Chrome title: {chrome_title}")
        print(f"  Playwright title: {playwright_title}")

        if self.normalize_content(chrome_title) == self.normalize_content(playwright_title):
            print("  ✓ Titles match!")
        else:
            print("  ✗ Title mismatch!")
            self.format_issues.append({
                "method": "browser_evaluate (title)",
                "chrome_status": "success",
                "playwright_status": "success",
                "format_match": False,
                "issues": [f"Content mismatch: Chrome='{chrome_title}', Playwright='{playwright_title}'"]
            })

        # Test 2: Get current URL
        print("\n[Test 2] Getting current URL...")
        chrome_url_result = self.chrome_client.browser_evaluate("() => window.location.href")
        playwright_url_result = self.playwright_client.browser_evaluate("() => window.location.href")

        chrome_url = self.extract_text_from_result(chrome_url_result)
        playwright_url = self.extract_text_from_result(playwright_url_result)

        print(f"  Chrome URL: {chrome_url}")
        print(f"  Playwright URL: {playwright_url}")

        if self.normalize_content(chrome_url) == self.normalize_content(playwright_url):
            print("  ✓ URLs match!")
        else:
            print("  ✗ URL mismatch!")
            self.format_issues.append({
                "method": "browser_evaluate (url)",
                "chrome_status": "success",
                "playwright_status": "success",
                "format_match": False,
                "issues": [f"Content mismatch: Chrome='{chrome_url}', Playwright='{playwright_url}'"]
            })

        # Test 3: Get page HTML (critical for get_page_content)
        print("\n[Test 3] Getting page HTML (outerHTML)...")
        chrome_html_result = self.chrome_client.browser_evaluate("() => document.documentElement.outerHTML")
        playwright_html_result = self.playwright_client.browser_evaluate("() => document.documentElement.outerHTML")

        chrome_html = self.extract_full_result(chrome_html_result)
        playwright_html = self.extract_full_result(playwright_html_result)

        print(f"  Chrome HTML length: {len(chrome_html)} chars")
        print(f"  Playwright HTML length: {len(playwright_html)} chars")
        print(f"  Chrome HTML preview: {chrome_html[:200]}...")
        print(f"  Playwright HTML preview: {playwright_html[:200]}...")

        # Normalize whitespace for comparison
        chrome_html_normalized = self.normalize_content(chrome_html)
        playwright_html_normalized = self.normalize_content(playwright_html)

        if chrome_html_normalized == playwright_html_normalized:
            print("  ✓ HTML content matches exactly!")
        else:
            # Check if they're similar (allow for minor differences)
            similarity = self.calculate_similarity(chrome_html_normalized, playwright_html_normalized)
            print(f"  Content similarity: {similarity:.1%}")

            if similarity > 0.95:
                print("  ⚠ HTML content is very similar (>95%) but not identical")
            else:
                print("  ✗ HTML content significantly different!")
                self.format_issues.append({
                    "method": "browser_evaluate (outerHTML)",
                    "chrome_status": "success",
                    "playwright_status": "success",
                    "format_match": False,
                    "issues": [
                        f"Content mismatch: Chrome={len(chrome_html)} chars, Playwright={len(playwright_html)} chars",
                        f"Similarity: {similarity:.1%}"
                    ]
                })

    def normalize_content(self, content: str) -> str:
        """Normalize content for comparison (trim, collapse whitespace)"""
        import re
        # Remove markdown formatting if present (### Result\n"...")
        content = re.sub(r'###\s*Result\s*\n"([^"]*)"', r'\1', content)
        # Unescape common escape sequences
        content = content.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
        # Collapse multiple whitespace into single space
        content = ' '.join(content.split())
        return content.strip()

    def extract_full_result(self, result: Dict[str, Any]) -> str:
        """Extract full text content from result (without truncation)"""
        if result.get("status") != "success":
            return f"Error: {result.get('message', 'Unknown error')}"

        res = result.get("result", {})
        content = res.get("content", [])

        if isinstance(content, list) and len(content) > 0:
            text = content[0].get("text", "")
            # Parse from markdown format if present
            import re
            match = re.search(r'### Result\s*\n"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
            if match:
                html = match.group(1)
                html = html.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
                return html
            return text
        return str(res)

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings"""
        if not str1 or not str2:
            return 0.0

        # Use length-based similarity as a simple metric
        min_len = min(len(str1), len(str2))
        max_len = max(len(str1), len(str2))

        if max_len == 0:
            return 1.0

        # Count matching characters at the same position (simple approach)
        matches = sum(c1 == c2 for c1, c2 in zip(str1, str2))

        # Similarity is based on: matching chars / max length
        return matches / max_len

    def test_wait_for(self):
        """Test browser_wait_for method"""
        self.print_test_header("browser_wait_for")

        wait_time = 1.0

        print(f"\n[Chrome] Waiting for {wait_time} seconds...")
        chrome_result = self.chrome_client.browser_wait_for(time_seconds=wait_time)
        print(f"Result: {self.extract_text_from_result(chrome_result)}")

        print(f"\n[Playwright] Waiting for {wait_time} seconds...")
        playwright_result = self.playwright_client.browser_wait_for(time_seconds=wait_time)
        print(f"Result: {self.extract_text_from_result(playwright_result)}")

        comparison = self.compare_response_format("browser_wait_for", chrome_result, playwright_result)
        self.print_comparison_result(comparison)
        self.test_results.append(comparison)

        if not comparison["format_match"]:
            self.format_issues.append(comparison)

    def test_scroll_down(self):
        """Test scroll_down method"""
        self.print_test_header("scroll_down")

        print(f"\n[Chrome] Scrolling down...")
        chrome_result = self.chrome_client.scroll_down(times=1, amount=300)
        print(f"Result: {chrome_result}")

        time.sleep(0.5)

        print(f"\n[Playwright] Scrolling down...")
        playwright_result = self.playwright_client.scroll_down(times=1, amount=300)
        print(f"Result: {playwright_result}")

        comparison = self.compare_response_format("scroll_down", chrome_result, playwright_result)
        self.print_comparison_result(comparison)
        self.test_results.append(comparison)

        if not comparison["format_match"]:
            self.format_issues.append(comparison)

    def test_scroll_up(self):
        """Test scroll_up method"""
        self.print_test_header("scroll_up")

        print(f"\n[Chrome] Scrolling up...")
        chrome_result = self.chrome_client.scroll_up(times=1, amount=300)
        print(f"Result: {chrome_result}")

        time.sleep(0.5)

        print(f"\n[Playwright] Scrolling up...")
        playwright_result = self.playwright_client.scroll_up(times=1, amount=300)
        print(f"Result: {playwright_result}")

        comparison = self.compare_response_format("scroll_up", chrome_result, playwright_result)
        self.print_comparison_result(comparison)
        self.test_results.append(comparison)

        if not comparison["format_match"]:
            self.format_issues.append(comparison)

    def test_browser_tabs(self):
        """Test browser_tabs method"""
        self.print_test_header("browser_tabs (list)")

        print(f"\n[Chrome] Listing tabs...")
        chrome_result = self.chrome_client.browser_tabs(action="list")
        print(f"Result preview: {self.extract_text_from_result(chrome_result)}")

        print(f"\n[Playwright] Listing tabs...")
        playwright_result = self.playwright_client.browser_tabs(action="list")
        print(f"Result preview: {self.extract_text_from_result(playwright_result)}")

        comparison = self.compare_response_format("browser_tabs", chrome_result, playwright_result)
        self.print_comparison_result(comparison)
        self.test_results.append(comparison)

        if not comparison["format_match"]:
            self.format_issues.append(comparison)

    def test_screenshot(self):
        """Test browser_take_screenshot method"""
        self.print_test_header("browser_take_screenshot")

        print(f"\n[Chrome] Taking screenshot...")
        chrome_result = self.chrome_client.browser_take_screenshot(
            filename="chrome_compat_test",
            full_page=False
        )
        print(f"Result: {self.extract_text_from_result(chrome_result)}")

        print(f"\n[Playwright] Taking screenshot...")
        playwright_result = self.playwright_client.browser_take_screenshot(
            filename="playwright_compat_test",
            full_page=False
        )
        print(f"Result: {self.extract_text_from_result(playwright_result)}")

        comparison = self.compare_response_format("browser_take_screenshot", chrome_result, playwright_result)
        self.print_comparison_result(comparison)
        self.test_results.append(comparison)

        if not comparison["format_match"]:
            self.format_issues.append(comparison)

    def test_browser_integration_wrapper(self):
        """Test BrowserIntegration wrapper with both client types"""
        self.print_test_header("BrowserIntegration Wrapper Tests")

        # Import BrowserIntegration
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        from browser_integration import BrowserIntegration

        test_url = "https://www.example.com"

        # Test with Playwright client
        print("\n[Step 1] Testing BrowserIntegration with Playwright client...")
        playwright_integration = BrowserIntegration(client_type="playwright")
        playwright_integration.playwright_client.browser_navigate(test_url)
        time.sleep(2)

        pw_html = playwright_integration.get_current_page_html()
        pw_url = playwright_integration.get_current_url()
        pw_title = playwright_integration.get_page_title()

        print(f"  URL: {pw_url}")
        print(f"  Title: {pw_title}")
        print(f"  HTML length: {len(pw_html)} chars")
        print(f"  HTML preview: {pw_html[:200]}...")

        playwright_integration.close()
        print("  ✓ Playwright integration tested")

        # Test with Chrome client
        print("\n[Step 2] Testing BrowserIntegration with Chrome client...")
        chrome_integration = BrowserIntegration(client_type="chrome")
        chrome_integration.playwright_client.browser_navigate(test_url)
        time.sleep(2)

        chrome_html = chrome_integration.get_current_page_html()
        chrome_url = chrome_integration.get_current_url()
        chrome_title = chrome_integration.get_page_title()

        print(f"  URL: {chrome_url}")
        print(f"  Title: {chrome_title}")
        print(f"  HTML length: {len(chrome_html)} chars")
        print(f"  HTML preview: {chrome_html[:200]}...")

        chrome_integration.close()
        print("  ✓ Chrome integration tested")

        # Compare results
        print("\n[Step 3] Comparing BrowserIntegration results...")

        # URL comparison
        if pw_url == chrome_url:
            print(f"  ✓ URL match: {pw_url}")
        else:
            print(f"  ✗ URL mismatch: Playwright={pw_url}, Chrome={chrome_url}")
            self.format_issues.append({
                "method": "BrowserIntegration.get_current_url",
                "chrome_status": "success",
                "playwright_status": "success",
                "format_match": False,
                "issues": [f"Content mismatch: Playwright='{pw_url}', Chrome='{chrome_url}'"]
            })

        # Title comparison
        if pw_title == chrome_title:
            print(f"  ✓ Title match: {pw_title}")
        else:
            print(f"  ✗ Title mismatch: Playwright={pw_title}, Chrome={chrome_title}")
            self.format_issues.append({
                "method": "BrowserIntegration.get_page_title",
                "chrome_status": "success",
                "playwright_status": "success",
                "format_match": False,
                "issues": [f"Content mismatch: Playwright='{pw_title}', Chrome='{chrome_title}'"]
            })

        # HTML comparison (normalized)
        pw_html_norm = self.normalize_content(pw_html)
        chrome_html_norm = self.normalize_content(chrome_html)

        if pw_html_norm == chrome_html_norm:
            print(f"  ✓ HTML match (length: {len(pw_html)} chars)")
        else:
            # Check similarity
            similarity = self.calculate_similarity(pw_html_norm, chrome_html_norm)
            print(f"  Content similarity: {similarity:.1%}")

            if similarity > 0.95:
                print(f"  ⚠ HTML similar but not identical (Playwright: {len(pw_html)} chars, Chrome: {len(chrome_html)} chars)")
            else:
                print(f"  ✗ HTML mismatch (Playwright: {len(pw_html)} chars, Chrome: {len(chrome_html)} chars)")
                self.format_issues.append({
                    "method": "BrowserIntegration.get_current_page_html",
                    "chrome_status": "success",
                    "playwright_status": "success",
                    "format_match": False,
                    "issues": [
                        f"Content mismatch: Playwright={len(pw_html)} chars, Chrome={len(chrome_html)} chars",
                        f"Similarity: {similarity:.1%}"
                    ]
                })

    def generate_summary_report(self):
        """Generate summary report"""
        self.print_section_header("COMPATIBILITY TEST SUMMARY")

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["format_match"])
        failed_tests = total_tests - passed_tests

        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✓")
        print(f"Failed: {failed_tests} ✗")
        print(f"Pass Rate: {(passed_tests/total_tests*100):.1f}%")

        if self.format_issues:
            print("\n" + "=" * 80)
            print("FORMAT ISSUES DETECTED")
            print("=" * 80)

            for issue in self.format_issues:
                print(f"\n⚠️  Method: {issue['method']}")
                print(f"   Chrome Status: {issue['chrome_status']}")
                print(f"   Playwright Status: {issue['playwright_status']}")
                print(f"   Issues:")
                for problem in issue['issues']:
                    print(f"      - {problem}")
        else:
            print("\n✓ All compatibility tests passed!")
            print("Both clients have compatible output formats.")

    def run_all_tests(self):
        """Run all compatibility tests"""
        try:
            self.print_section_header("CLIENT COMPATIBILITY TEST SUITE")

            # Initialize clients
            print("\n[1/3] Initializing Chrome MCP Client...")
            self.chrome_client = MCPChromeClient()
            print("✓ Chrome client initialized")

            print("\n[2/3] Initializing Playwright MCP Client...")
            self.playwright_client = MCPPlaywrightClient()
            print("✓ Playwright client initialized")

            print("\n[3/3] Running compatibility tests...")

            # Run all tests
            self.test_navigation()
            self.test_evaluate()
            self.test_content_equality()  # NEW: Test content equality
            self.test_wait_for()
            self.test_scroll_down()
            self.test_scroll_up()
            self.test_browser_tabs()
            self.test_screenshot()
            self.test_browser_integration_wrapper()  # NEW: Test BrowserIntegration wrapper

            # Generate summary
            self.generate_summary_report()

            return 0 if not self.format_issues else 1

        except Exception as e:
            print(f"\n✗ Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()
            return 1

        finally:
            # Clean up
            if self.chrome_client:
                print("\n[Cleanup] Closing Chrome MCP Client...")
                self.chrome_client.close()
                print("✓ Chrome client closed")

            if self.playwright_client:
                print("[Cleanup] Closing Playwright MCP Client...")
                self.playwright_client.close()
                print("✓ Playwright client closed")


def main():
    """Main entry point"""
    test_suite = ClientCompatibilityTest()
    return test_suite.run_all_tests()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
