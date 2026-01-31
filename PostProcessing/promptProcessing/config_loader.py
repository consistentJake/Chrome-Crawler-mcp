"""
Configuration Loader

Loads settings from YAML config files with fallback to defaults.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add project root to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared import (
    deep_merge,
    find_config_file as shared_find_config_file,
    SKIP_KEYWORDS,
    LOW_VALUE_PATTERNS,
)

try:
    import yaml
except ImportError:
    yaml = None
    print("Warning: PyYAML not installed. Run: pip install pyyaml")


# Default configuration values (use shared constants for filters)
DEFAULT_CONFIG = {
    "api": {
        "provider": "anthropic",  # or "openai"
        "api_key": "",
        "base_url": None,
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "temperature": 0.1,
    },
    "processing": {
        "posts_per_group": 3,
        "min_content_length": 50,
        "delay_between_calls": 1.0,
    },
    "output": {
        "output_dir": "output",
        "save_intermediate": True,
    },
    "filters": {
        "skip_keywords": SKIP_KEYWORDS,
        "low_value_patterns": LOW_VALUE_PATTERNS,
    },
}


def find_config_file(config_path: Optional[str] = None) -> Optional[Path]:
    """
    Find the config file to use.

    Priority:
    1. Explicitly provided path
    2. config.local.yaml (user-specific, gitignored)
    3. config.yaml (default template)

    Args:
        config_path: Optional explicit config path

    Returns:
        Path to config file or None
    """
    search_dirs = [Path.cwd(), Path(__file__).parent]
    return shared_find_config_file(config_path, search_dirs)


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Optional path to config file

    Returns:
        Configuration dictionary
    """
    if yaml is None:
        print("Warning: PyYAML not installed, using default config")
        return DEFAULT_CONFIG.copy()

    config_file = find_config_file(config_path)

    if config_file is None:
        print("No config file found, using defaults")
        return DEFAULT_CONFIG.copy()

    print(f"Loading config from: {config_file}")

    with open(config_file, "r", encoding="utf-8") as f:
        file_config = yaml.safe_load(f) or {}

    # Merge with defaults
    config = deep_merge(DEFAULT_CONFIG, file_config)

    # Environment variable override for API key (highest priority)
    env_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_api_key:
        config["api"]["api_key"] = env_api_key

    return config


class Config:
    """Configuration object with attribute access."""

    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict

    # API settings
    @property
    def provider(self) -> str:
        return self._config["api"].get("provider", "anthropic")

    @property
    def api_key(self) -> str:
        return self._config["api"]["api_key"]

    @property
    def base_url(self) -> Optional[str]:
        return self._config["api"].get("base_url")

    @property
    def model(self) -> str:
        return self._config["api"]["model"]

    @property
    def max_tokens(self) -> int:
        return self._config["api"]["max_tokens"]

    @property
    def temperature(self) -> float:
        return self._config["api"]["temperature"]

    # Processing settings
    @property
    def posts_per_group(self) -> int:
        return self._config["processing"]["posts_per_group"]

    @property
    def min_content_length(self) -> int:
        return self._config["processing"]["min_content_length"]

    @property
    def delay_between_calls(self) -> float:
        return self._config["processing"]["delay_between_calls"]

    # Output settings
    @property
    def output_dir(self) -> str:
        return self._config["output"]["output_dir"]

    @property
    def save_intermediate(self) -> bool:
        return self._config["output"]["save_intermediate"]

    # Filter settings
    @property
    def skip_keywords(self) -> list:
        return self._config["filters"]["skip_keywords"]

    @property
    def low_value_patterns(self) -> list:
        return self._config["filters"]["low_value_patterns"]

    def to_dict(self) -> Dict[str, Any]:
        return self._config.copy()


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get configuration object.

    Args:
        config_path: Optional path to config file

    Returns:
        Config object
    """
    config_dict = load_config(config_path)
    return Config(config_dict)


if __name__ == "__main__":
    # Test config loading
    config = get_config()
    print("\nLoaded configuration:")
    print(f"  Model: {config.model}")
    print(f"  Posts per group: {config.posts_per_group}")
    print(f"  Output dir: {config.output_dir}")
    print(f"  API key set: {'Yes' if config.api_key else 'No'}")
