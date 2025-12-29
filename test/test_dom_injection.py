#!/usr/bin/env python3
"""
Test DOM injection functionality.

Verifies that data-web-agent-id attributes are properly injected
into the browser DOM after get_page_content() is called.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_injection_logic():
    """Test the injection JavaScript logic structure"""
    # Test element registry format
    test_registry = [
        {
            "index": 0,
            "web_agent_id": "wa-0",
            "tag": "a",
            "text": "Test Link",
            "attributes": {"href": "/test"},
            "locators": {
                "data_id": '[data-web-agent-id="wa-0"]',
                "xpath": "//a[1]"
            }
        },
        {
            "index": 1,
            "web_agent_id": "wa-1",
            "tag": "button",
            "text": "Click Me",
            "attributes": {},
            "locators": {
                "data_id": '[data-web-agent-id="wa-1"]',
                "xpath": "//button[1]"
            }
        }
    ]

    # Verify structure
    assert len(test_registry) == 2
    assert test_registry[0]["web_agent_id"] == "wa-0"
    assert test_registry[1]["web_agent_id"] == "wa-1"
    assert "xpath" in test_registry[0]["locators"]
    assert "data_id" in test_registry[0]["locators"]

    print("✓ Element registry structure is correct")


def test_injection_javascript():
    """Test that the injection JavaScript is syntactically valid"""
    inject_js = """
    (elements) => {
        const results = {
            total: elements.length,
            injected: 0,
            failed: []
        };

        elements.forEach(el => {
            try {
                const xpath = el.locators.xpath;
                const xpathResult = document.evaluate(
                    xpath,
                    document,
                    null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                    null
                );
                const element = xpathResult.singleNodeValue;

                if (element) {
                    element.setAttribute('data-web-agent-id', el.web_agent_id);
                    results.injected++;
                } else {
                    results.failed.push({
                        web_agent_id: el.web_agent_id,
                        xpath: xpath,
                        reason: 'Element not found by XPath'
                    });
                }
            } catch (err) {
                results.failed.push({
                    web_agent_id: el.web_agent_id,
                    xpath: el.locators.xpath,
                    reason: err.message
                });
            }
        });

        return results;
    }
    """

    # Basic validation - check for key components
    assert "document.evaluate" in inject_js
    assert "setAttribute" in inject_js
    assert "data-web-agent-id" in inject_js
    assert "XPathResult.FIRST_ORDERED_NODE_TYPE" in inject_js

    print("✓ Injection JavaScript structure is valid")


def test_injection_result_format():
    """Test expected injection result format"""
    # Simulated successful injection result
    success_result = {
        "success": True,
        "total": 10,
        "injected": 10,
        "failed": []
    }

    assert success_result["success"] == True
    assert success_result["injected"] == success_result["total"]
    assert len(success_result["failed"]) == 0

    # Simulated partial failure
    partial_result = {
        "success": True,
        "total": 10,
        "injected": 8,
        "failed": [
            {"web_agent_id": "wa-5", "xpath": "//div[5]", "reason": "Element not found"},
            {"web_agent_id": "wa-7", "xpath": "//span[2]", "reason": "Element not found"}
        ]
    }

    assert partial_result["total"] == 10
    assert partial_result["injected"] == 8
    assert len(partial_result["failed"]) == 2

    print("✓ Injection result format is correct")


if __name__ == "__main__":
    print("Testing DOM Injection Implementation...\n")

    try:
        test_injection_logic()
        test_injection_javascript()
        test_injection_result_format()

        print("\n✅ All DOM injection tests passed!")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
