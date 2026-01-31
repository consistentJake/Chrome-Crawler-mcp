"""
Shared Utilities Module

Common utilities used across workflows and PostProcessing modules.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Keywords to skip posts that are not interview-related
SKIP_KEYWORDS = [
    "新人如何使用",
    "发错了",
    "Welcome on board",
    "如何免费获得",
    "积分限制",
]

# Keywords indicating low-value replies to filter
LOW_VALUE_PATTERNS = [
    "感谢楼主",
    "已加米",
    "求加米",
    "顶",
    "mark",
    "已私信",
    "已dm",
]


# =============================================================================
# DICTIONARY UTILITIES
# =============================================================================

def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries.

    Args:
        base: Base dictionary
        override: Override dictionary (takes precedence)

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# =============================================================================
# FILE UTILITIES
# =============================================================================

def load_yaml(file_path: Path) -> Dict[str, Any]:
    """
    Load YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed dictionary

    Raises:
        ImportError: If PyYAML is not installed
        ValueError: If file content is not a dictionary
    """
    if not HAS_YAML:
        raise ImportError(
            "PyYAML is required for YAML files. "
            "Install with: pip install pyyaml"
        )

    with open(file_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    if config is not None and not isinstance(config, dict):
        raise ValueError("YAML content must be a dictionary")

    return config or {}


def load_json(file_path: Path) -> Dict[str, Any]:
    """
    Load JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed dictionary

    Raises:
        ValueError: If file content is not a dictionary
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    if not isinstance(config, dict):
        raise ValueError("JSON content must be a dictionary/object")

    return config


