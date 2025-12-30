# 1Point3Acres Forum Parser

**Created:** 2025-12-29
**Parser Version:** 1.0.0
**Status:** ✅ Implemented and Registered

---

## Overview

A special parser for extracting structured data from 1point3acres.com forum pages. This parser follows the same architecture as the X.com parser and can extract:

- Main forum post with author info, content, and reactions
- All replies/reviews with user details, timestamps, and reactions
- Thread metadata (title, tags, etc.)
- User statistics (posts, replies, points)

---

## Architecture

### Parser Class

**File:** `src/special_parsers/onepoint3acres.py`

```python
class OnePoint3AcresParser(BaseParser):
    name = "1point3acres"
    description = "Extracts forum posts and replies with user info, content, and reactions"
    version = "1.0.0"
```

### Registration

**File:** `src/special_parsers/__init__.py`

```python
PARSER_REGISTRY = {
    "1point3acres": {
        "patterns": [
            r"1point3acres\.com",
            r"1point3acres",
        ],
        "parser_class": OnePoint3AcresParser,
        ...
    }
}
```

---

## Usage

### Via MCP Tool

```python
# 1. Navigate to a 1point3acres thread
navigate(url="https://www.1point3acres.com/bbs/thread-1157833-1-1.html")

# 2. Optional: Scroll to load more replies
scroll_down(times=5)

# 3. Parse and extract data
parse_page_with_special_parser(parser_name="auto")  # Auto-detects 1point3acres
# OR
parse_page_with_special_parser(parser_name="1point3acres")  # Explicit
```

### Programmatic Usage

```python
from special_parsers import OnePoint3AcresParser

parser = OnePoint3AcresParser()

# Validate page
if parser.validate_page(browser_client):
    # Extract data
    result = parser.parse(browser_client)

    print(f"Extracted {result['item_count']} items")
    print(f"Main post: {result['items']['main_post']}")
    print(f"Replies: {len(result['items']['replies'])}")
```

---

## Output Format

### Success Response

```json
{
  "parser": "1point3acres",
  "parser_version": "1.0.0",
  "url": "https://www.1point3acres.com/bbs/thread-1157833-1-1.html",
  "timestamp": "2025-12-29T10:30:00.123456",
  "item_count": 9,
  "items": {
    "main_post": {
      "post_id": "20740624",
      "user": {
        "username": "UserABC",
        "user_id": "370639",
        "stats": {
          "posts": "100",
          "replies": "500",
          "points": "2000"
        },
        "is_anonymous": false
      },
      "content": "Main post content here...",
      "timestamp": "2025-12-12 10:00",
      "reactions": {
        "likes": 5,
        "dislikes": 0,
        "emoji_reactions": [
          {"emoji": "😮", "count": 1}
        ]
      },
      "quotes": [],
      "url": "https://www.1point3acres.com/bbs/thread-1157833-1-1.html#20740624"
    },
    "replies": [
      {
        "post_id": "20741101",
        "user": {
          "username": "TommyDKOZ",
          "user_id": "844758",
          "stats": {
            "posts": "5",
            "replies": "29",
            "points": "355"
          },
          "is_anonymous": false
        },
        "content": "Reply content here...",
        "timestamp": "2025-12-12 23:04",
        "reactions": {
          "likes": 0,
          "dislikes": 0
        },
        "quotes": ["Quoted text from previous post"],
        "url": "https://www.1point3acres.com/bbs/thread-1157833-1-1.html#20741101"
      }
      // ... more replies
    ]
  },
  "metadata": {
    "page_title": "求开放爱的MLCoding和MLDesign面经 - 一亩三分地",
    "extraction_time_ms": 187,
    "thread_title": "求开放爱的MLCoding和MLDesign面经",
    "thread_tags": ["海外面经", "openai"],
    "total_replies": 8
  }
}
```

---

## Implementation Details

### JavaScript Extraction

The parser executes JavaScript in the browser context to extract structured data:

**Key Selectors:**

```javascript
// Post containers
document.querySelectorAll('[id^="postnum"]')  // All posts

// Thread metadata
document.querySelector('h1.ts')  // Thread title
document.querySelectorAll('a.taglink')  // Tags

// User info
article.querySelector('a[href*="space-uid-"]')  // Username link

// Post content
article.querySelector('.t_f, .pcb, [id^="postmessage_"]')

// Reactions
article.querySelector('a[href*="recommend&do=add"]')  // Likes
article.querySelector('[id^="reaction-"]')  // Emoji reactions

// Timestamps
article.querySelector('em[id^="authorposton"]')
```

### Data Extraction Process

1. **Extract Metadata:** Thread title, tags from navigation/header elements
2. **Find Post Containers:** Select all elements with `id` starting with "postnum"
3. **Extract Each Post:**
   - User info (username, ID, stats)
   - Post content
   - Timestamp
   - Reactions (likes, dislikes, emoji)
   - Quoted content
4. **Separate Main Post:** First post is treated as main post
5. **Return Structured Data:** JSON format with metadata

---

## Testing

### Test Files

1. **test/test_1point3acres_real.py** - Real browser test using Playwright
   - Loads HTML file in browser
   - Executes extraction JavaScript
   - Validates output structure

### Running Tests

```bash
# With Playwright (recommended)
python test/test_1point3acres_real.py

# Install Playwright if needed
pip install playwright
playwright install chromium
```

