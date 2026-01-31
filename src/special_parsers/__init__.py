"""
Special Parser Registry
Maps URL patterns to specialized parsers for structured data extraction.
"""

import re
from typing import Optional
from .base import BaseParser
from .x_com import XComParser
from .onepoint3acres import OnePoint3AcresParser
from .linkedin_jobs import LinkedInJobsParser
from .reddit import RedditParser


# Parser registry with URL pattern matching
PARSER_REGISTRY = {
    "x.com": {
        "patterns": [
            r"x\.com",
            r"twitter\.com",
        ],
        "parser_class": XComParser,
        "description": "Extracts tweets with user info, text, metrics, and media",
        "supported_pages": ["search", "timeline", "profile", "tweet"]
    },
    "1point3acres": {
        "patterns": [
            r"1point3acres\.com",
            r"1point3acres",
        ],
        "parser_class": OnePoint3AcresParser,
        "description": "Extracts forum posts and replies with user info, content, and reactions",
        "supported_pages": ["thread", "forum"]
    },
    "linkedin-jobs": {
        "patterns": [
            r"linkedin\.com/jobs",
        ],
        "parser_class": LinkedInJobsParser,
        "description": "Extracts job listings with title, company, location, salary, and metadata",
        "supported_pages": ["search", "company-jobs"]
    },
    "reddit": {
        "patterns": [
            r"reddit\.com",
        ],
        "parser_class": RedditParser,
        "description": "Extracts posts and comments from subreddit listings and post pages",
        "supported_pages": ["subreddit", "post"]
    },
}


def get_parser_for_url(url: str) -> Optional[BaseParser]:
    """
    Match URL to appropriate parser.

    Args:
        url: Current page URL

    Returns:
        Parser instance or None if no match
    """
    for name, config in PARSER_REGISTRY.items():
        for pattern in config["patterns"]:
            if re.search(pattern, url, re.IGNORECASE):
                parser_class = config["parser_class"]
                return parser_class()
    return None


def list_available_parsers():
    """
    Return list of available parsers with descriptions.

    Returns:
        List of parser info dicts
    """
    return [
        {
            "name": name,
            "description": config["description"],
            "supported_pages": config.get("supported_pages", []),
            "patterns": config["patterns"]
        }
        for name, config in PARSER_REGISTRY.items()
    ]


__all__ = [
    "BaseParser",
    "XComParser",
    "OnePoint3AcresParser",
    "LinkedInJobsParser",
    "RedditParser",
    "get_parser_for_url",
    "list_available_parsers",
    "PARSER_REGISTRY"
]