def load_config_file(file_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML or JSON file.

    Auto-detects format from file extension.

    Args:
        file_path: Path to config file (.yaml, .yml, or .json)

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If format is not supported
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix in ['.yaml', '.yml']:
        return load_yaml(path)
    elif suffix == '.json':
        return load_json(path)
    else:
        raise ValueError(
            f"Unsupported config format: {suffix}\n"
            f"Supported formats: .yaml, .yml, .json"
        )


def save_json(data: Any, file_path: str, indent: int = 2) -> str:
    """
    Save data to JSON file.

    Args:
        data: Data to save
        file_path: Output file path
        indent: JSON indentation level

    Returns:
        Absolute path to saved file
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)

    return str(path.absolute())


def save_yaml(data: Dict, file_path: str) -> str:
    """
    Save data to YAML file.

    Args:
        data: Data to save
        file_path: Output file path

    Returns:
        Absolute path to saved file

    Raises:
        ImportError: If PyYAML is not installed
    """
    if not HAS_YAML:
        raise ImportError("PyYAML required. Install with: pip install pyyaml")

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return str(path.absolute())


# =============================================================================
# DIRECTORY UTILITIES
# =============================================================================

def create_timestamped_dir(base_dir: str, prefix: str = "") -> str:
    """
    Create a directory with timestamp suffix.

    Args:
        base_dir: Base directory path
        prefix: Optional prefix for the directory name

    Returns:
        Path to created directory (e.g., "output_20250122_153045")
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if prefix:
        dir_name = f"{prefix}_{timestamp}"
    else:
        dir_name = f"{base_dir}_{timestamp}"
        base_dir = os.path.dirname(base_dir) or "."

    full_path = os.path.join(base_dir, dir_name) if prefix else dir_name
    os.makedirs(full_path, exist_ok=True)
    return full_path


def find_config_file(
    config_path: Optional[str] = None,
    search_dirs: Optional[List[Path]] = None,
    config_names: Optional[List[str]] = None
) -> Optional[Path]:
    """
    Find a config file using priority search.

    Args:
        config_path: Explicit config path (highest priority)
        search_dirs: Directories to search in
        config_names: Config file names to look for (in priority order)

    Returns:
        Path to config file or None if not found

    Raises:
        FileNotFoundError: If explicit config_path doesn't exist
    """
    if config_path:
        path = Path(config_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"Config file not found: {config_path}")

    if search_dirs is None:
        search_dirs = [Path.cwd()]

    if config_names is None:
        config_names = ["config.local.yaml", "config.yaml", "config.json"]

    for search_dir in search_dirs:
        for name in config_names:
            config_file = search_dir / name
            if config_file.exists():
                return config_file

    return None


# =============================================================================
# TEXT FILTERING UTILITIES
# =============================================================================

def should_skip_by_keywords(text: str, keywords: Optional[List[str]] = None) -> bool:
    """
    Check if text should be skipped based on keywords.

    Args:
        text: Text to check
        keywords: List of keywords (uses SKIP_KEYWORDS if None)

    Returns:
        True if text contains any skip keyword
    """
    if keywords is None:
        keywords = SKIP_KEYWORDS

    for keyword in keywords:
        if keyword in text:
            return True
    return False


def is_low_value_content(
    content: str,
    patterns: Optional[List[str]] = None,
    min_length: int = 10
) -> bool:
    """
    Check if content is low-value (thanks, mark, etc.).

    Args:
        content: Content to check
        patterns: Low-value patterns (uses LOW_VALUE_PATTERNS if None)
        min_length: Minimum content length

    Returns:
        True if content is low-value
    """
    if not content:
        return True

    content_lower = content.lower().strip()

    if len(content_lower) < min_length:
        return True

    if patterns is None:
        patterns = LOW_VALUE_PATTERNS

    for pattern in patterns:
        if content_lower.startswith(pattern.lower()):
            # But if it has more content after, might still be valuable
            if len(content_lower) > len(pattern) + 20:
                return False
            return True

    return False


# =============================================================================
# DATA EXTRACTION UTILITIES
# =============================================================================

def extract_posts_from_workflow_output(workflow_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract posts array from workflow output format.

    Handles the output format from onepoint3acres_workflow.py:
    {
        "workflow": "1point3acres_forum_scraper",
        "config": {...},
        "summary": {...},
        "posts": [...]
    }

    Args:
        workflow_output: Workflow output dictionary

    Returns:
        List of post dictionaries
    """
    # Direct posts array
    if "posts" in workflow_output:
        return workflow_output["posts"]

    # If it's already a list, return as-is
    if isinstance(workflow_output, list):
        return workflow_output

    return []


def get_post_title(post: Dict[str, Any]) -> str:
    """
    Extract title from post, handling different data structures.

    Args:
        post: Post dictionary

    Returns:
        Post title or empty string
    """
    # New scraper format: metadata.thread_title
    metadata = post.get("metadata", {})
    if metadata.get("thread_title"):
        return metadata["thread_title"]
    if metadata.get("page_title"):
        return metadata["page_title"]

    # Workflow metadata format
    workflow_metadata = post.get("workflow_metadata", {})
    original_link = workflow_metadata.get("original_link", {})
    if original_link.get("text"):
        return original_link["text"]

    # Old format: direct keys
    return post.get("thread_title", "") or post.get("page_title", "") or post.get("title", "")


def get_post_url(post: Dict[str, Any]) -> str:
    """
    Extract URL from post, handling different data structures.

    Args:
        post: Post dictionary

    Returns:
        Post URL or empty string
    """
    if post.get("url"):
        return post["url"]

    workflow_metadata = post.get("workflow_metadata", {})
    original_link = workflow_metadata.get("original_link", {})
    if original_link.get("full_url"):
        return original_link["full_url"]

    return ""


def get_main_content(post: Dict[str, Any]) -> str:
    """
    Extract main content from post, handling different data structures.

    Args:
        post: Post dictionary

    Returns:
        Main post content or empty string
    """
    # New scraper format: items.main_post
    items = post.get("items", {})
    if items:
        main_post = items.get("main_post")
        if main_post and main_post.get("content"):
            return main_post["content"]
        # Fall back to first reply
        replies = items.get("replies", [])
        if replies and replies[0].get("content"):
            return replies[0]["content"]

    # Old format: replies[0].mainPageContent
    replies = post.get("replies", [])
    if replies and "mainPageContent" in replies[0]:
        return replies[0]["mainPageContent"]

    return ""


def get_replies(post: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract replies from post, handling different data structures.

    Args:
        post: Post dictionary

    Returns:
        List of reply dictionaries
    """
    # New scraper format: items.replies
    items = post.get("items", {})
    if items:
        return items.get("replies", [])

    # Old format: direct replies
    return post.get("replies", [])


# =============================================================================
# UNIFIED CONFIGURATION
# =============================================================================

# Default configuration for the entire pipeline
DEFAULT_UNIFIED_CONFIG = {
    "scraper": {
        "url": "",
        "num_pages": 1,
        "posts_per_page": None,
        "speed": "normal",
        "custom_waits": {
            "enabled": False,
            "page_load_wait": 3.0,
            "between_posts_wait": 1.5,
            "between_pages_wait": 2.0,
        },
        "output": {
            "directory": "./scraper_output",
            "save_individual_posts": True,
            "save_combined_results": True,
        },
        "verification": {
            "min_posts_per_page": 1,
            "verify_post_content": True,
        },
        "runtime": {
            "verbose": True,
            "client_type": "chrome",
        },
        "resume": {
            "enabled": False,
            "start_page": 1,
            "resume_from_post": 0,
        },
    },
    "extraction": {
        "api": {
            "provider": "anthropic",
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
    },
    "filters": {
        "skip_keywords": SKIP_KEYWORDS,
        "low_value_patterns": LOW_VALUE_PATTERNS,
        "llm_filter": {
            "enabled": False,
            "api": {},
            "processing": {
                "posts_per_batch": 20,
                "confidence_threshold": 0.7,
                "delay_between_calls": 0.5,
            },
            "output": {
                "save_results": True,
                "results_filename": "filter_results.json",
            },
        },
    },
    "pipeline": {
        "auto_extract": True,
        "dry_run": False,
        "dump_prompt_only": False,
        "stages": {
            "keyword_filter": True,
            "llm_filter": False,
            "extraction": True,
        },
    },
}


class UnifiedConfig:
    """
    Unified configuration for the entire WebAgent pipeline.

    Loads configuration from a single YAML/JSON file with sections for:
    - scraper: Web scraping settings
    - extraction: LLM extraction settings
    - filters: Shared filter keywords
    - pipeline: Orchestration settings
    """

    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "UnifiedConfig":
        """
        Load unified configuration from file.

        Args:
            config_path: Path to config file (optional)

        Returns:
            UnifiedConfig instance
        """
        # Find config file
        project_root = Path(__file__).parent.parent
        search_dirs = [Path.cwd(), project_root]

        config_file = find_config_file(config_path, search_dirs)

        if config_file is None:
            print("No config file found, using defaults")
            return cls(DEFAULT_UNIFIED_CONFIG.copy())

        print(f"Loading config from: {config_file}")
        file_config = load_config_file(str(config_file))

        # Deep merge with defaults
        merged_config = deep_merge(DEFAULT_UNIFIED_CONFIG, file_config)

        # Environment variable override for API key
        env_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_api_key and not merged_config["extraction"]["api"].get("api_key"):
            merged_config["extraction"]["api"]["api_key"] = env_api_key

        return cls(merged_config)

    # -------------------------------------------------------------------------
    # Scraper Settings
    # -------------------------------------------------------------------------
    @property
    def scraper(self) -> Dict[str, Any]:
        return self._config.get("scraper", {})

    @property
    def scraper_url(self) -> str:
        return self.scraper.get("url", "")

    @property
    def scraper_num_pages(self) -> int:
        return self.scraper.get("num_pages", 1)

    @property
    def scraper_posts_per_page(self) -> Optional[int]:
        return self.scraper.get("posts_per_page")

    @property
    def scraper_speed(self) -> str:
        return self.scraper.get("speed", "normal")

    @property
    def scraper_output_dir(self) -> str:
        return self.scraper.get("output", {}).get("directory", "./scraper_output")

    @property
    def scraper_verbose(self) -> bool:
        return self.scraper.get("runtime", {}).get("verbose", True)

    # -------------------------------------------------------------------------
    # Extraction Settings
    # -------------------------------------------------------------------------
    @property
    def extraction(self) -> Dict[str, Any]:
        return self._config.get("extraction", {})

    @property
    def api_provider(self) -> str:
        return self.extraction.get("api", {}).get("provider", "anthropic")

    @property
    def api_key(self) -> str:
        return self.extraction.get("api", {}).get("api_key", "")

    @property
    def api_base_url(self) -> Optional[str]:
        return self.extraction.get("api", {}).get("base_url")

    @property
    def api_model(self) -> str:
        return self.extraction.get("api", {}).get("model", "claude-sonnet-4-20250514")

    @property
    def api_max_tokens(self) -> int:
        return self.extraction.get("api", {}).get("max_tokens", 4096)

    @property
    def api_temperature(self) -> float:
        return self.extraction.get("api", {}).get("temperature", 0.1)

    @property
    def posts_per_group(self) -> int:
        return self.extraction.get("processing", {}).get("posts_per_group", 3)

    @property
    def min_content_length(self) -> int:
        return self.extraction.get("processing", {}).get("min_content_length", 50)

    @property
    def delay_between_calls(self) -> float:
        return self.extraction.get("processing", {}).get("delay_between_calls", 1.0)

    @property
    def extraction_output_dir(self) -> str:
        return self.extraction.get("output", {}).get("output_dir", "output")

    @property
    def save_intermediate(self) -> bool:
        return self.extraction.get("output", {}).get("save_intermediate", True)

    # -------------------------------------------------------------------------
    # Filter Settings
    # -------------------------------------------------------------------------
    @property
    def filters(self) -> Dict[str, Any]:
        return self._config.get("filters", {})

    @property
    def skip_keywords(self) -> List[str]:
        return self.filters.get("skip_keywords", SKIP_KEYWORDS)

    @property
    def low_value_patterns(self) -> List[str]:
        return self.filters.get("low_value_patterns", LOW_VALUE_PATTERNS)

    @property
    def llm_filter_enabled(self) -> bool:
        """Check if LLM filtering is enabled in the filters section."""
        return self.filters.get("llm_filter", {}).get("enabled", False)

    @property
    def llm_filter_config(self) -> Dict[str, Any]:
        """Get the full LLM filter configuration."""
        return self.filters.get("llm_filter", {})

    # -------------------------------------------------------------------------
    # Pipeline Settings
    # -------------------------------------------------------------------------
    @property
    def pipeline(self) -> Dict[str, Any]:
        return self._config.get("pipeline", {})

    @property
    def auto_extract(self) -> bool:
        return self.pipeline.get("auto_extract", True)

    @property
    def dry_run(self) -> bool:
        return self.pipeline.get("dry_run", False)

    @property
    def dump_prompt_only(self) -> bool:
        return self.pipeline.get("dump_prompt_only", False)

    @property
    def keyword_filter_enabled(self) -> bool:
        """Check if keyword-based filtering stage is enabled."""
        return self.pipeline.get("stages", {}).get("keyword_filter", True)

    @property
    def llm_filter_stage_enabled(self) -> bool:
        """Check if LLM-based filtering stage is enabled."""
        return self.pipeline.get("stages", {}).get("llm_filter", False)

    @property
    def extraction_stage_enabled(self) -> bool:
        """Check if extraction stage is enabled."""
        return self.pipeline.get("stages", {}).get("extraction", True)

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return self._config.copy()

    def get_scraper_config_dict(self) -> Dict[str, Any]:
        """Get scraper config in the format expected by workflows."""
        scraper = self.scraper
        return {
            "url": scraper.get("url", ""),
            "num_pages": scraper.get("num_pages", 1),
            "posts_per_page": scraper.get("posts_per_page"),
            "speed": scraper.get("speed", "normal"),
            "custom_waits": scraper.get("custom_waits", {}),
            "output": scraper.get("output", {}),
            "verification": scraper.get("verification", {}),
            "runtime": scraper.get("runtime", {}),
            "resume": scraper.get("resume", {}),
        }

    def get_extraction_config_dict(self) -> Dict[str, Any]:
        """Get extraction config in the format expected by promptProcessing."""
        extraction = self.extraction
        return {
            "api": extraction.get("api", {}),
            "processing": extraction.get("processing", {}),
            "output": extraction.get("output", {}),
            "filters": self.filters,
        }
