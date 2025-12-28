# Debug Mode Usage Guide

## Overview

The Interactive Web Agent MCP now includes a comprehensive debug mode that tracks all operations and saves HTML snapshots for troubleshooting and analysis.

## Enabling Debug Mode

Set the `DEBUG_MODE` environment variable to enable debug logging:

```bash
export DEBUG_MODE=true
export DOWNLOADS_DIR=./downloads  # Optional, default: ./downloads
export SESSION_TIMEOUT_SECONDS=60  # Optional, default: 60
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG_MODE` | `false` | Enable/disable debug mode |
| `DOWNLOADS_DIR` | `./downloads` | Base directory for downloads and sessions |
| `SESSION_TIMEOUT_SECONDS` | `60` | Timeout between operations to start new session |

## Session Management

### What is a Session?

A **session** is a series of operations where consecutive operations occur within the timeout period (default: 60 seconds). If you wait more than 60 seconds between operations, a new session will be created.

### Session ID Format

Session IDs follow the pattern: `{8-char-uuid}_{YYYYMMDDHHmmss}`

Example: `abc12345_20250127103045`

- First part: 8-character UUID for uniqueness
- Second part: Timestamp of first operation in the session

## Directory Structure

When debug mode is enabled, the following structure is created:

```
downloads/
└── sessions/
    ├── session_manager.json          # Global session tracker
    └── abc12345_20250127103045/      # Session directory
        ├── session.json              # Session metadata
        ├── operations.jsonl          # Operation history (one JSON per line)
        └── html/                     # HTML snapshots
            ├── 001_raw.html          # Raw HTML from browser
            ├── 001_sanitized.html    # Sanitized HTML
            ├── 002_raw.html
            └── 002_sanitized.html
```

## Session Manager File

The `session_manager.json` file tracks all sessions:

```json
{
  "current_session_id": "abc12345_20250127103045",
  "last_operation_time": "2025-01-27T10:35:22.123456",
  "sessions": {
    "abc12345_20250127103045": {
      "created_at": "2025-01-27T10:30:45.000000",
      "last_operation_at": "2025-01-27T10:35:22.123456",
      "operation_count": 5,
      "status": "active"
    }
  }
}
```

## Session Metadata File

Each session has a `session.json` file with metadata:

```json
{
  "session_id": "abc12345_20250127103045",
  "created_at": "2025-01-27T10:30:45.000000",
  "last_operation_at": "2025-01-27T10:35:22.123456",
  "operation_count": 5,
  "status": "active",
  "initial_url": "https://example.com",
  "environment": {
    "python_version": "3.11.0",
    "platform": "Linux",
    "platform_release": "6.14.0-37-generic"
  }
}
```

## Operations Log

The `operations.jsonl` file contains one JSON object per line, representing each operation:

### Navigate Operation
```json
{
  "seq": 1,
  "timestamp": "2025-01-27T10:30:45.123",
  "operation": "navigate",
  "input": {
    "url": "https://example.com",
    "wait_seconds": 2.0
  },
  "output": {
    "success": true,
    "url": "https://example.com",
    "title": "Example Domain"
  },
  "duration_ms": 1234.56
}
```

### Get Page Content Operation
```json
{
  "seq": 2,
  "timestamp": "2025-01-27T10:30:48.456",
  "operation": "get_page_content",
  "input": {
    "format": "indexed"
  },
  "output": {
    "url": "https://example.com",
    "title": "Example Domain",
    "element_count": 50
  },
  "html_files": {
    "raw": "html/002_raw.html",
    "sanitized": "html/002_sanitized.html"
  },
  "duration_ms": 567.89
}
```

### Click Element Operation
```json
{
  "seq": 3,
  "timestamp": "2025-01-27T10:31:05.789",
  "operation": "click_element",
  "input": {
    "web_agent_id": "wa-15",
    "wait_after": 1.0
  },
  "output": {
    "success": true,
    "element_text": "Next Page",
    "new_url": "https://example.com/page2"
  },
  "duration_ms": 890.12
}
```

## HTML Snapshots

For every `get_page_content` operation, two HTML files are saved:

1. **Raw HTML** (`{seq}_raw.html`): Exact HTML from the browser
2. **Sanitized HTML** (`{seq}_sanitized.html`): Processed HTML with web-agent-id attributes

### Naming Convention

- Format: `{seq_number:03d}_{type}.html`
- Examples:
  - `001_raw.html` - First operation's raw HTML
  - `001_sanitized.html` - First operation's sanitized HTML
  - `002_raw.html` - Second operation's raw HTML
  - `002_sanitized.html` - Second operation's sanitized HTML

## Example Usage

### Basic Usage

