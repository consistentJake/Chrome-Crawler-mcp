# Interactive Web Agent MCP Server Configuration

## Controlling Output and Logging

By default, the MCP server **does not save any outputs to disk** to prevent storage bloat when integrated into projects. You can enable logging and output saving using environment variables.

## Environment Variables

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_LOGGING` | `false` | **Master switch** for all output saving (downloads, parsed results, debug logs) |
| `DEBUG_MODE` | `false` | Enable detailed session logging (only works if `ENABLE_LOGGING=true`) |
| `DOWNLOADS_DIR` | `./downloads` | Base directory for all outputs |
| `MCP_CLIENT_TYPE` | `chrome` | Browser client type: `chrome` or `playwright` |
| `BROWSER_APP_NAME` | `Google Chrome` | Browser application name for PyAutoGUI scrolling |
| `SESSION_TIMEOUT_SECONDS` | `60` | Session timeout in seconds (only for DEBUG_MODE) |

## Folder Structure

### When `ENABLE_LOGGING=false` (Default)
- No folders are created
- No outputs are saved to disk
- `download_page()` will return an error
- `parse_page_with_special_parser()` will parse but not save results

### When `ENABLE_LOGGING=true` and `DEBUG_MODE=false`
```
./downloads/
  page_example_com_20260124_123456.html
  page_twitter_com_20260124_123500.html
  parsed_results/
    x.com/
      20260124_123500_search_query.json
    1point3acres/
      20260124_123600_thread_title.json
    linkedin-jobs/
      20260124_123700_software_engineer.json
```

### When `ENABLE_LOGGING=true` and `DEBUG_MODE=true`
```
./downloads/
  sessions/
    session_20260124_123000/
      operations.jsonl              # Operation logs
      html_snapshots/               # HTML snapshots for debugging
        navigate_001.html
        get_page_content_002.html
      downloads/                    # Page downloads
        page_example_com_20260124_123456.html
      parsed_results/               # Parsed structured data
        x.com/
          20260124_123500_search_query.json
```

## MCP Server Configuration Examples

### Example 1: Minimal (No Logging)
Use this configuration when you want to browse and interact with web pages but **don't need to save any outputs**.

```json
{
  "mcpServers": {
    "interactive-web-agent": {
      "command": "python",
      "args": ["/path/to/WebAgent/src/interactive_web_agent_mcp.py"],
      "env": {
        "ENABLE_LOGGING": "false",
        "MCP_CLIENT_TYPE": "chrome"
      }
    }
  }
}
```

**Use cases:**
- General web browsing and interaction
- Form filling and automation
- Navigation and element querying
- When disk space is limited

### Example 2: With Logging (Save Downloads and Parsed Results)
Use this when you want to **save downloaded pages and parsed data** but don't need detailed debug logs.

```json
{
  "mcpServers": {
    "interactive-web-agent": {
      "command": "python",
      "args": ["/path/to/WebAgent/src/interactive_web_agent_mcp.py"],
      "env": {
        "ENABLE_LOGGING": "true",
        "DEBUG_MODE": "false",
        "DOWNLOADS_DIR": "./web_agent_outputs",
        "MCP_CLIENT_TYPE": "chrome"
      }
    }
  }
}
```

**Use cases:**
- Scraping and saving web pages
- Extracting structured data (tweets, jobs, forum posts)
- Building datasets from web content
- Archiving web content

### Example 3: Full Debug Mode
Use this for **development, debugging, or troubleshooting** when you need detailed operation logs and HTML snapshots.

```json
{
  "mcpServers": {
    "interactive-web-agent": {
      "command": "python",
      "args": ["/path/to/WebAgent/src/interactive_web_agent_mcp.py"],
      "env": {
        "ENABLE_LOGGING": "true",
        "DEBUG_MODE": "true",
        "DOWNLOADS_DIR": "./debug_outputs",
        "SESSION_TIMEOUT_SECONDS": "300",
        "MCP_CLIENT_TYPE": "chrome"
      }
    }
  }
}
```

**Use cases:**
- Debugging MCP server issues
- Understanding operation flow
- Analyzing page snapshots at each step
- Development and testing

## Managing Multiple Configurations

You can define multiple server instances with different configurations:

```json
{
  "mcpServers": {
    "web-agent-browsing": {
      "command": "python",
      "args": ["/path/to/WebAgent/src/interactive_web_agent_mcp.py"],
      "env": {
        "ENABLE_LOGGING": "false",
        "MCP_CLIENT_TYPE": "chrome"
      }
    },
    "web-agent-scraping": {
      "command": "python",
      "args": ["/path/to/WebAgent/src/interactive_web_agent_mcp.py"],
      "env": {
        "ENABLE_LOGGING": "true",
        "DEBUG_MODE": "false",
        "DOWNLOADS_DIR": "./scraped_data",
        "MCP_CLIENT_TYPE": "chrome"
      }
    }
  }
}
```

Then use `web-agent-browsing` for general browsing and `web-agent-scraping` when you need to save outputs.

## Disk Space Considerations

### Storage Impact by Mode

| Mode | Typical Storage per Operation | Storage Impact |
|------|------------------------------|----------------|
| `ENABLE_LOGGING=false` | 0 bytes | None - nothing saved |
| `ENABLE_LOGGING=true`, `DEBUG_MODE=false` | 50-500 KB per download | Low - only saved pages |
| `ENABLE_LOGGING=true`, `DEBUG_MODE=true` | 100-1000 KB per operation | High - all HTML snapshots + logs |

### Recommendations

1. **Default (No Logging)**: Use for most projects to avoid disk bloat
2. **Logging Enabled**: Only enable when you need to save outputs
3. **Debug Mode**: Only use temporarily for debugging, then disable
4. **Clean Up**: Periodically delete old session folders if using DEBUG_MODE

## Example Usage in Projects

### Add to Claude Code MCP Config

On macOS/Linux, add to `~/.config/claude-code/mcp.json`:

```json
{
  "mcpServers": {
    "interactive-web-agent": {
      "command": "python",
      "args": ["/absolute/path/to/WebAgent/src/interactive_web_agent_mcp.py"],
      "env": {
        "ENABLE_LOGGING": "false"
      }
    }
  }
}
```

### Temporarily Enable Logging

When you need to save outputs for a specific task, edit the config:

```json
"env": {
  "ENABLE_LOGGING": "true",
  "DOWNLOADS_DIR": "/tmp/web_scraping"
}
```

Then restart the Claude Code MCP server to apply changes.

## Checking Current Configuration

When the MCP server starts, it prints the current configuration:

```
[MCP CLIENT] Using chrome client
[LOGGING] Disabled - No outputs will be saved to disk
```

Or with logging enabled:

```
[MCP CLIENT] Using chrome client
[LOGGING] Enabled - Outputs will be saved to ./downloads
[DEBUG MODE] Enabled - Sessions will be saved to ./downloads/sessions/
```

## Troubleshooting

### "Download disabled: ENABLE_LOGGING=false"
This error occurs when calling `download_page()` with logging disabled. Set `ENABLE_LOGGING=true` to enable downloads.

### Disk space running out
1. Check if `DEBUG_MODE=true` - disable it if not needed
2. Set `ENABLE_LOGGING=false` if you don't need outputs
3. Periodically clean the `DOWNLOADS_DIR` folder

### Can't find downloaded files
1. Check the server startup message for the actual `DOWNLOADS_DIR` path
2. Ensure `ENABLE_LOGGING=true` is set
3. Check the file path returned in the tool response
