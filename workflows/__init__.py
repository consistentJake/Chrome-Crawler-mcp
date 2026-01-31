"""
WebAgent Workflows Module.

Provides automated workflow classes for common web scraping and automation tasks.
These workflows use the interactive_web_agent_mcp.py infrastructure programmatically.

Available Workflows:
- OnePoint3AcresWorkflow: Scrape 1point3acres forum posts
- (More to come)

Usage:
    from workflows import scrape_1point3acres

    result = scrape_1point3acres(
        url="https://www.1point3acres.com/bbs/tag/openai-9407-1.html",
        num_pages=2,
        posts_per_page=5
    )
"""

from .base_workflow import (
    BaseWorkflow,
    WorkflowResult,
    StepResult,
    VerificationResult,
    VerificationStatus
)

from .onepoint3acres_workflow import (
    OnePoint3AcresWorkflow,
    OnePoint3AcresConfig,
    scrape_1point3acres
)

__all__ = [
    # Base classes
    "BaseWorkflow",
    "WorkflowResult",
    "StepResult",
    "VerificationResult",
    "VerificationStatus",

    # 1point3acres workflow
    "OnePoint3AcresWorkflow",
    "OnePoint3AcresConfig",
    "scrape_1point3acres",
]
