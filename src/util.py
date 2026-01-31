"""Utility helpers for environment detection and shared constants."""

import platform


def detect_host_os() -> str:
    """Return a normalized platform string ("linux" or "macos")."""
    system = platform.system()
    if system == "Darwin":
        return "macos"
    elif system == "Linux":
        return "linux"
    raise RuntimeError(f"Unsupported operating system: {system}")
