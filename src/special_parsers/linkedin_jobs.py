"""
LinkedIn Jobs Parser
Extracts structured job listing data from LinkedIn Jobs search pages.
"""

from datetime import datetime
from typing import Dict, List, Any
from .base import BaseParser

class LinkedInJobsParser(BaseParser):
    """
    Parser for LinkedIn Jobs search pages.

    Supports:
    - Job search results
    - Company job listings
    - Filtered job searches

    Extracts:
    - Job ID, title, URL
    - Company name and logo
    - Location
    - Salary range (if available)
    - Job insights (alumni count, etc.)
    - Application status (Viewed, Applied, etc.)
    """

    name = "linkedin-jobs"
    description = "Extracts job listings with title, company, location, salary, and metadata"
    version = "1.0.0"

    def parse(self, browser_client) -> Dict[str, Any]:
        """
        Extract job listings from current LinkedIn Jobs page.

        Args:
            browser_client: BrowserIntegration instance

        Returns:
            Structured job listing data
        """
        import re
        import json

        # Get current URL
        url = browser_client.get_current_url()
        page_title = browser_client.get_page_title()

        start_time = datetime.now()

        # Use chrome_get_web_content to get HTML and parse it in Python
        # This is more reliable than browser_evaluate for Chrome MCP
        html_result = browser_client.playwright_client.get_html_content()
        end_time = datetime.now()

        # Extract HTML from nested response
        html = self._extract_html_from_response(html_result)

        # Parse job data from HTML using Python regex
        extraction_result = self._parse_html_for_jobs(html)

        # Build structured output
        jobs = extraction_result.get('jobs', [])
        search_info = extraction_result.get('search_info', {})
        pagination = extraction_result.get('pagination', {})

        return {
            "parser": self.name,
            "parser_version": self.version,
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "item_count": len(jobs),
            "items": jobs,
            "metadata": {
                "page_title": page_title,
                "extraction_time_ms": int((end_time - start_time).total_seconds() * 1000),
                "search_query": search_info.get('keywords', ''),
                "location_filter": search_info.get('location', ''),
                "total_results": search_info.get('total_results', 0),
            },
            "pagination": pagination
        }

    def get_extraction_js(self) -> str:
        """
        JavaScript code to extract job listings from DOM.
        """
        return r"""
        () => {
          try {
            // Extract search info from the page
            const extractSearchInfo = () => {
              const info = {
                keywords: '',
                location: '',
                total_results: 0
              };

              // Get search keywords from input
              const keywordsInput = document.querySelector('input[aria-label*="Search"]') ||
                                   document.querySelector('input[placeholder*="Search"]');
              if (keywordsInput) {
                info.keywords = keywordsInput.value || '';
              }

              // Get location from input
              const locationInput = document.querySelector('input[aria-label*="location"]') ||
                                   document.querySelector('input[placeholder*="location"]');
              if (locationInput) {
                info.location = locationInput.value || '';
              }

              // Get total results count from page title or subtitle
              const titleText = document.title || '';
              const resultsMatch = titleText.match(/\((\d+)\)/);
              if (resultsMatch) {
                info.total_results = parseInt(resultsMatch[1], 10);
              }

              return info;
            };

            // Extract a single job card
            const extractJobCard = (card) => {
              try {
                // Get job ID from data attribute
                const jobId = card.getAttribute('data-job-id') || '';

                // Get job title and URL
                const titleLink = card.querySelector('.job-card-container__link, .job-card-list__title--link, a[href*="/jobs/view/"]');
                let title = '';
                let jobUrl = '';

                if (titleLink) {
                  // Clean the title text (remove SVG icons and extra whitespace)
                  title = titleLink.textContent
                    .replace(/\[SVG Icon\]/g, '')
                    .replace(/with verification/gi, '')
                    .replace(/\s+/g, ' ')
                    .trim();
                  jobUrl = titleLink.getAttribute('href') || '';
                  if (jobUrl && !jobUrl.startsWith('http')) {
                    jobUrl = 'https://www.linkedin.com' + jobUrl;
                  }
                }

                // Get company name
                const companyEl = card.querySelector('.artdeco-entity-lockup__subtitle span, .job-card-container__primary-description');
                const company = companyEl ? companyEl.textContent.trim() : '';

                // Get location
                const locationEl = card.querySelector('.artdeco-entity-lockup__caption li span, .job-card-container__metadata-item');
                const location = locationEl ? locationEl.textContent.trim() : '';

                // Get salary (if available)
                const salaryEl = card.querySelector('.artdeco-entity-lockup__metadata li span');
                let salary = '';
                if (salaryEl) {
                  const salaryText = salaryEl.textContent.trim();
                  // Check if it looks like a salary (contains $ or /yr or /hr)
                  if (salaryText.includes('$') || salaryText.includes('/yr') || salaryText.includes('/hr')) {
                    salary = salaryText;
                  }
                }

                // Get job insight (alumni count, etc.)
                const insightEl = card.querySelector('.job-card-container__job-insight-text');
                let insight = '';
                if (insightEl) {
                  insight = insightEl.textContent.replace(/\s+/g, ' ').trim();
                }

                // Get application status (Viewed, Applied, etc.)
                const statusEl = card.querySelector('.job-card-container__footer-job-state');
                const status = statusEl ? statusEl.textContent.trim() : '';

                // Get company logo URL
                const logoEl = card.querySelector('.job-card-list__logo img, .artdeco-entity-lockup__image img');
                const logoUrl = logoEl ? logoEl.getAttribute('src') : '';

                // Get posted time (if available)
                const timeEl = card.querySelector('.job-card-container__listed-time, time');
                const postedTime = timeEl ? timeEl.textContent.trim() : '';

                // Check if job is promoted/sponsored
                const isPromoted = card.querySelector('.job-card-container__footer-item--promoted') !== null;

                // Check if Easy Apply is available
                const hasEasyApply = card.textContent.includes('Easy Apply');

                return {
                  job_id: jobId,
                  title: title,
                  company: company,
                  location: location,
                  salary: salary,
                  insight: insight,
                  status: status,
                  logo_url: logoUrl,
                  job_url: jobUrl,
                  posted_time: postedTime,
                  is_promoted: isPromoted,
                  has_easy_apply: hasEasyApply
                };
              } catch (err) {
                return {
                  error: err.message,
                  stack: err.stack
                };
              }
            };

            // Extract pagination info
            const extractPagination = () => {
              const pagination = {
                current_page: 1,
                total_pages: 1,
                has_next_page: false,
                next_page_url: null
              };

              // Look for active page button
              const activePageBtn = document.querySelector('button[aria-current="true"], .artdeco-pagination__indicator--number.active');
              if (activePageBtn) {
                pagination.current_page = parseInt(activePageBtn.textContent.trim(), 10) || 1;
              }

              // Look for all page buttons to get total pages
              const pageButtons = document.querySelectorAll('.artdeco-pagination__indicator--number button, button[aria-label*="Page"]');
              let maxPage = pagination.current_page;
              pageButtons.forEach(btn => {
                const pageNum = parseInt(btn.textContent.trim(), 10);
                if (!isNaN(pageNum) && pageNum > maxPage) {
                  maxPage = pageNum;
                }
              });
              pagination.total_pages = maxPage;

              // Check for next button
              const nextBtn = document.querySelector('button[aria-label*="Next"], button[aria-label*="next"]');
              if (nextBtn && !nextBtn.disabled) {
                pagination.has_next_page = true;
              }

              return pagination;
            };

            // Find all job cards
            const jobCards = document.querySelectorAll('[data-job-id]');
            const jobs = [];

            jobCards.forEach(card => {
              const job = extractJobCard(card);
              // Only include valid jobs with ID and title
              if (job.job_id && job.title && !job.error) {
                jobs.push(job);
              }
            });

            // Deduplicate jobs by job_id
            const seenIds = new Set();
            const uniqueJobs = jobs.filter(job => {
              if (seenIds.has(job.job_id)) {
                return false;
              }
              seenIds.add(job.job_id);
              return true;
            });

            // Extract search info and pagination
            const searchInfo = extractSearchInfo();
            const pagination = extractPagination();

            return {
              jobs: uniqueJobs,
              search_info: searchInfo,
              pagination: pagination,
              total_cards_found: jobCards.length,
              unique_jobs: uniqueJobs.length,
              extraction_timestamp: new Date().toISOString()
            };

          } catch (err) {
            return {
              error: err.message,
              stack: err.stack
            };
          }
        }
        """

    def _extract_html_from_response(self, result: Dict) -> str:
        """
        Extract HTML content from Chrome MCP response.
        Handles the nested JSON structure.
        """
        import json

        if result.get("status") != "success":
            raise RuntimeError(f"Failed to get HTML: {result.get('message', 'Unknown error')}")

        # Try to extract from nested structure
        result_data = result.get("data") or result.get("result", {})
        if isinstance(result_data, dict) and "content" in result_data:
            content_list = result_data.get("content", [])
            if isinstance(content_list, list) and len(content_list) > 0:
                text = content_list[0].get("text", "{}")
                try:
                    outer_data = json.loads(text)
                    inner_content = outer_data.get("data", {}).get("content", [])
                    if inner_content:
                        inner_text = inner_content[0].get("text", "{}")
                        inner_data = json.loads(inner_text)
                        return inner_data.get("htmlContent", "")
                except json.JSONDecodeError:
                    pass

        return ""

    def _parse_html_for_jobs(self, html: str) -> Dict[str, Any]:
        """
        Parse job listings from HTML using Python regex.
        This is more reliable than JavaScript evaluation for Chrome MCP.
        """
        import re

        jobs = []

        # Find all job card blocks by data-job-id
        job_card_pattern = r'data-job-id="(\d+)"[^>]*class="[^"]*job-card-container[^"]*"[^>]*>(.*?)(?=data-job-id="|</ul>)'
        job_cards = re.findall(job_card_pattern, html, re.DOTALL)

        for job_id, card_content in job_cards:
            job_info = {"job_id": job_id}

            # Extract title
            title_match = re.search(r'<strong>([^<]+)</strong>', card_content)
            job_info["title"] = self._clean_html_text(title_match.group(1)) if title_match else ""

            # Extract company
            company_match = re.search(r'artdeco-entity-lockup__subtitle[^>]*>.*?<span[^>]*dir="ltr"[^>]*>\s*([^<\n]+)', card_content, re.DOTALL)
            job_info["company"] = self._clean_html_text(company_match.group(1)) if company_match else ""

            # Extract location
            location_match = re.search(r'artdeco-entity-lockup__caption[^>]*>.*?<span[^>]*dir="ltr"[^>]*>\s*([^<\n]+)', card_content, re.DOTALL)
            job_info["location"] = self._clean_html_text(location_match.group(1)) if location_match else ""

            # Extract salary (in metadata)
            salary_match = re.search(r'artdeco-entity-lockup__metadata[^>]*>.*?<span[^>]*dir="ltr"[^>]*>\s*(\$[^<\n]+)', card_content, re.DOTALL)
            job_info["salary"] = self._clean_html_text(salary_match.group(1)) if salary_match else ""

            # Extract status (Viewed, Applied, etc.)
            status_match = re.search(r'job-card-container__footer-job-state[^>]*>\s*([^<\n]+)', card_content)
            job_info["status"] = self._clean_html_text(status_match.group(1)) if status_match else ""

            # Extract insight (alumni info)
            insight_match = re.search(r'job-card-container__job-insight-text[^>]*dir="ltr"[^>]*>\s*<span[^>]*>([^<]+)', card_content)
            job_info["insight"] = self._clean_html_text(insight_match.group(1)) if insight_match else ""

            # Build job URL
            job_info["job_url"] = f"https://www.linkedin.com/jobs/view/{job_id}/"

            if job_info["job_id"] and job_info["title"]:
                jobs.append(job_info)

        # Extract search info from page
        search_info = {}
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            title = title_match.group(1)
            results_match = re.search(r'\((\d+)\)', title)
            if results_match:
                search_info["total_results"] = int(results_match.group(1))

        return {
            "jobs": jobs,
            "search_info": search_info,
            "pagination": {"current_page": 1}
        }

    def _clean_html_text(self, text: str) -> str:
        """Clean HTML entities and whitespace from text."""
        import html
        if not text:
            return ""
        # Decode HTML entities
        text = html.unescape(text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text.strip()

    def validate_page(self, browser_client) -> bool:
        """Check if current page is a valid LinkedIn Jobs page"""
        url = browser_client.get_current_url()
        return 'linkedin.com/jobs' in url
