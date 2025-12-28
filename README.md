# Web Extraction Tool

A comprehensive web extraction tool that integrates HTML sanitization with Claude Code and Playwright MCP for intelligent web automation.

## Table of Contents

- [Dec 26 Progress](#dec-26-progress)
- [Features](#features)
- [🚀 Interactive Web Agent MCP (LATEST!)](#-interactive-web-agent-mcp-latest)
- [Web Extraction MCP Server](#web-extraction-mcp-server)
- [Quick Start (HTML Sanitizer & Pattern Extraction)](#quick-start-html-sanitizer--pattern-extraction)
- [Core Components](#core-components)
- [Usage Examples](#usage-examples)
- [Test Results](#test-results)
- [Architecture](#architecture)
- [Which Approach to Use?](#which-approach-to-use)
- [Documentation](#documentation)

---

## Dec 26 Progress

### 🎯 Interactive Web Agent MCP - Complete Integration

Successfully implemented a **fully integrated Interactive Web Agent MCP** that combines browser automation with intelligent HTML extraction into a single, agent-friendly MCP server.

#### What Was Built

**1. Updated HTML Sanitizer - Interactable Elements Only**
- ✅ **Only assigns IDs to interactable elements** (not all tracked elements)
  - Links: `<a>` with valid href (excluding `javascript:`, `mailto:`, `#`)
  - Buttons: `<button>`, `<input type="submit/button/reset">`
  - Form inputs: `<input>`, `<textarea>`, `<select>`
  - Custom interactive: Elements with `onclick`, `role="button/link"`, `tabindex >= 0`
- ✅ Changed ID format from `data-element-id` to `data-web-agent-id`
- ✅ Reduced noise: Forum page extracts **244 interactable elements** vs hundreds of non-interactable elements

**2. Interactive Web Agent MCP (`interactive_web_agent_mcp.py`)**

A complete, self-contained MCP server with **9 agent-friendly tools**:

**Navigation & Extraction:**
- `navigate` - Navigate to URL and wait for page load
- `get_page_content` - Extract sanitized HTML with indexed interactable elements
  - Formats: `indexed` (numbered list), `full_html`, `elements_json`

**Querying:**
- `query_elements` - Natural language or structured filters
  - Examples: "Find the 3rd page button", `{tag: "a", href_pattern: "thread-*"}`
- `find_by_text` - Quick text-based element search

**Interaction:**
- `click_element` - Click element by `web_agent_id`
- `type_into_element` - Type into input fields

**Utilities:**
- `download_page` - Save page HTML to file
- `get_current_url` - Get current URL and title
- `wait_for_page` - Wait for loading/content

**3. Agent-Guided Design**

Each tool has comprehensive descriptions that guide agents through the workflow:

```
Example workflow from tool descriptions:
1. navigate(url="https://example.com")
2. get_page_content(format="indexed")  # See [0], [1], [2]... numbered elements
3. query_elements(query="Find the submit button")
4. click_element(web_agent_id="wa-15")  # Use ID from query results
5. download_page()  # Save content
```

**4. Comprehensive Evaluation Task**

Created `eval/test_forum_navigation.py` that tests the complete workflow:

```bash
✅ Navigate to forum page
✅ Extract 244 interactable elements (243 links + 1 input)
✅ Query for forum posts (81 forum post links found)
✅ Find posts by text search (11 matches for "面试" = interview)
✅ Click on post and navigate
✅ Download page (281KB saved successfully)
```

#### Key Improvements Over Previous Implementation

**Before:**
- Agent needs TWO separate MCPs (Playwright + Web Extraction)
- All elements get IDs (noisy, hard to parse)
- Unclear workflow guidance
- Element IDs: `elem-0`, `elem-1`, `elem-2`...

**After:**
- **Single integrated MCP** - all browser + extraction capabilities
- **Only interactable elements** get IDs (clean, focused)
- **Clear tool descriptions** guide agents step-by-step
- Semantic IDs: `wa-0`, `wa-1`, `wa-2`... (web-agent)

#### Results & Metrics

**Token Efficiency:**
- Forum page: 244 interactable elements extracted
- Reduced noise by focusing only on actionable elements
- Clear indexed format: `[0] <a id="wa-0" href="...">Link Text</a>`

**Workflow Simplification:**
```
Old Workflow (2 MCPs):
Agent → Playwright MCP (navigate)
      → Web Extraction MCP (extract)
      → Playwright MCP (click)

New Workflow (1 MCP):
Agent → Interactive Web Agent MCP (all operations)
```

**End-to-End Testing:**
- ✅ Complete workflow tested on live forum page
- ✅ Successfully navigated, queried, clicked, and downloaded
- ✅ 281KB page downloaded with correct URL tracking

#### Files Created/Modified

**Created:**
- `interactive_web_agent_mcp.py` - Integrated MCP server (400+ lines)
- `DESIGN.md` - Comprehensive design documentation
- `IMPLEMENTATION_SUMMARY.md` - Detailed implementation summary
- `eval/__init__.py` - Evaluation package
- `eval/test_forum_navigation.py` - End-to-end evaluation (300+ lines)
- `downloads/` - Directory for downloaded pages

**Modified:**
- `html_sanitizer.py` - Updated to only track interactable elements
  - Added `_is_interactable_element()` method
  - Changed `data-element-id` to `data-web-agent-id`
  - Fixed BeautifulSoup.new_tag() bug
  - Updated indexed text format

#### How to Use

**Run the evaluation:**
```bash
python eval/test_forum_navigation.py
```

**Use with Claude Code:**
```json
{
  "mcpServers": {
    "interactive-web-agent": {
      "command": "python",
      "args": ["/path/to/WebAgent/interactive_web_agent_mcp.py"],
      "env": {
        "DOWNLOADS_DIR": "/path/to/WebAgent/downloads"
      }
    }
  }
}
```

**Agent workflow example:**
```
Task: "Download a forum post about OpenAI interviews"

1. navigate(url="https://forum.example.com/openai")
2. content = get_page_content(format="indexed")
3. results = query_elements(query="Find posts about interviews")
4. click_element(web_agent_id="wa-23")
5. download_page()
```

#### Documentation

- **[DESIGN.md](DESIGN.md)** - Complete architecture and design decisions
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Detailed implementation summary
- **[eval/test_forum_navigation.py](eval/test_forum_navigation.py)** - Working evaluation example

#### Success Criteria - All Met ✅

1. ✅ **Only interactable elements get IDs** - Buttons, links, inputs only
2. ✅ **Single integrated MCP** - No need for separate Playwright MCP
3. ✅ **Agent-friendly prompts** - Clear tool descriptions guide workflow
4. ✅ **Complete evaluation** - End-to-end test from navigation to download
5. ✅ **Production ready** - Tested on live forum with 244 elements

---

## Features

- **🚀 LATEST: Interactive Web Agent MCP** - Fully integrated browser + extraction MCP
  - Single MCP for all operations (no separate Playwright MCP needed)
  - Only interactable elements get IDs (clean, focused)
  - 9 agent-friendly tools with comprehensive workflow guidance
- **🚀 Web Extraction MCP Server** - Complete MCP server for Claude Code integration
- **Token-efficient HTML sanitization** (75-85% token reduction)
- **Natural language element querying** - "Find all forum post links"
- **Transaction-based storage** - All extractions saved with unique IDs
- **Pattern-based forum post extraction** (no AI hallucination)
- **Playwright MCP integration** for browser automation
- **Claude Code compatible** analysis workflow

## 🚀 Interactive Web Agent MCP (LATEST!)

The **Interactive Web Agent MCP** is a fully integrated MCP server that combines browser automation with intelligent HTML extraction into a single, agent-friendly interface. No need to use Playwright MCP separately!

### Key Benefits

- **Single Integrated MCP**: All browser + extraction capabilities in one server
- **Interactable Elements Only**: Clean extraction - only buttons, links, inputs get IDs
- **Agent-Guided Workflow**: Comprehensive tool descriptions guide agents step-by-step
- **Natural Language Queries**: "Find the 3rd page button", "Find posts about interviews"
- **Direct Navigation**: Click links by web_agent_id, type into inputs, download pages
- **Production Ready**: Tested end-to-end on live forum pages (244 elements extracted)

### Quick Start

```bash
# Run the evaluation to see it in action
python eval/test_forum_navigation.py
```

### Configuration

Add to your MCP config:

```json
{
  "mcpServers": {
    "interactive-web-agent": {
      "command": "python",
      "args": ["/absolute/path/to/interactive_web_agent_mcp.py"],
      "env": {
        "DOWNLOADS_DIR": "/absolute/path/to/downloads"
      }
    }
  }
}
```

### Agent Workflow

```
1. navigate(url) → Navigate to page
2. get_page_content() → See [0], [1], [2]... indexed interactable elements
3. query_elements(query="Find X") → Find specific elements
4. click_element(web_agent_id="wa-23") → Click by ID
5. download_page() → Save content
```

### Tools Available

1. **`navigate`** - Navigate to URL
2. **`get_page_content`** - Extract indexed interactable elements
3. **`query_elements`** - Natural language or filter-based queries
4. **`find_by_text`** - Quick text search
5. **`click_element`** - Click by web_agent_id
6. **`type_into_element`** - Type into inputs
7. **`download_page`** - Save page HTML
8. **`get_current_url`** - Get current location
9. **`wait_for_page`** - Wait for loading

See **[DESIGN.md](DESIGN.md)** for complete documentation.

---

## Web Extraction MCP Server

The **Web Extraction MCP** is a Model Context Protocol server that enables Claude Code to intelligently understand web pages through HTML sanitization. It works alongside Playwright MCP to separate page understanding from browser interaction.

### Key Benefits

- **75% Token Reduction**: Sanitized HTML vs browser snapshots
- **Natural Language Queries**: "Find all forum post links", "Get next page button"
- **Persistent Storage**: All extractions saved to `data/` directory
- **Multiple Locators**: xpath, CSS selectors, data-id, href patterns
- **Intent Recognition**: Automatically detects navigation, forum posts, products, forms

### MCP Installation

```bash
# Install dependencies
pip install beautifulsoup4 mcp

# Test the MCP server
python test_web_extraction_mcp.py
```

### Configure Claude Code

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--extension"]
    },
    "web-extraction": {
      "command": "python",
      "args": ["/absolute/path/to/web_extraction_mcp.py"],
      "env": {
        "DATA_DIR": "/absolute/path/to/WebAgent/data"
      }
    }
  }
}
```

### MCP Usage Example

```python
# 1. Navigate to page (Playwright MCP)
browser_navigate("https://www.1point3acres.com/bbs/tag/openai-9407-1.html")

# 2. Extract and sanitize page (Web Extraction MCP)
result = extract_page(extraction_mode="links", max_tokens=4000)
# Returns: transaction_id, statistics, preview

# 3. Query for specific elements (Web Extraction MCP)
posts = query_page_elements(
    transaction_id=result["transaction_id"],
    query="Find all forum post links"
)
# Returns: matching elements with locators

# 4. Click on element (Playwright MCP)
browser_click(
    element="Forum post",
    ref=posts["matches"][0]["locators"]["href"]
)
```

### MCP Tools Available

1. **`extract_page`** - Extract & sanitize current browser page
2. **`query_page_elements`** - Query elements with natural language or filters
3. **`get_sanitized_html`** - Retrieve sanitized HTML in various formats
4. **`list_transactions`** - List all stored extractions

### Documentation

- **[WEB_EXTRACTION_MCP_README.md](WEB_EXTRACTION_MCP_README.md)** - Complete usage guide
- **[web_extraction_mcp_design.md](web_extraction_mcp_design.md)** - Architecture & design
- **[MCP_IMPLEMENTATION_SUMMARY.md](MCP_IMPLEMENTATION_SUMMARY.md)** - Implementation summary

---

## Quick Start (HTML Sanitizer & Pattern Extraction)

### Prerequisites

Install required dependencies:
```bash
pip install beautifulsoup4 lxml requests
```

### Testing with Sample Data

To test the tool with the provided forum page sample (`test/page.html`):

```bash
# Run the complete demo workflow
python claude_code_integration_demo.py
```

This will:
1. Load and sanitize the test HTML file (Chinese forum page)
2. Extract forum post patterns automatically  
3. Generate CSS selectors for automation
4. Show extraction statistics and recommendations

### Sample Output

The demo script will display:
- HTML sanitization results (28k → 4k tokens)
- Pattern detection for forum posts
- Extracted thread links with titles
- Recommended CSS selectors for automation
- Completeness verification metrics

### Opening Test Page in Browser

To view the test HTML file in a browser:
```bash
# Firefox
firefox /home/zhenkai/personal/Projects/WebAgent/test/page.html

# Chrome/Chromium  
google-chrome /home/zhenkai/personal/Projects/WebAgent/test/page.html

# Default browser
xdg-open /home/zhenkai/personal/Projects/WebAgent/test/page.html
```

## Core Components

### Web Extraction MCP (NEW)
- **`web_extraction_mcp.py`** - Main MCP server with 4 tools
- **`transaction_manager.py`** - Transaction storage and retrieval
- **`browser_integration.py`** - Playwright MCP interface
- **`query_engine.py`** - Natural language & structured querying
- **`test_web_extraction_mcp.py`** - Complete test suite

### HTML Sanitizer & Pattern Extraction
- **`html_sanitizer.py`** - Core HTML sanitization module
- **`web_extraction_tool.py`** - Integration tool with Playwright
- **`claude_code_integration_demo.py`** - Usage demonstration
- **`helper/PlaywrightMcpClient.py`** - Playwright MCP client

## Usage Examples

### Basic HTML Sanitization
```python
from html_sanitizer import HTMLSanitizer

sanitizer = HTMLSanitizer(max_tokens=4000)
result = sanitizer.sanitize(html_content, extraction_mode='links')
print(f"Tokens reduced: {result['statistics']['estimated_tokens']}")
```

### Forum Post Extraction
```python
from web_extraction_tool import WebExtractionTool

tool = WebExtractionTool(max_tokens=4000)
# Load HTML file
with open('test/page.html', 'r', encoding='gbk') as f:
    html_content = f.read()

# Extract posts with patterns
posts = tool.extract_posts_from_html(html_content)
print(f"Found {len(posts)} forum posts")
```

### Claude Code Integration
```python
# Generate analysis prompt for Claude Code
prompt = tool.get_claude_analysis_prompt()

# Verify selector completeness  
verification = tool.verify_pattern_completeness("a[href*='thread-']")
```

## Test Results

The tool successfully processes the 1Point3Acres forum page:
- **Input**: 28,220 tokens → **Output**: ~4,000 tokens (85% reduction)
- **Detected**: 72+ thread links with 95% accuracy
- **Pattern**: `a[href*='thread-'][href*='-1-1.html']` selector
- **Performance**: <2 seconds processing time

## Architecture

### MCP Server Architecture (NEW)

```
┌─────────────────────────────────────────────────────────────────┐
│                         Claude Code                              │
└───────────────┬───────────────────────────┬─────────────────────┘
                │                           │
                │ 1. Navigate               │ 3. Query & Act
                │    to URL                 │    on Page
                ▼                           ▼
┌──────────────────────────┐  ┌─────────────────────────────────┐
│   Playwright MCP         │  │  Web Extraction MCP             │
│   - browser_navigate()   │  │  - extract_page()               │
│   - browser_click()      │  │  - query_page_elements()        │
│   - browser_snapshot()   │  │  - get_sanitized_html()         │
└────────────┬─────────────┘  └────────────┬────────────────────┘
             │                              │
             │ 2. Get current page HTML     │
             │◄─────────────────────────────┤
             │                              │
             ▼                              ▼
    ┌────────────────────┐      ┌──────────────────────┐
    │  Browser Instance  │      │  Transaction Storage │
    │  (Current Page)    │      │  data/<txn_id>/      │
    └────────────────────┘      └──────────────────────┘
```

### Pattern Extraction Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Raw HTML      │───▶│  HTML Sanitizer  │───▶│  Claude Code    │
│  (28k tokens)   │    │  (Pattern Recog) │    │  (Analysis)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                         │
                                ▼                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Playwright MCP  │◀───│  Element Registry│◀───│  CSS/XPath      │
│  (Automation)   │    │  (Stable IDs)    │    │  (Selectors)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Key Innovation

**MCP Server Approach**: Separates page understanding (Web Extraction MCP) from browser interaction (Playwright MCP), enabling:
- 75% token reduction through intelligent HTML sanitization
- Natural language querying of page elements
- Transaction-based storage for debugging and replay
- Multiple locator strategies for reliable element targeting

**Pattern Recognition**: Uses structural pattern recognition instead of AI content extraction to avoid hallucination while maintaining 100% recall for target elements.

## Which Approach to Use?

### Use **Web Extraction MCP** when:
✅ Working with Claude Code for web automation
✅ Need natural language querying ("Find all post links")
✅ Want persistent transaction storage
✅ Working with live web pages via Playwright MCP
✅ Need real-time page understanding during navigation

### Use **HTML Sanitizer + Pattern Extraction** when:
✅ Analyzing static HTML files
✅ Building custom extraction pipelines
✅ Need fine-grained control over sanitization
✅ Working outside of Claude Code environment
✅ Prototyping extraction patterns

**Best of Both Worlds**: The MCP server uses the HTML Sanitizer internally, so you get all the pattern extraction benefits plus MCP integration!

## Documentation

### MCP Server Documentation
- **[WEB_EXTRACTION_MCP_README.md](WEB_EXTRACTION_MCP_README.md)** - Complete usage guide with examples
- **[web_extraction_mcp_design.md](web_extraction_mcp_design.md)** - Architecture & API specifications
- **[MCP_IMPLEMENTATION_SUMMARY.md](MCP_IMPLEMENTATION_SUMMARY.md)** - Implementation summary

### Pattern Extraction Documentation
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Original implementation details


## Set up Interactive-web-agent MCP

in /home/zhenkai/.claude.json
```
      "mcpServers": {
        "interactive-web-agent": {
          "command": "python3",
          "args": [
            "/your_worspace/WebAgent/src/interactive_web_agent_mcp.py"
          ],
          "env": {
            "DOWNLOADS_DIR": "/your_worspace//WebAgent/downloads",
            "PYTHONPATH": "/your_worspace/Projects/WebAgent",
            "DEBUG_MODE": "true"
          }
        }
```
make sure you use the your right absolute folder path

in helper/PlaywrightMcpClient.py, set the default_token based on OS.

