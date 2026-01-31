#!/usr/bin/env python3
"""
Extract job posting content from OpenAI career page HTML files.
"""

import json
from pathlib import Path
from bs4 import BeautifulSoup


def extract_job_content(html_file_path):
    """
    Extract structured job information from an OpenAI career page HTML file.

    Args:
        html_file_path: Path to the HTML file

    Returns:
        Dictionary containing extracted job information
    """
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract job information
    job_data = {
        'title': None,
        'location': None,
        'team': None,
        'about_the_team': None,
        'about_the_role': None,
        'responsibilities': [],
        'qualifications': [],
        'you_might_thrive': [],
        'compensation_and_benefits': None,
        'raw_text': None
    }

    # Extract title from page title or h1
    title_tag = soup.find('title')
    if title_tag:
        job_data['title'] = title_tag.get_text().replace(' | OpenAI', '').strip()

    # Extract main content - try to find the main job description area
    # Look for common OpenAI career page structure
    main_content = soup.find('main') or soup.find('body')

    if main_content:
        # Get all visible text
        text_content = main_content.get_text(separator='\n', strip=True)
        job_data['raw_text'] = text_content

        # Try to extract sections by looking for common headings
        sections = {
            'About the team': 'about_the_team',
            'About the role': 'about_the_role',
            'You might thrive in this role if you': 'you_might_thrive',
            'About OpenAI': 'about_openai',
            'Compensation and Benefits': 'compensation_and_benefits'
        }

        # Find all headings and their content
        all_text = text_content.split('\n')
        current_section = None
        section_content = []

        for line in all_text:
            line = line.strip()
            if not line:
                continue

            # Check if this line is a section header
            is_header = False
            for header, key in sections.items():
                if header.lower() in line.lower() and len(line) < 100:
                    # Save previous section
                    if current_section and section_content:
                        content_text = '\n'.join(section_content)
                        if current_section in ['about_the_team', 'about_the_role', 'compensation_and_benefits', 'about_openai']:
                            job_data[current_section] = content_text
                        elif current_section == 'you_might_thrive':
                            job_data['you_might_thrive'] = section_content

                    # Start new section
                    current_section = key
                    section_content = []
                    is_header = True
                    break

            if not is_header and current_section:
                section_content.append(line)

        # Save last section
        if current_section and section_content:
            content_text = '\n'.join(section_content)
            if current_section in ['about_the_team', 'about_the_role', 'compensation_and_benefits', 'about_openai']:
                job_data[current_section] = content_text
            elif current_section == 'you_might_thrive':
                job_data['you_might_thrive'] = section_content

    return job_data


def main():
    """Main function to extract job content."""
    # Path to the job HTML file
    html_file = Path(__file__).parent / 'jobs' / 'ai-social-risk-analyst.html'

    if not html_file.exists():
        print(f"Error: File not found: {html_file}")
        return

    print(f"Extracting content from: {html_file}")

    # Extract job data
    job_data = extract_job_content(html_file)

    # Save to JSON
    output_file = html_file.with_suffix('.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(job_data, f, indent=2, ensure_ascii=False)

    print(f"\nExtracted job data saved to: {output_file}")
    print(f"\nJob Title: {job_data['title']}")

    # Print summary
    print("\n" + "="*80)
    print("EXTRACTED CONTENT SUMMARY")
    print("="*80)

    for key, value in job_data.items():
        if key == 'raw_text':
            continue  # Skip raw text in summary
        if value:
            print(f"\n{key.upper().replace('_', ' ')}:")
            if isinstance(value, list):
                for item in value[:5]:  # Show first 5 items
                    print(f"  - {item}")
                if len(value) > 5:
                    print(f"  ... and {len(value) - 5} more items")
            else:
                # Show first 200 characters
                text = str(value)[:200]
                if len(str(value)) > 200:
                    text += "..."
                print(f"  {text}")


if __name__ == '__main__':
    main()