### Test Output

```
================================================================================
1POINT3ACRES PARSER - REAL BROWSER TEST
================================================================================

✓ Found HTML file: test/002_sanitized.html
Starting browser...
✓ Page loaded

Executing parser JavaScript...

Total posts found: 9
MAIN POST: ...
REPLIES: 8 total

================================================================================
✓ TEST PASSED
================================================================================
```

---

## Important Notes

### Sanitized HTML vs Real Pages

⚠️ **The parser is designed for REAL 1point3acres web pages, not sanitized HTML.**

The test file `002_sanitized.html` has been processed by `HTMLSanitizer`, which:
- Strips away most DOM structure
- Removes non-interactive elements
- Flattens the HTML into a stream of links and buttons

This makes it difficult to extract full post content from the sanitized HTML. The parser works best when:

✅ **Use with real pages:**
```python
navigate("https://www.1point3acres.com/bbs/thread-1157833-1-1.html")
parse_page_with_special_parser()  # Full content extracted
```

❌ **Limited results with sanitized HTML:**
- Post IDs extracted correctly  ✓
- User info may be incomplete  ⚠️
- Post content may be empty  ⚠️
- Structure metadata still works  ✓

### Browser Support

- Chrome MCP: ✅ Supported
- Playwright MCP: ✅ Supported

### Validation

The parser validates URLs before execution:

```python
def validate_page(self, browser_client) -> bool:
    url = browser_client.get_current_url()
    return '1point3acres.com' in url or '1point3acres' in url
```

---

## Future Enhancements

### Potential Improvements

1. **Pagination Support**
   - Auto-detect and parse multiple pages
   - Combine results from all pages

2. **Content Filtering**
   - Extract only posts by specific users
   - Filter by date range
   - Filter by reaction counts

3. **Media Extraction**
   - Extract images from posts
   - Download attachments
   - Capture embedded videos

4. **Enhanced Metadata**
   - View counts
   - Forum category info
   - Related threads

5. **Export Formats**
   - CSV export for analysis
   - Markdown format for documentation
   - Database storage

---

## Troubleshooting

### Empty Content

**Problem:** Extracted posts have empty content

**Causes:**
1. Using sanitized HTML instead of real page
2. CSS selectors don't match forum structure
3. Content loaded dynamically after page load

**Solutions:**
1. Navigate to real 1point3acres.com URLs
2. Wait for page to fully load (increase `wait_seconds`)
3. Check browser console for JavaScript errors

### No Posts Found

**Problem:** `total_posts: 0`

**Causes:**
1. Not on a thread page
2. Thread requires login
3. Page structure changed

**Solutions:**
1. Ensure URL is a thread URL (e.g., `thread-XXXXX-1-1.html`)
2. Log in to 1point3acres if needed
3. Update selectors in parser if forum structure changed

### Parser Not Auto-Detected

**Problem:** "No parser available for URL"

**Causes:**
1. URL doesn't match pattern `1point3acres.com`
2. Using localhost/file:// URL

**Solutions:**
1. Use explicit parser name: `parser_name="1point3acres"`
2. Navigate to actual 1point3acres.com domain

---

## Example Workflow

### Complete Example: Extract Interview Experiences

```python
# Step 1: Navigate to thread
navigate(
    url="https://www.1point3acres.com/bbs/thread-1157833-1-1.html",
    wait_seconds=3.0
)

# Step 2: Wait for page to fully load
wait_for_page(seconds=2.0)

# Step 3: Optional - scroll to load lazy content
scroll_down(times=3)

# Step 4: Extract structured data
result = parse_page_with_special_parser(
    parser_name="auto",
    save_results=True
)

# Result saved to:
# downloads/sessions/{session_id}/parsed_results/1point3acres/{timestamp}_{thread_id}.json
```

### Result File Location

```
downloads/
└── sessions/
    └── session_20251229_103000/
        └── parsed_results/
            └── 1point3acres/
                └── 20251229_105030_thread_1157833.json
```

---

## Integration with Workflow

### Use in Data Analysis Pipeline

1. **Extract:** Use parser to collect forum posts
2. **Transform:** Process JSON into database records
3. **Analyze:** Sentiment analysis, topic modeling, etc.
4. **Visualize:** Create dashboards, reports

### Batch Processing

```python
# Process multiple threads
thread_ids = [1157833, 1157829, 1157837]

for tid in thread_ids:
    navigate(f"https://www.1point3acres.com/bbs/thread-{tid}-1-1.html")
    parse_page_with_special_parser()
    # Results auto-saved to session folder
```

---

## Summary

✅ **Parser implemented** - Follows BaseParser architecture
✅ **Registered in registry** - Auto-detected for 1point3acres.com URLs
✅ **Tested** - Validated with Playwright browser tests
✅ **Documented** - Full usage guide and examples

**Ready for use** with real 1point3acres.com forum pages!

---

## Related Files

- **Parser:** `src/special_parsers/onepoint3acres.py`
- **Registry:** `src/special_parsers/__init__.py`
- **Tests:** `test/test_1point3acres_real.py`
- **Test Data:** `test/002_sanitized.html`
- **Test Output:** `test/test_1point3acres_real_output.json`
- **Design Doc:** `doc/SPECIAL_PARSER_DESIGN.md`
