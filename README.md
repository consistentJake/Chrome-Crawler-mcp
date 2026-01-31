# WebAgent

A web automation and extraction toolkit for intelligent web scraping and LLM-based data extraction, powered by MCP (Model Context Protocol) servers.

## Features

- **Interactive Web Scraping**: Automate browser interactions with Chrome/Playwright
- **Intelligent Parsers**: Built-in parsers for Reddit, Twitter/X, LinkedIn Jobs, and 1point3acres
- **LLM Integration**: Extract structured data using Anthropic Claude or OpenAI models
- **MCP Server**: Use as a Model Context Protocol server with Claude Code or other MCP clients
- **Unified Pipeline**: Orchestrated scraping and extraction workflow

## Quick Start

### Prerequisites

```bash
# Core dependencies
pip install beautifulsoup4 lxml requests mcp pyyaml

# For LLM extraction
pip install anthropic openai

# For Chrome MCP integration
# Follow instructions at: https://github.com/hangwin/mcp-chrome
```

### MCP Server Setup

This project works as an MCP server that can be integrated with Claude Code or other MCP clients.

#### 1. Install Chrome Extension (Required for Chrome MCP)

Follow the instructions at [mcp-chrome](https://github.com/hangwin/mcp-chrome) to:
1. Clone the mcp-chrome repository
2. Install the Chrome extension from the `extension/` folder
3. Verify the extension is running (you should see the MCP icon in Chrome)

#### 2. Configure MCP Server

Add to your `~/.claude.json` or MCP client configuration:

```json
{
  "mcpServers": {
    "interactive-web-agent": {
      "command": "python3",
      "args": [
        "/path/to/WebAgent/src/interactive_web_agent_mcp.py"
      ],
      "env": {
        "DOWNLOADS_DIR": "/path/to/WebAgent/downloads",
        "PYTHONPATH": "/path/to/WebAgent",
        "DEBUG_MODE": "true",
        "ENABLE_LOGGING": "true"
      }
    },
    "chrome-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "@hangwin/mcp-chrome"
      ]
    }
  }
}
```

**Important**: Replace `/path/to/WebAgent` with your actual project path (e.g., `/home/user/Projects/WebAgent`)

#### 3. Start Using the MCP Server

Once configured, the server provides tools for:
- Browser navigation and interaction
- Page content extraction
- Special parsers for supported sites (Reddit, Twitter, LinkedIn, etc.)
- HTML sanitization and element detection
- Automated scrolling and tab management

## Project Structure

```
WebAgent/
├── main.py                 # Pipeline orchestrator (scrape + extract)
├── config.yaml             # Unified configuration file
├── shared/                 # Shared utilities
│   └── utils.py            # Common functions & UnifiedConfig
├── src/                    # Core MCP components
│   ├── interactive_web_agent_mcp.py  # Main MCP server
│   ├── html_sanitizer.py             # HTML processing
│   ├── browser_integration.py        # Browser control
│   └── special_parsers/              # Site-specific parsers
│       ├── reddit_parser.py
│       ├── x_parser.py
│       ├── linkedin_parser.py
│       └── onepoint3acres_parser.py
├── helper/                 # MCP client libraries
│   ├── ChromeMcpClient.py
│   ├── PlaywrightMcpClient.py
│   └── PyAutoGuiClient.py
├── workflows/              # Scraping workflows
│   ├── run_scraper.py      # Scraper CLI
│   ├── reddit_workflow.py
│   ├── base_workflow.py
│   └── config_loader.py
└── exploration/            # Experimental scrapers

downloads/sessions/         # Logs and downloaded pages (when ENABLE_LOGGING=true)
```

## Standalone Usage (Without MCP)

### Full Pipeline

Run both scraping and extraction with a single command:

```bash
# Use settings from config.yaml
python main.py

# Override URL and pages (example with Reddit)
python main.py --url "https://reddit.com/r/python" --pages 2

# Generate prompts only (no API calls)
python main.py --dump-prompt

# Scrape only, skip extraction
python main.py --scrape-only

# Extract only from existing scraper output
python main.py --extract-only ./scraper_output/combined_results_20250122_120000.json
```

### Configuration

Edit `config.yaml` (or create `config.local.yaml` for local overrides):

```yaml
# Scraper settings
scraper:
  url: "https://reddit.com/r/MachineLearning"
  num_pages: 2
  posts_per_page: 5
  speed: "normal"  # fast, normal, slow, cautious
  output:
    directory: "./scraper_output"

# Extraction settings
extraction:
  api:
    api_key: ""  # Use environment variable ANTHROPIC_API_KEY
    base_url: null  # null for official Anthropic API
    model: "claude-3-5-haiku-20241022"
  output:
    output_dir: "output"
    save_intermediate: true

# Pipeline settings
pipeline:
  dump_prompt_only: false
  auto_extract: true
```

### CLI Options

| Option | Description |
|--------|-------------|
| `-c, --config FILE` | Config file path |
| `--url URL` | Override scraper URL |
| `--pages N` | Number of pages to scrape |
| `--posts N` | Posts per page |
| `--max-posts N` | Max posts for extraction |
| `--scrape-only` | Only run scraper |
| `--extract-only FILE` | Only run extraction on file |
| `--dump-prompt` | Generate prompts without API calls |
| `-q, --quiet` | Suppress output |

## Individual Components

### Scraper Only

```bash
cd workflows

# Scrape Reddit subreddit
python run_scraper.py "https://reddit.com/r/python" --pages 2 --posts 10

# With speed profile
python run_scraper.py "URL" --speed fast --output ./output
```

## Output Structure

```
scraper_output/                      # Scraper output
├── combined_results_TIMESTAMP.json  # All posts combined
└── posts/
    └── post_THREADID_TIMESTAMP.json

output_TIMESTAMP/                    # Extraction output (timestamped)
├── extracted_data_*.json            # Final results
├── markdown/                        # Converted markdown
├── prompts/                         # LLM prompts (--dump-prompt)
└── responses/                       # Raw LLM responses
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `DOWNLOADS_DIR` | Directory for session logs | `./downloads` |
| `PYTHONPATH` | Python path for imports | - |
| `DEBUG_MODE` | Enable debug logging | `false` |
| `ENABLE_LOGGING` | Save session logs to disk | `false` |
| `MCP_CLIENT_TYPE` | MCP client type | `chrome` |

## Supported Sites

The interactive web agent includes special parsers for:

- **Reddit**: Subreddit listings and post pages
- **Twitter/X**: Search results, timelines, profiles
- **LinkedIn Jobs**: Job listings and search results
- **1point3acres**: Forum threads and posts

Use the `parse_page_with_special_parser` MCP tool to automatically extract structured data from these sites.

## Development

### Adding Custom Parsers

Create a new parser in `src/special_parsers/`:

```python
def parse_your_site(soup, url):
    """Extract structured data from your site"""
    results = []
    # Your parsing logic here
    return {
        'status': 'success',
        'item_count': len(results),
        'items': results
    }
```

Register it in `interactive_web_agent_mcp.py`.

## License

MIT License
