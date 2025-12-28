# Interactive Web Agent MCP - Debug Mode Design

## Overview
Add comprehensive debug mode to track all operations and HTML snapshots for troubleshooting and analysis.

## Requirements

### 1. Configuration
- Add `DEBUG_MODE` environment variable (default: `false`)
- When enabled, track all operations and save HTML snapshots

### 2. Session Management
- **Session Definition**: A series of operations where consecutive operations have < 60 seconds interval
- **Session Storage**: `DOWNLOADS_DIR/sessions/`
- **Session ID Format**: `{8-char-uuid}_{YYYYMMDDHHmmss}` (timestamp of first operation)
- **Session Tracking**: Use `session_manager.json` with file locking for concurrent access

### 3. Session Directory Structure
```
DOWNLOADS_DIR/
└── sessions/
    ├── session_manager.json          # Tracks active/recent sessions
    └── abc12345_20250127103045/      # Session folder
        ├── session.json              # Session metadata
        ├── operations.jsonl          # Operation history (JSON Lines)
        ├── html/                     # HTML snapshots
        │   ├── 001_raw.html          # Raw HTML from browser
        │   ├── 001_sanitized.html    # Sanitized HTML
        │   ├── 002_raw.html
        │   └── 002_sanitized.html
        └── screenshots/              # Optional: future enhancement
```

### 4. Session Manager File (`session_manager.json`)
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

### 5. Session Metadata (`session.json`)
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
    "platform": "linux"
  }
}
```

### 6. Operation History (`operations.jsonl`)
Each line is a JSON object representing one operation:

```json
{"seq": 1, "timestamp": "2025-01-27T10:30:45.123", "operation": "navigate", "input": {"url": "https://example.com", "wait_seconds": 2.0}, "output": {"success": true, "url": "https://example.com"}, "duration_ms": 1234}
{"seq": 2, "timestamp": "2025-01-27T10:30:48.456", "operation": "get_page_content", "input": {"format": "indexed"}, "output": {"success": true, "element_count": 50}, "html_files": {"raw": "html/002_raw.html", "sanitized": "html/002_sanitized.html"}, "duration_ms": 567}
{"seq": 3, "timestamp": "2025-01-27T10:31:05.789", "operation": "click_element", "input": {"web_agent_id": "wa-15", "wait_after": 1.0}, "output": {"success": true, "new_url": "https://example.com/page2"}, "duration_ms": 890}
```

### 7. HTML Snapshot Naming
- Format: `{seq_number:03d}_{type}.html`
- Examples:
  - `001_raw.html` - Raw HTML from browser (operation 1)
  - `001_sanitized.html` - Sanitized HTML (operation 1)
  - `002_raw.html` - Raw HTML from browser (operation 2)
  - `002_sanitized.html` - Sanitized HTML (operation 2)

## Implementation Plan

### Phase 1: Core Infrastructure
1. **Session Manager Class** (`session_manager.py`)
   - Create/resume sessions based on time gap
   - Thread-safe file locking using `fcntl` (Linux/Mac) or `msvcrt` (Windows)
   - Session lifecycle management

2. **Debug Logger Class** (`debug_logger.py`)
   - Log operations to JSONL file
   - Save HTML snapshots
   - Track operation metadata

### Phase 2: Integration
1. **Modify `interactive_web_agent_mcp.py`**
   - Add debug mode detection (environment variable)
   - Initialize SessionManager if debug mode enabled
   - Wrap each tool call with debug logging

2. **Operation Tracking**
   - Before operation: Log input parameters
   - After operation: Log output, duration, status
   - For `get_page_content`: Save raw + sanitized HTML

### Phase 3: Utilities
1. **Session Viewer** (Future enhancement)
   - CLI tool to view session history
   - Replay operations
   - Compare HTML snapshots

## Key Design Decisions

### 1. File Locking Strategy
- Use platform-specific locking (fcntl/msvcrt)
- Timeout-based lock acquisition (5 seconds)
- Graceful fallback if lock fails

### 2. Session Timeout
- 60 seconds between operations
- Configurable via environment variable `SESSION_TIMEOUT_SECONDS`

### 3. HTML Storage Optimization
- Store both raw and sanitized HTML for complete debugging
- Use relative paths in operations.jsonl
- Consider compression for large HTML files (future)

### 4. Performance Impact
- Minimal: Only enabled when DEBUG_MODE=true
- Async file I/O to avoid blocking operations
- Background thread for HTML writing (optional optimization)

## Configuration Variables

```bash
# Enable debug mode
DEBUG_MODE=true

# Session timeout in seconds (default: 60)
SESSION_TIMEOUT_SECONDS=60

# Downloads directory (existing)
DOWNLOADS_DIR=./downloads

# Max sessions to keep (future: auto-cleanup old sessions)
MAX_SESSIONS=100
```

## Error Handling

1. **Session Manager Unavailable**
   - Log warning
   - Continue operation without debug logging
   - Don't fail the actual operation

2. **Disk Space Issues**
   - Monitor available space
   - Warn when < 100MB available
   - Disable debug mode automatically if critical

3. **Lock Timeout**
   - Log warning
   - Skip debug logging for this operation
   - Continue with actual operation

## Testing Strategy

1. **Unit Tests**
   - SessionManager: create, resume, timeout
   - DebugLogger: JSONL writing, HTML storage
   - File locking: concurrent access

2. **Integration Tests**
   - Full workflow with debug mode enabled
   - Session continuity across operations
   - HTML snapshot correctness

3. **Performance Tests**
   - Measure overhead with debug mode on/off
   - Large HTML files (>10MB)
   - Concurrent MCP instances

## Future Enhancements

1. **Session Replay**
   - Replay recorded operations
   - Compare results with original

2. **HTML Diffing**
   - Visual diff between HTML snapshots
   - Highlight changes after interactions

3. **Screenshots**
   - Capture screenshots for each operation
   - Store in `screenshots/` subdirectory

4. **Session Analytics**
   - Statistics on operation types
   - Performance metrics
   - Error patterns

5. **Web UI**
   - Browse sessions via web interface
   - Visual timeline of operations
   - Interactive HTML comparison

## Implementation Checklist

- [ ] Create `session_manager.py`
- [ ] Create `debug_logger.py`
- [ ] Add environment variable detection
- [ ] Integrate with existing tool calls
- [ ] Add HTML snapshot saving for `get_page_content`
- [ ] Implement file locking (cross-platform)
- [ ] Add error handling and fallbacks
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Update documentation
- [ ] Add example session output to docs

## Example Usage

```bash
# Enable debug mode
export DEBUG_MODE=true
export DOWNLOADS_DIR=./downloads

# Run MCP server (operations will be logged)
python src/interactive_web_agent_mcp.py

# After operations, inspect session
ls -la downloads/sessions/abc12345_20250127103045/
# View operations
cat downloads/sessions/abc12345_20250127103045/operations.jsonl | jq
# View HTML snapshot
open downloads/sessions/abc12345_20250127103045/html/001_raw.html
```

## Security Considerations

1. **Sensitive Data in HTML**
   - Debug mode may capture sensitive form data
   - User should be aware when enabling
   - Add warning in documentation

2. **Disk Space**
   - HTML files can be large
   - Implement cleanup policy
   - Monitor disk usage

3. **Session Data Access**
   - Session files may contain private browsing data
   - Ensure proper file permissions (600)
   - Don't commit session data to git

## Documentation Updates

1. Update README.md with debug mode instructions
2. Add troubleshooting guide using session logs
3. Document session file format for external tools
4. Add privacy/security notice about debug mode
