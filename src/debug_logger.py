#!/usr/bin/env python3
"""
Debug Logger for Interactive Web Agent MCP
Logs operations, inputs, outputs, and HTML snapshots to session directory.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class DebugLogger:
    """
    Logs debug information for web agent operations

    Stores:
    - Operation sequence in operations.jsonl
    - Raw and sanitized HTML snapshots
    - Operation timing and metadata
    """

    def __init__(self, session_dir: Path):
        """
        Initialize DebugLogger

        Args:
            session_dir: Session directory path
        """
        self.session_dir = Path(session_dir)
        self.html_dir = self.session_dir / "html"
        self.operations_file = self.session_dir / "operations.jsonl"

        # Ensure directories exist
        self.html_dir.mkdir(parents=True, exist_ok=True)

        # Track operation sequence number
        self.operation_seq = self._get_last_seq_number() + 1

    def _get_last_seq_number(self) -> int:
        """
        Get the last sequence number from operations.jsonl

        Returns:
            Last sequence number (0 if file empty/doesn't exist)
        """
        if not self.operations_file.exists():
            return 0

        try:
            with open(self.operations_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if not lines:
                    return 0

                # Get last line and parse seq number
                last_line = lines[-1].strip()
                if last_line:
                    data = json.loads(last_line)
                    return data.get("seq", 0)
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            pass

        return 0

    def log_operation(
        self,
        operation: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        duration_ms: float,
        raw_html: Optional[str] = None,
        sanitized_html: Optional[str] = None
    ):
        """
        Log an operation to operations.jsonl

        Args:
            operation: Operation name (e.g., "navigate", "get_page_content")
            input_data: Input parameters
            output_data: Output/result data
            duration_ms: Operation duration in milliseconds
            raw_html: Optional raw HTML to save
            sanitized_html: Optional sanitized HTML to save
        """
        # Prepare operation record
        record = {
            "seq": self.operation_seq,
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "input": input_data,
            "output": self._sanitize_output(output_data),
            "duration_ms": round(duration_ms, 2)
        }

        # Save HTML files if provided
        if raw_html or sanitized_html:
            html_files = {}

            if raw_html:
                raw_path = self._save_html(self.operation_seq, "raw", raw_html)
                html_files["raw"] = str(raw_path.relative_to(self.session_dir))

            if sanitized_html:
                sanitized_path = self._save_html(self.operation_seq, "sanitized", sanitized_html)
                html_files["sanitized"] = str(sanitized_path.relative_to(self.session_dir))

            record["html_files"] = html_files

        # Append to operations.jsonl
        try:
            with open(self.operations_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Warning: Failed to log operation: {e}")

        # Increment sequence number
        self.operation_seq += 1

    def _save_html(self, seq: int, html_type: str, html_content: str) -> Path:
        """
        Save HTML content to file

        Args:
            seq: Sequence number
            html_type: Type of HTML ("raw" or "sanitized")
            html_content: HTML content string

        Returns:
            Path to saved HTML file
        """
        filename = f"{seq:03d}_{html_type}.html"
        filepath = self.html_dir / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            print(f"Warning: Failed to save HTML file {filename}: {e}")

        return filepath

    def _sanitize_output(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize output data to avoid storing huge content in JSONL

        Args:
            output_data: Original output data

        Returns:
            Sanitized output data
        """
        sanitized = output_data.copy()

        # Remove or truncate large fields
        if "content" in sanitized:
            content = sanitized["content"]
            if isinstance(content, str) and len(content) > 500:
                sanitized["content"] = content[:500] + f"... (truncated, {len(content)} chars total)"

        if "elements" in sanitized:
            elements = sanitized["elements"]
            if isinstance(elements, list) and len(elements) > 10:
                sanitized["elements"] = f"[{len(elements)} elements - see HTML files]"

        if "sanitized_html" in sanitized:
            html = sanitized["sanitized_html"]
            if isinstance(html, str) and len(html) > 500:
                sanitized["sanitized_html"] = html[:500] + f"... (truncated, {len(html)} chars total)"

        return sanitized

    def get_operation_count(self) -> int:
        """
        Get current operation count

        Returns:
            Number of operations logged
        """
        return self.operation_seq - 1


class OperationTimer:
    """Context manager to time operations"""

    def __init__(self):
        self.start_time = None
        self.duration_ms = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            self.duration_ms = (time.perf_counter() - self.start_time) * 1000

    def get_duration(self) -> float:
        """Get duration in milliseconds"""
        return self.duration_ms
