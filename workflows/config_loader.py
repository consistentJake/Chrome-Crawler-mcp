"""
Configuration File Loader for WebAgent Workflows.

Supports loading workflow configurations from YAML or JSON files.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class ConfigLoader:
    """Load and validate workflow configurations from files."""

    @staticmethod
    def load(config_path: str) -> Dict[str, Any]:
        """
        Load configuration from a file.

        Args:
            config_path: Path to config file (.yaml, .yml, or .json)

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config format is invalid
        """
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Determine format from extension
        suffix = config_file.suffix.lower()

        if suffix in ['.yaml', '.yml']:
            if not HAS_YAML:
                raise ImportError(
                    "PyYAML is required for YAML configs. "
                    "Install with: pip install pyyaml\n"
                    "Or use JSON format instead."
                )
            return ConfigLoader._load_yaml(config_file)

        elif suffix == '.json':
            return ConfigLoader._load_json(config_file)

        else:
            raise ValueError(
                f"Unsupported config format: {suffix}\n"
                f"Supported formats: .yaml, .yml, .json"
            )

    @staticmethod
    def _load_yaml(config_file: Path) -> Dict[str, Any]:
        """Load YAML configuration."""
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ValueError("YAML config must be a dictionary")

        return config

    @staticmethod
    def _load_json(config_file: Path) -> Dict[str, Any]:
        """Load JSON configuration."""
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        if not isinstance(config, dict):
            raise ValueError("JSON config must be an object")

        return config

    @staticmethod
    def save_template(
        output_path: str,
        format: str = "yaml",
        template_type: str = "1point3acres"
    ):
        """
        Save a template configuration file.

        Args:
            output_path: Where to save the template
            format: "yaml" or "json"
            template_type: Type of template ("1point3acres", etc.)
        """
        template = ConfigLoader._get_template(template_type)

        output_file = Path(output_path)

        if format == "yaml":
            if not HAS_YAML:
                raise ImportError("PyYAML required. Install with: pip install pyyaml")

            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(template, f, default_flow_style=False, sort_keys=False)

        elif format == "json":
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)

        else:
            raise ValueError(f"Unsupported format: {format}")

        print(f"Template saved to: {output_file}")

    @staticmethod
    def _get_template(template_type: str) -> Dict[str, Any]:
        """Get a configuration template."""
        if template_type == "1point3acres":
            return {
                "# 1Point3Acres Forum Scraper Configuration": None,
                "# All parameters are optional except 'url'": None,
                "": None,

                "# Target Configuration": None,
                "url": "https://www.1point3acres.com/bbs/tag-9407-1.html",
                "num_pages": 1,
                "posts_per_page": None,  # None = all posts, or specify a number

                "# Speed Configuration": None,
                "# Options: fast, normal, slow, cautious": None,
                "speed": "normal",

                "# Or set custom wait times (overrides speed profile)": None,
                "custom_waits": {
                    "enabled": False,
                    "page_load_wait": 3.0,
                    "between_posts_wait": 1.5,
                    "between_pages_wait": 2.0
                },

                "# Output Configuration": None,
                "output": {
                    "directory": "./scraper_output",
                    "save_individual_posts": True,
                    "save_combined_results": True
                },

                "# Verification Settings": None,
                "verification": {
                    "min_posts_per_page": 1,
                    "verify_post_content": True
                },

                "# Runtime Options": None,
                "runtime": {
                    "verbose": True,
                    "client_type": "chrome"
                },

                "# Resume Settings (optional)": None,
                "resume": {
                    "enabled": False,
                    "start_page": 1,
                    "resume_from_post": 0
                }
            }

        else:
            raise ValueError(f"Unknown template type: {template_type}")


def load_1point3acres_config(config_path: str):
    """
    Load 1point3acres workflow config from file.

    Args:
        config_path: Path to config file

    Returns:
        Tuple of (OnePoint3AcresConfig, runtime_options)
    """
    from onepoint3acres_workflow import OnePoint3AcresConfig, SpeedProfile

    config = ConfigLoader.load(config_path)

    # Extract components
    url = config.get("url")
    if not url:
        raise ValueError("Config must specify 'url'")

    num_pages = config.get("num_pages", 1)
    posts_per_page = config.get("posts_per_page", None)

    # Speed configuration
    speed = config.get("speed", "normal")
    custom_waits = config.get("custom_waits", {})

    # Output configuration
    output_config = config.get("output", {})
    output_dir = output_config.get("directory", "./scraper_output")
    save_individual = output_config.get("save_individual_posts", True)
    save_combined = output_config.get("save_combined_results", True)

    # Verification
    verification = config.get("verification", {})
    min_posts = verification.get("min_posts_per_page", 1)
    verify_content = verification.get("verify_post_content", True)

    # Runtime options
    runtime = config.get("runtime", {})
    verbose = runtime.get("verbose", True)
    client_type = runtime.get("client_type", "chrome")

    # Resume settings
    resume = config.get("resume", {})
    resume_enabled = resume.get("enabled", False)
    start_page = resume.get("start_page", 1) if resume_enabled else None
    resume_from_post = resume.get("resume_from_post", 0) if resume_enabled else None

    # Create workflow config
    if custom_waits.get("enabled", False):
        # Use custom wait times
        workflow_config = OnePoint3AcresConfig(
            base_url=url,
            num_pages=num_pages,
            posts_per_page=posts_per_page,
            page_load_wait=custom_waits.get("page_load_wait", 3.0),
            between_posts_wait=custom_waits.get("between_posts_wait", 1.5),
            between_pages_wait=custom_waits.get("between_pages_wait", 2.0),
            min_posts_per_page=min_posts,
            verify_post_content=verify_content,
            save_individual_posts=save_individual,
            save_combined_results=save_combined
        )
    else:
        # Use speed profile
        workflow_config = OnePoint3AcresConfig.from_speed_profile(
            base_url=url,
            speed=speed,
            num_pages=num_pages,
            posts_per_page=posts_per_page,
            min_posts_per_page=min_posts,
            verify_post_content=verify_content,
            save_individual_posts=save_individual,
            save_combined_results=save_combined
        )

    runtime_options = {
        "verbose": verbose,
        "client_type": client_type,
        "output_dir": output_dir,
        "start_page": start_page,
        "resume_from_post": resume_from_post
    }

    return workflow_config, runtime_options


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Config file tools")
    parser.add_argument("--create", metavar="FILE", help="Create a template config file")
    parser.add_argument("--format", choices=["yaml", "json"], default="yaml",
                        help="Config format (default: yaml)")
    parser.add_argument("--test", metavar="FILE", help="Test loading a config file")

    args = parser.parse_args()

    if args.create:
        try:
            ConfigLoader.save_template(args.create, format=args.format)
            print(f"✅ Template created: {args.create}")
        except Exception as e:
            print(f"❌ Error: {e}")

    elif args.test:
        try:
            config = ConfigLoader.load(args.test)
            print(f"✅ Config loaded successfully")
            print(f"\nConfig contents:")
            print(json.dumps(config, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"❌ Error: {e}")

    else:
        parser.print_help()
