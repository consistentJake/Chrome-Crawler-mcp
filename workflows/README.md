# WebAgent Workflows

Automated workflows for web scraping using the interactive web agent infrastructure.

## Quick Start

### Option 1: Simple Command Line

```bash
cd /home/zhenkai/personal/Projects/WebAgent/workflows

# Scrape all posts from page 2
python run_scraper.py "https://www.1point3acres.com/bbs/tag-9407-2.html" --all

# Scrape first 5 posts from 3 pages
python run_scraper.py "https://www.1point3acres.com/bbs/tag-9407-1.html" --pages 3 --posts 5
```

### Option 2: Using the onepoint3acres_workflow.py directly

```bash
python onepoint3acres_workflow.py \
    --url "https://www.1point3acres.com/bbs/tag-9407-2.html" \
    --pages 1 \
    --posts 0 \
    --output ./output
```

Note: `--posts 0` means "scrape all posts"

### Option 3: Python Script

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/home/zhenkai/personal/Projects/WebAgent/workflows")
sys.path.insert(0, "/home/zhenkai/personal/Projects/WebAgent/src")
sys.path.insert(0, "/home/zhenkai/personal/Projects/WebAgent/helper")
sys.path.insert(0, "/home/zhenkai/personal/Projects/WebAgent")

from onepoint3acres_workflow import scrape_1point3acres

result = scrape_1point3acres(
    url="https://www.1point3acres.com/bbs/tag-9407-2.html",
    num_pages=1,
    posts_per_page=None,  # None = all posts
    output_dir="./my_output",
    verbose=True
)

print(f"Success: {result.success}")
print(f"Posts parsed: {result.summary['posts_successfully_parsed']}")
```

## Features

✅ **No LLM Required** - Pure Python automation
✅ **Multi-page Support** - Scrape across multiple pages with pagination
✅ **Auto Page Detection** - Automatically detects page number from URL
✅ **Resume Support** - Resume from specific page/post if interrupted
✅ **Verification** - Built-in verification for URL, content, element counts
✅ **Structured Output** - Individual JSON files + combined results
✅ **Special Parser** - Uses 1point3acres parser for structured data extraction

## Output Structure

```
output/
├── combined_results_TIMESTAMP.json    # All posts combined
└── posts/
    ├── post_THREADID_TIMESTAMP.json
    ├── post_THREADID_TIMESTAMP.json
    └── ...
```

## Configuration Options

### run_scraper.py Options

```
--url       URL to scrape (required)
--pages     Number of pages to scrape (default: 1)
--posts     Posts per page to parse (default: all)
--all       Parse all posts (explicit flag)
--output    Output directory (default: ./scraper_output)
--quiet     Suppress progress output
--wait-page Wait time after page load in seconds (default: 3.0)
--wait-post Wait time between posts in seconds (default: 1.5)
```

### Advanced Configuration (Python API)

```python
from onepoint3acres_workflow import OnePoint3AcresWorkflow, OnePoint3AcresConfig

config = OnePoint3AcresConfig(
    base_url="https://www.1point3acres.com/bbs/tag-9407-1.html",
    num_pages=2,                   # Scrape 2 pages
    posts_per_page=10,             # 10 posts per page (None = all)

    # Timing settings
    page_load_wait=3.0,            # Wait after page load
    between_posts_wait=1.5,        # Wait between posts
    between_pages_wait=2.0,        # Wait between pages

    # Verification
    min_posts_per_page=1,          # Minimum expected posts
    verify_post_content=True,      # Verify content extraction

    # Output
    save_individual_posts=True,    # Save each post separately
    save_combined_results=True     # Save combined file
)

workflow = OnePoint3AcresWorkflow(
    config=config,
    client_type="chrome",          # Use Chrome MCP
    output_dir="./custom_output",
    verbose=True
)

result = workflow.run(
    start_page=2,                  # Override URL page number
    resume_from_post=5             # Skip first 5 posts
)
```

## Examples

### Example 1: Scrape Multiple Pages

```bash
python run_scraper.py \
    "https://www.1point3acres.com/bbs/tag-9407-1.html" \
    --pages 5 \
    --all
```

python run_scraper.py \
    "https://www.1point3acres.com/bbs/tag/anthropic-9878-1.html" \
    --pages 16 \
    --posts -1

### Example 2: Scrape Specific Posts

```bash
python run_scraper.py \
    "https://www.1point3acres.com/bbs/tag-9407-1.html" \
    --pages 1 \
    --posts 3
```

### Example 3: Scrape with Custom Wait Times

```bash
python run_scraper.py \
    "https://www.1point3acres.com/bbs/tag-9407-1.html" \
    --all \
    --wait-page 5.0 \
    --wait-post 2.0
```

### Example 4: Resume from Failure

```python
# If workflow failed on page 2, post 3:
result = workflow.run(
    start_page=2,
    resume_from_post=3
)
```

## Prerequisites

1. **Chrome Browser** must be running
2. **Chrome MCP Server** must be accessible
3. **Python 3.7+** with required dependencies

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'helper'"

Make sure you're running from the workflows directory or have the correct paths in sys.path.

### Issue: "Chrome MCP server not found"

Check that the Chrome MCP server path is correct in `src/browser_integration.py`.

### Issue: Workflow scraped wrong page

The workflow now auto-detects the page number from the URL. If you provide `tag-9407-2.html`, it will start from page 2.

## Extending the Workflow

To create a new workflow for a different website:

1. Create a new file: `workflows/my_site_workflow.py`
2. Inherit from `BaseWorkflow`
3. Implement the `run()` method
4. Use the base operations: `navigate()`, `get_page_content()`, `query_elements()`, `parse_page_with_parser()`

```python
from base_workflow import BaseWorkflow, WorkflowResult

class MySiteWorkflow(BaseWorkflow):
    @property
    def name(self) -> str:
        return "my_site_scraper"

    def run(self, **kwargs) -> WorkflowResult:
        # Your workflow logic here
        pass
```

## Testing

```bash
# Test import
python -c "from onepoint3acres_workflow import scrape_1point3acres; print('✅ Import OK')"

# Test with minimal posts
python run_scraper.py "https://www.1point3acres.com/bbs/tag-9407-1.html" --posts 2
```

## License

MIT License - See project root for details.
