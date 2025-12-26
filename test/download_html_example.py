#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helper.PlaywrightMcpClient import MCPPlaywrightClient

def download_page_html(url, output_file):
    """Download full HTML content of a page using PlaywrightMcpClient"""
    
    # Initialize the client
    client = MCPPlaywrightClient()
    
    try:
        # Navigate to the URL
        print(f"Navigating to {url}")
        nav_result = client.browser_navigate(url)
        if nav_result.get("status") != "success":
            print(f"Navigation failed: {nav_result}")
            return False
        
        # Get the full HTML content using JavaScript evaluation
        print("Extracting HTML content...")
        html_result = client.browser_evaluate("() => document.documentElement.outerHTML")
        
        if html_result.get("status") == "success":
            result_data = html_result.get("result")
            
            # Check if there's an error in the result
            if isinstance(result_data, dict) and result_data.get("isError"):
                content_list = result_data.get("content", [])
                if content_list and isinstance(content_list, list):
                    error_text = content_list[0].get("text", "") if isinstance(content_list[0], dict) else str(content_list[0])
                    print(f"JavaScript evaluation error: {error_text}")
                    return False
            
            # Extract HTML content
            if isinstance(result_data, dict):
                content_list = result_data.get("content")
                if isinstance(content_list, list) and content_list:
                    # Extract text from the content list
                    html_content = ""
                    for item in content_list:
                        if isinstance(item, dict) and "text" in item:
                            html_content += item["text"]
                        else:
                            html_content += str(item)
                else:
                    html_content = result_data.get("value") or str(result_data)
            else:
                html_content = str(result_data)
            
            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"HTML content saved to: {output_file}")
            return True
        else:
            print(f"Failed to extract HTML: {html_result}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        # Clean up
        client.close()

if __name__ == "__main__":
    url = "https://www.1point3acres.com/bbs/tag/openai-9407-1.html"
    output_file = "/home/zhenkai/personal/Projects/WebAgent/test/playwright_page.html"
    
    success = download_page_html(url, output_file)
    if success:
        print("✅ HTML download completed successfully")
    else:
        print("❌ HTML download failed")