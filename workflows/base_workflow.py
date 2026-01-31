"""
Base Workflow Module for Web Agent Automation.

Provides common operations for browser-based workflows using
the interactive web agent infrastructure.
"""

import os
import sys
import json
import time
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

# Add project directories to path
PROJECT_DIR = Path(__file__).parent.parent
SRC_DIR = PROJECT_DIR / "src"
HELPER_DIR = PROJECT_DIR / "helper"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(HELPER_DIR))
sys.path.insert(0, str(PROJECT_DIR))

from browser_integration import BrowserIntegration
from html_sanitizer import HTMLSanitizer
from query_engine import QueryEngine
from special_parsers import get_parser_for_url, list_available_parsers


class VerificationStatus(Enum):
    """Verification result status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class VerificationResult:
    """Result of a verification check."""
    name: str
    status: VerificationStatus
    message: str
    details: Optional[Dict] = None


@dataclass
class StepResult:
    """Result of a workflow step."""
    step_name: str
    success: bool
    duration_ms: int
    data: Optional[Any] = None
    error: Optional[str] = None
    verifications: List[VerificationResult] = field(default_factory=list)


@dataclass
class WorkflowResult:
    """Complete workflow execution result."""
    workflow_name: str
    success: bool
    start_time: str
    end_time: str
    total_duration_ms: int
    steps: List[StepResult] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)
    output_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class BaseWorkflow(ABC):
    """
    Base class for web automation workflows.

    Provides common operations like:
    - Browser navigation with verification
    - Page content extraction
    - Element querying
    - Result saving
    """

    def __init__(
        self,
        client_type: str = "chrome",
        output_dir: Optional[str] = None,
        wait_between_steps: float = 1.0,
        verbose: bool = True
    ):
        """
        Initialize workflow.

        Args:
            client_type: Browser client type ("chrome" or "playwright")
            output_dir: Directory for output files
            wait_between_steps: Default wait time between steps (seconds)
            verbose: Print progress messages
        """
        self.client_type = client_type
        self.output_dir = Path(output_dir) if output_dir else Path("./workflow_output")
        self.wait_between_steps = wait_between_steps
        self.verbose = verbose

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components (lazy loading)
        self._browser: Optional[BrowserIntegration] = None
        self._sanitizer: Optional[HTMLSanitizer] = None
        self._query_engine: Optional[QueryEngine] = None

        # State
        self._current_elements: List[Dict] = []
        self._current_url: str = ""
        self._current_title: str = ""

        # Results tracking
        self._steps: List[StepResult] = []
        self._errors: List[str] = []

    @property
    def browser(self) -> BrowserIntegration:
        """Get or create browser integration instance."""
        if self._browser is None:
            self._browser = BrowserIntegration(client_type=self.client_type)
        return self._browser

    @property
    def sanitizer(self) -> HTMLSanitizer:
        """Get or create HTML sanitizer instance."""
        if self._sanitizer is None:
            self._sanitizer = HTMLSanitizer(max_tokens=8000, preserve_structure=True)
        return self._sanitizer

    @property
    def query_engine(self) -> QueryEngine:
        """Get or create query engine instance."""
        if self._query_engine is None:
            self._query_engine = QueryEngine()
        return self._query_engine

    def log(self, message: str, level: str = "INFO"):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "")
            print(f"[{timestamp}] {prefix} {message}")

    # ==================== Core Operations ====================

    def navigate(
        self,
        url: str,
        wait_seconds: float = 2.0,
        verify_url_contains: Optional[str] = None
    ) -> StepResult:
        """
        Navigate to a URL with verification.

        Args:
            url: URL to navigate to
            wait_seconds: Seconds to wait after navigation
            verify_url_contains: Optional string that URL should contain

        Returns:
            StepResult with navigation outcome
        """
        start_time = time.time()
        verifications = []

        self.log(f"Navigating to: {url}")

        try:
            # Navigate
            result = self.browser.playwright_client.browser_navigate(url)

            if result.get("status") != "success":
                return StepResult(
                    step_name="navigate",
                    success=False,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=f"Navigation failed: {result.get('message', 'Unknown error')}"
                )

            # Wait for page load
            time.sleep(wait_seconds)

            # Get current URL and title
            self._current_url = self.browser.get_current_url()
            self._current_title = self.browser.get_page_title()

            # Verify URL if requested
            if verify_url_contains:
                if verify_url_contains in self._current_url:
                    verifications.append(VerificationResult(
                        name="url_contains",
                        status=VerificationStatus.PASSED,
                        message=f"URL contains '{verify_url_contains}'"
                    ))
                else:
                    verifications.append(VerificationResult(
                        name="url_contains",
                        status=VerificationStatus.FAILED,
                        message=f"URL does not contain '{verify_url_contains}'",
                        details={"expected": verify_url_contains, "actual": self._current_url}
                    ))

            self.log(f"Navigated to: {self._current_title}", "SUCCESS")

            return StepResult(
                step_name="navigate",
                success=True,
                duration_ms=int((time.time() - start_time) * 1000),
                data={"url": self._current_url, "title": self._current_title},
                verifications=verifications
            )

        except Exception as e:
            return StepResult(
                step_name="navigate",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def get_page_content(
        self,
        min_elements: Optional[int] = None,
        expected_element_types: Optional[List[str]] = None
    ) -> StepResult:
        """
        Extract page content and interactable elements.

        Args:
            min_elements: Minimum expected number of elements
            expected_element_types: List of expected element types (a, button, input)

        Returns:
            StepResult with extracted elements
        """
        start_time = time.time()
        verifications = []

        self.log("Extracting page content...")

        try:
            # Get raw HTML
            raw_html = self.browser.get_current_page_html()

            # Sanitize and extract elements
            sanitized_result = self.sanitizer.sanitize(raw_html, extraction_mode="all")
            self._current_elements = sanitized_result['element_registry']

            element_count = len(self._current_elements)
            element_types = sanitized_result['statistics']['element_types']

            # Verify minimum elements
            if min_elements is not None:
                if element_count >= min_elements:
                    verifications.append(VerificationResult(
                        name="min_elements",
                        status=VerificationStatus.PASSED,
                        message=f"Found {element_count} elements (min: {min_elements})"
                    ))
                else:
                    verifications.append(VerificationResult(
                        name="min_elements",
                        status=VerificationStatus.FAILED,
                        message=f"Found only {element_count} elements (min: {min_elements})"
                    ))

            # Verify expected element types
            if expected_element_types:
                for etype in expected_element_types:
                    if element_types.get(etype, 0) > 0:
                        verifications.append(VerificationResult(
                            name=f"element_type_{etype}",
                            status=VerificationStatus.PASSED,
                            message=f"Found {element_types[etype]} <{etype}> elements"
                        ))
                    else:
                        verifications.append(VerificationResult(
                            name=f"element_type_{etype}",
                            status=VerificationStatus.WARNING,
                            message=f"No <{etype}> elements found"
                        ))

            self.log(f"Extracted {element_count} elements", "SUCCESS")

            return StepResult(
                step_name="get_page_content",
                success=True,
                duration_ms=int((time.time() - start_time) * 1000),
                data={
                    "element_count": element_count,
                    "element_types": element_types,
                    "elements": self._current_elements
                },
                verifications=verifications
            )

        except Exception as e:
            return StepResult(
                step_name="get_page_content",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def query_elements(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict] = None,
        limit: Optional[int] = None,
        verify_min_results: Optional[int] = None
    ) -> StepResult:
        """
        Query elements using natural language or structured filters.

        Args:
            query: Natural language query
            filters: Structured filters dict
            limit: Maximum results to return
            verify_min_results: Minimum expected results

        Returns:
            StepResult with matching elements
        """
        start_time = time.time()
        verifications = []

        query_desc = query or str(filters)
        self.log(f"Querying elements: {query_desc[:50]}...")

        try:
            if not self._current_elements:
                return StepResult(
                    step_name="query_elements",
                    success=False,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error="No page content loaded. Call get_page_content() first."
                )

            # Execute query
            matches = self.query_engine.query_elements(
                self._current_elements,
                query=query,
                filters=filters,
                limit=limit
            )

            # Verify minimum results
            if verify_min_results is not None:
                if len(matches) >= verify_min_results:
                    verifications.append(VerificationResult(
                        name="min_results",
                        status=VerificationStatus.PASSED,
                        message=f"Found {len(matches)} results (min: {verify_min_results})"
                    ))
                else:
                    verifications.append(VerificationResult(
                        name="min_results",
                        status=VerificationStatus.FAILED,
                        message=f"Found only {len(matches)} results (min: {verify_min_results})"
                    ))

            self.log(f"Found {len(matches)} matching elements", "SUCCESS")

            return StepResult(
                step_name="query_elements",
                success=True,
                duration_ms=int((time.time() - start_time) * 1000),
                data={"matches": matches, "count": len(matches)},
                verifications=verifications
            )

        except Exception as e:
            return StepResult(
                step_name="query_elements",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def parse_page_with_parser(
        self,
        parser_name: str = "auto",
        verify_min_items: Optional[int] = None
    ) -> StepResult:
        """
        Parse current page using a specialized parser.

        Args:
            parser_name: Parser name or "auto" for auto-detection
            verify_min_items: Minimum expected items

        Returns:
            StepResult with parsed data
        """
        start_time = time.time()
        verifications = []

        self.log(f"Parsing page with parser: {parser_name}")

        try:
            # Get parser
            current_url = self.browser.get_current_url()

            if parser_name == "auto":
                parser = get_parser_for_url(current_url)
                if not parser:
                    return StepResult(
                        step_name="parse_page",
                        success=False,
                        duration_ms=int((time.time() - start_time) * 1000),
                        error=f"No parser available for URL: {current_url}"
                    )
            else:
                parser = get_parser_for_url(f"https://{parser_name}/")
                if not parser:
                    return StepResult(
                        step_name="parse_page",
                        success=False,
                        duration_ms=int((time.time() - start_time) * 1000),
                        error=f"Parser '{parser_name}' not found"
                    )

            # Validate page
            if not parser.validate_page(self.browser):
                return StepResult(
                    step_name="parse_page",
                    success=False,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=f"Page not compatible with {parser.name} parser"
                )

            # Execute parser
            parsed_data = parser.parse(self.browser)
            item_count = parsed_data.get("item_count", 0)

            # Verify minimum items
            if verify_min_items is not None:
                if item_count >= verify_min_items:
                    verifications.append(VerificationResult(
                        name="min_items",
                        status=VerificationStatus.PASSED,
                        message=f"Parsed {item_count} items (min: {verify_min_items})"
                    ))
                else:
                    verifications.append(VerificationResult(
                        name="min_items",
                        status=VerificationStatus.WARNING,
                        message=f"Parsed only {item_count} items (min: {verify_min_items})"
                    ))

            self.log(f"Parsed {item_count} items with {parser.name} parser", "SUCCESS")

            return StepResult(
                step_name="parse_page",
                success=True,
                duration_ms=int((time.time() - start_time) * 1000),
                data=parsed_data,
                verifications=verifications
            )

        except Exception as e:
            import traceback
            return StepResult(
                step_name="parse_page",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )

    def save_results(
        self,
        data: Any,
        filename: str,
        subfolder: Optional[str] = None
    ) -> StepResult:
        """
        Save results to a JSON file.

        Args:
            data: Data to save
            filename: Output filename (without path)
            subfolder: Optional subfolder within output_dir

        Returns:
            StepResult with file path
        """
        start_time = time.time()

        try:
            # Determine output path
            if subfolder:
                output_path = self.output_dir / subfolder
                output_path.mkdir(parents=True, exist_ok=True)
            else:
                output_path = self.output_dir

            filepath = output_path / filename

            # Save JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.log(f"Saved results to: {filepath}", "SUCCESS")

            return StepResult(
                step_name="save_results",
                success=True,
                duration_ms=int((time.time() - start_time) * 1000),
                data={"filepath": str(filepath.absolute())}
            )

        except Exception as e:
            return StepResult(
                step_name="save_results",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def wait(self, seconds: float):
        """Wait for specified seconds."""
        time.sleep(seconds)

    # ==================== Abstract Methods ====================

    @property
    @abstractmethod
    def name(self) -> str:
        """Workflow name."""
        pass

    @abstractmethod
    def run(self, **kwargs) -> WorkflowResult:
        """
        Execute the workflow.

        Returns:
            WorkflowResult with complete execution details
        """
        pass

    # ==================== Helper Methods ====================

    def _create_workflow_result(
        self,
        success: bool,
        start_time: datetime,
        summary: Dict,
        output_files: List[str]
    ) -> WorkflowResult:
        """Create a WorkflowResult object."""
        end_time = datetime.now()
        return WorkflowResult(
            workflow_name=self.name,
            success=success,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_duration_ms=int((end_time - start_time).total_seconds() * 1000),
            steps=self._steps,
            summary=summary,
            output_files=output_files,
            errors=self._errors
        )

    def _add_step(self, step: StepResult):
        """Add a step result to tracking."""
        self._steps.append(step)
        if not step.success and step.error:
            self._errors.append(f"{step.step_name}: {step.error}")

    def close(self):
        """Close browser and cleanup resources."""
        if self._browser:
            self._browser.close()
            self._browser = None