```bash
# Enable debug mode
export DEBUG_MODE=true

# Run your MCP operations as normal
# The system will automatically track everything
```

### Inspecting Session Data

```bash
# View session manager
cat downloads/sessions/session_manager.json | jq

# List all sessions
ls -la downloads/sessions/

# View specific session metadata
cat downloads/sessions/abc12345_20250127103045/session.json | jq

# View operations (pretty print with jq)
cat downloads/sessions/abc12345_20250127103045/operations.jsonl | jq

# View specific operation
cat downloads/sessions/abc12345_20250127103045/operations.jsonl | jq 'select(.seq == 2)'

# View HTML snapshot
open downloads/sessions/abc12345_20250127103045/html/001_raw.html
```

### Analyzing Operations

```bash
# Count operations
wc -l downloads/sessions/abc12345_20250127103045/operations.jsonl

# Get average operation duration
cat downloads/sessions/abc12345_20250127103045/operations.jsonl | \
  jq '.duration_ms' | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count, "ms"}'

# Find failed operations
cat downloads/sessions/abc12345_20250127103045/operations.jsonl | \
  jq 'select(.output.success == false)'

# List all URLs visited
cat downloads/sessions/abc12345_20250127103045/operations.jsonl | \
  jq -r 'select(.operation == "navigate") | .input.url'
```

## Performance Impact

Debug mode has minimal performance impact:

- **Overhead**: ~5-10ms per operation for logging
- **Disk I/O**: Async file writes don't block operations
- **Memory**: Negligible (operations logged immediately)

For most use cases, the overhead is negligible. Only disable debug mode if:
- Disk space is critically low
- Maximum performance is required
- You're processing hundreds of pages per minute

## Security Considerations

### Sensitive Data Warning

⚠️ **Warning**: Debug mode may capture sensitive information in HTML snapshots:
- Form data (passwords, credit cards)
- Session tokens
- Personal information
- API keys in page content

**Best Practices:**
1. Never commit session directories to git
2. Review HTML files before sharing
3. Use appropriate file permissions (600)
4. Delete sessions after debugging

### File Permissions

Session directories are created with default permissions. For sensitive data:

```bash
# Restrict access to session directory
chmod 700 downloads/sessions/abc12345_20250127103045/
chmod 600 downloads/sessions/abc12345_20250127103045/*
```

## Troubleshooting

### Debug Mode Not Working

Check if environment variable is set:
```bash
echo $DEBUG_MODE
```

Ensure it's set to a truthy value: `true`, `1`, `yes`

### Session Files Not Created

1. Check DOWNLOADS_DIR exists and is writable
2. Verify no file permission issues
3. Check disk space is available

### Session Not Continuing

If a new session starts unexpectedly:
- Check if timeout exceeded (default: 60 seconds)
- Verify `session_manager.json` exists and is readable
- Adjust `SESSION_TIMEOUT_SECONDS` if needed

### File Locking Issues

On some systems, file locking may fail gracefully:
- Operations will continue without locking
- Warning message will be printed
- No impact on functionality

## Cleanup

### Manual Cleanup

```bash
# Remove all sessions
rm -rf downloads/sessions/

# Remove specific session
rm -rf downloads/sessions/abc12345_20250127103045/

# Remove sessions older than 7 days
find downloads/sessions/ -type d -mtime +7 -exec rm -rf {} +
```

### Automated Cleanup (Future)

The `MAX_SESSIONS` configuration will enable automatic cleanup of old sessions.

## Advanced Usage

### Session Replay (Future Feature)

```bash
# Replay operations from a session
python tools/replay_session.py downloads/sessions/abc12345_20250127103045/
```

### HTML Diff (Future Feature)

```bash
# Compare HTML snapshots
python tools/html_diff.py \
  downloads/sessions/abc12345_20250127103045/html/001_sanitized.html \
  downloads/sessions/abc12345_20250127103045/html/002_sanitized.html
```

## FAQ

**Q: Does debug mode slow down operations?**
A: Minimal impact (5-10ms per operation). HTML saving is async.

**Q: How much disk space do sessions use?**
A: Depends on HTML size. Typical session: 1-10 MB. Large pages: up to 50 MB.

**Q: Can I use debug mode in production?**
A: Not recommended. Use only for debugging and development.

**Q: How do I share session data with support?**
A: Zip the session directory, but review for sensitive data first.

**Q: Can multiple MCP instances share sessions?**
A: Yes, file locking ensures safe concurrent access.

**Q: What happens if disk is full?**
A: Operations continue, but debug logging is disabled automatically.

## Related Files

- Design document: `doc/debug_mode_design.md`
- Session manager: `src/session_manager.py`
- Debug logger: `src/debug_logger.py`
- Main MCP: `src/interactive_web_agent_mcp.py`
