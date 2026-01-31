#!/usr/bin/env python3
"""
Utility functions for OpenAI job scraping and processing.
"""

import re
from typing import Dict, List, Optional, Set
from bs4 import BeautifulSoup


def extract_job_content(html_content: str) -> Dict:
    """
    Extract structured job information from HTML content.

    Args:
        html_content: Raw HTML of job page

    Returns:
        Dictionary containing extracted job information
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    job_data = {
        'title': None,
        'location': [],  # Changed to list for multiple locations
        'team': None,
        'application_link': None,
        'about_the_team': None,
        'about_the_role': None,
        'responsibilities': [],
        'qualifications': [],
        'you_might_thrive': [],
        'about_openai': None,
        'compensation': None,
    }

    # Extract title from page title
    title_tag = soup.find('title')
    if title_tag:
        job_data['title'] = title_tag.get_text().replace(' | OpenAI', '').strip()

    # Extract team and location from the header area
    # Pattern: "Team - Location1 and Location2" in p.text-primary-100
    for p in soup.find_all('p', class_=re.compile(r'text-primary-100')):
        text = p.get_text().strip()
        # Skip "Careers" text
        if text == 'Careers':
            continue
        # Parse "Team - Location" format
        if ' - ' in text:
            parts = text.split(' - ', 1)
            job_data['team'] = parts[0].strip()
            location_str = parts[1].strip()
            # Parse locations (can be "Location1 and Location2" or "Location1, Location2")
            locations = _parse_locations(location_str)
            job_data['location'] = locations
            break

    # Extract application link
    for a in soup.find_all('a', href=re.compile(r'jobs\.ashbyhq\.com.*application')):
        job_data['application_link'] = a.get('href')
        break

    # Get main content and extract text
    main_content = soup.find('main') or soup.find('body')

    if main_content:
        text_content = main_content.get_text(separator='\n', strip=True)

        # Extract location and team from header area
        lines = text_content.split('\n')

        # Define sections to extract - now includes Responsibilities and Qualifications
        sections = {
            'About the team': 'about_the_team',
            'About the role': 'about_the_role',
            'Overview:': 'about_the_role',  # Some pages use Overview instead
            'Responsibilities:': 'responsibilities',
            'Responsibilities': 'responsibilities',
            'Qualifications:': 'qualifications',
            'Qualifications': 'qualifications',
            'You might thrive in this role if you': 'you_might_thrive',
            'About OpenAI': 'about_openai',
        }

        current_section = None
        section_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line is a section header
            is_header = False
            for header, key in sections.items():
                if header.lower() in line.lower() and len(line) < 100:
                    # Save previous section
                    if current_section and section_content:
                        _save_section(job_data, current_section, section_content)

                    # Start new section
                    current_section = key
                    section_content = []
                    is_header = True
                    break

            if not is_header and current_section:
                section_content.append(line)

            # Extract compensation (appears near the end)
            if 'Compensation' in line or '$' in line:
                # Look for salary pattern like "$220K – $320K"
                salary_match = re.search(r'\$[\d,]+K?\s*[–-]\s*\$[\d,]+K?', line)
                if salary_match:
                    job_data['compensation'] = salary_match.group(0)

        # Save last section
        if current_section and section_content:
            _save_section(job_data, current_section, section_content)

        # Try to extract compensation from raw text if not found
        if not job_data['compensation']:
            comp_match = re.search(
                r'\$[\d,]+K?\s*[–-]\s*\$[\d,]+K?(?:\s*\+?\s*(?:Offers\s+)?Equity)?',
                text_content
            )
            if comp_match:
                job_data['compensation'] = comp_match.group(0)

    return job_data


def _parse_locations(location_str: str) -> List[str]:
    """
    Parse location string into a list of individual locations.

    Examples:
        "Seattle and San Francisco" -> ["Seattle", "San Francisco"]
        "San Francisco, Seattle, New York" -> ["San Francisco", "Seattle", "New York"]
        "Remote" -> ["Remote"]

    Args:
        location_str: Raw location string

    Returns:
        List of individual location names
    """
    if not location_str:
        return []

    # First split by " and "
    parts = []
    for part in re.split(r'\s+and\s+', location_str, flags=re.IGNORECASE):
        # Then split by comma
        for subpart in part.split(','):
            loc = subpart.strip()
            if loc:
                parts.append(loc)

    return parts


def _save_section(job_data: Dict, section_key: str, content: List[str]) -> None:
    """
    Save section content to job_data dictionary.

    Args:
        job_data: Dictionary to update
        section_key: Key name for the section
        content: List of lines for this section
    """
    content_text = '\n'.join(content)

    if section_key in ['about_the_team', 'about_the_role', 'about_openai']:
        job_data[section_key] = content_text
    elif section_key in ['you_might_thrive', 'responsibilities', 'qualifications']:
        job_data[section_key] = content


def extract_skills(text: str) -> Set[str]:
    """
    Extract skills and technologies mentioned in text.

    Args:
        text: Job description text to analyze

    Returns:
        Set of skill names (lowercase)
    """
    if not text:
        return set()

    text_lower = text.lower()
    skills_found = set()

    # Define skill patterns with their canonical names
    skill_patterns = {
        # Programming Languages
        'python': r'\bpython\b',
        'go/golang': r'\b(?:go|golang)\b',
        'rust': r'\brust\b',
        'typescript': r'\btypescript\b',
        'javascript': r'\bjavascript\b',
        'java': r'\bjava\b(?!script)',
        'c++': r'\bc\+\+\b',
        'sql': r'\bsql\b',
        'scala': r'\bscala\b',
        'ruby': r'\bruby\b',

        # ML/AI
        'machine learning': r'\bmachine\s+learning\b',
        'deep learning': r'\bdeep\s+learning\b',
        'ai/ml': r'\bai/?ml\b|\bml/?ai\b|\bai\s+(?:and|&)\s+ml\b|\bml\s+(?:and|&)\s+ai\b',
        'ai systems': r'\bai\s+system(?:s)?\b',
        'llm': r'\bllm(?:s)?\b',
        'nlp': r'\bnlp\b|\bnatural\s+language\s+processing\b',
        'pytorch': r'\bpytorch\b',
        'tensorflow': r'\btensorflow\b',
        'reinforcement learning': r'\breinforcement\s+learning\b',
        'computer vision': r'\bcomputer\s+vision\b',

        # Infrastructure/DevOps
        'kubernetes': r'\bkubernetes\b|\bk8s\b',
        'docker': r'\bdocker\b',
        'aws': r'\baws\b|\bamazon\s+web\s+services\b',
        'gcp': r'\bgcp\b|\bgoogle\s+cloud\b',
        'azure': r'\bazure\b',
        'linux': r'\blinux\b',
        'ci/cd': r'\bci/?cd\b',
        'terraform': r'\bterraform\b',

        # Databases
        'postgresql': r'\bpostgres(?:ql)?\b',
        'mysql': r'\bmysql\b',
        'mongodb': r'\bmongodb\b',
        'redis': r'\bredis\b',
        'elasticsearch': r'\belasticsearch\b',

        # Data Engineering
        'spark': r'\bspark\b',
        'kafka': r'\bkafka\b',
        'airflow': r'\bairflow\b',
        'data pipelines': r'\bdata\s+pipeline(?:s)?\b',
        'data infrastructure': r'\bdata\s+infrastructure\b',
        'etl': r'\betl\b',

        # Web/API
        'react': r'\breact(?:\.?js)?\b',
        'node.js': r'\bnode(?:\.?js)?\b',
        'fastapi': r'\bfastapi\b',
        'graphql': r'\bgraphql\b',
        'rest api': r'\brest(?:ful)?\s*api(?:s)?\b',

        # Architecture/Concepts
        'distributed systems': r'\bdistributed\s+systems?\b',
        'microservices': r'\bmicroservices?\b',
        'system design': r'\bsystem\s+design\b',
        'backend': r'\bbackend\b|\bback-end\b',
        'frontend': r'\bfrontend\b|\bfront-end\b',
        'full-stack': r'\bfull[-\s]?stack\b',

        # Ads/Growth
        'ads': r'\bads\b|\badvertis(?:ing|ement)?\b',
        'ads system': r'\bads?\s+system(?:s)?\b|\badvertising\s+system(?:s)?\b',

        # Soft Skills / Domains
        'a/b testing': r'\ba/?b\s+test(?:ing)?\b',
        'data analysis': r'\bdata\s+analysis\b',
        'security': r'\bsecurity\b',
        'networking': r'\bnetworking\b',
    }

    for skill_name, pattern in skill_patterns.items():
        if re.search(pattern, text_lower):
            skills_found.add(skill_name)

    return skills_found
