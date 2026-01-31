# WebAgent Workflows - Features Summary

## ✅ Speed Profiles

Control scraping speed with 4 built-in profiles:

| Profile | Page Load | Between Posts | Between Pages | Best For |
|---------|-----------|---------------|---------------|----------|
| **fast** | 1.5s | 0.5s | 1.0s | Quick testing, good connections |
| **normal** | 3.0s | 1.5s | 2.0s | Default, balanced speed |
| **slow** | 5.0s | 2.5s | 3.0s | Reliable scraping |
| **cautious** | 8.0s | 4.0s | 5.0s | Unstable/slow connections |

### Usage

**Command line:**
```bash
python run_scraper.py "URL" --speed fast
python run_scraper.py "URL" --speed slow
```

**Python API:**
```python
result = scrape_1point3acres(
    url="...",
    speed="fast"
)
```

**Config file:**
```json
{
  "speed": "fast"
}
```

## ✅ Configuration Files

Control everything from a single JSON file!

### Quick Start
```bash
python run_scraper.py --config config_examples/fast_scraping.json
```

### Config File Structure
```json
{
  "url": "https://www.1point3acres.com/bbs/tag-9407-1.html",
  "num_pages": 2,
  "posts_per_page": null,
  "speed": "fast",
  "output": {
    "directory": "./my_output",
    "save_individual_posts": true,
    "save_combined_results": true
  },
  "verification": {
    "min_posts_per_page": 1,
    "verify_post_content": true
  },
  "runtime": {
    "verbose": true,
    "client_type": "chrome"
  }
}
```

### Available Config Examples

All in `config_examples/` directory:

1. **fast_scraping.json** - Quick scraping
2. **slow_reliable.json** - Slow, reliable scraping
3. **custom_waits.json** - Custom wait times
4. **resume_from_failure.json** - Resume from specific page/post

## ✅ Custom Wait Times

Override speed profiles with custom wait times:

```json
{
  "custom_waits": {
    "enabled": true,
    "page_load_wait": 4.0,
    "between_posts_wait": 2.0,
    "between_pages_wait": 2.5
  }
}
```

## ✅ Flexible Output Configuration

Control what gets saved:

```json
{
  "output": {
    "directory": "./custom_output",
    "save_individual_posts": true,   // Each post = separate JSON
    "save_combined_results": false   // Don't create combined file
  }
}
```

## ✅ Resume from Failure

Resume a failed scraping job:

```json
{
  "resume": {
    "enabled": true,
    "start_page": 3,       // Start from page 3
    "resume_from_post": 5  // Skip first 5 posts
  }
}
```

Or via Python:
```python
workflow.run(start_page=3, resume_from_post=5)
```

## ✅ Auto Page Number Detection

The workflow automatically detects the page number from your URL:

```bash
# This will scrape page 2
python run_scraper.py "https://www.1point3acres.com/bbs/tag-9407-2.html"

# This will scrape starting from page 5
python run_scraper.py "https://www.1point3acres.com/bbs/tag-9407-5.html" --pages 3
# (Scrapes pages 5, 6, 7)
```

## ✅ Verification System

Built-in verification for reliability:

- ✅ URL verification after navigation
- ✅ Minimum element count verification
- ✅ Expected element types verification
- ✅ Post content verification
- ✅ Minimum posts per page verification
- ✅ Structured verification results tracking

## Usage Comparison

### Command Line

```bash
# Simple
python run_scraper.py "URL" --all

# With speed
python run_scraper.py "URL" --speed fast --posts 5

# Multiple pages
python run_scraper.py "URL" --pages 3 --all --speed slow
```

### Config File (Recommended)

```bash
# One command, all settings in file
python run_scraper.py --config my_config.json
```

### Python API

```python
from onepoint3acres_workflow import scrape_1point3acres

result = scrape_1point3acres(
    url="https://www.1point3acres.com/bbs/tag-9407-1.html",
    num_pages=2,
    posts_per_page=5,
    speed="fast",
    output_dir="./output"
)
```

### Advanced Python API

```python
from onepoint3acres_workflow import (
    OnePoint3AcresWorkflow,
    OnePoint3AcresConfig
)

config = OnePoint3AcresConfig.from_speed_profile(
    base_url="...",
    speed="slow",
    num_pages=5,
    save_individual_posts=True
)

workflow = OnePoint3AcresWorkflow(
    config=config,
    output_dir="./output",
    verbose=True
)

result = workflow.run(start_page=2, resume_from_post=3)
```

## Performance Comparison

Based on scraping 10 posts from 1 page:

| Profile | Estimated Time | Use Case |
|---------|----------------|----------|
| Fast | ~21.5 seconds | Testing, good connection |
| Normal | ~48 seconds | Standard use |
| Slow | ~80 seconds | Reliability first |
| Cautious | ~128 seconds | Very slow/unstable connections |

## Examples

### Example 1: Quick Test
```bash
python run_scraper.py "URL" --speed fast --posts 2
```

### Example 2: Full Scraping
```json
// config.json
{
  "url": "https://www.1point3acres.com/bbs/tag-9407-1.html",
  "num_pages": 10,
  "posts_per_page": null,
  "speed": "normal",
  "output": {
    "directory": "./full_scrape"
  }
}
```
```bash
python run_scraper.py --config config.json
```

### Example 3: Resume After Failure
```bash
# First run failed on page 3, post 5
# Create resume config:
{
  "url": "...",
  "num_pages": 10,
  "resume": {
    "enabled": true,
    "start_page": 3,
    "resume_from_post": 5
  }
}

python run_scraper.py --config resume_config.json
```

## Tips

1. **Start small:** Test with 2 posts first
2. **Use config files:** Easier to track and reproduce
3. **Choose right speed:** Fast for testing, slow for production
4. **Monitor first run:** Adjust wait times if needed
5. **Enable resume:** For large scraping jobs
6. **Check output:** Verify JSON files are complete

## See Also

- `README.md` - Complete documentation
- `config_examples/README.md` - Config file documentation
- `examples/` - Python usage examples
