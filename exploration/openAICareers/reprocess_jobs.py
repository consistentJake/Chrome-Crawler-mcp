#!/usr/bin/env python3
"""
Reprocess all OpenAI job HTML files and regenerate all_jobs_extracted.json.

This script:
1. Reads all HTML files from the jobs/ directory
2. Re-extracts job information using the updated extract_job_content function
3. Regenerates the all_jobs_extracted.json file with improved data
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from utils import extract_job_content


def get_original_info_from_json(json_path: Path, html_filename: str) -> Optional[Dict]:
    """
    Try to find the original job info from existing JSON file.

    Args:
        json_path: Path to all_jobs_extracted.json
        html_filename: HTML filename to match

    Returns:
        Original info dict if found, None otherwise
    """
    if not json_path.exists():
        return None

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for job in data.get('jobs', []):
            html_file = job.get('html_file', '')
            if html_file.endswith(html_filename):
                return job.get('original_info', {})

    except Exception:
        pass

    return None


def reprocess_html_files(jobs_dir: Path, output_file: Path, existing_json: Optional[Path] = None) -> Dict:
    """
    Reprocess all HTML files in the jobs directory.

    Args:
        jobs_dir: Directory containing job HTML files
        output_file: Path to output JSON file
        existing_json: Optional path to existing JSON for original_info lookup

    Returns:
        Dictionary with processing results
    """
    html_files = sorted(jobs_dir.glob('*.html'))
    print(f"Found {len(html_files)} HTML files to process")

    results = []
    failed = []

    for i, html_path in enumerate(html_files):
        print(f"[{i + 1}/{len(html_files)}] Processing: {html_path.name}")

        try:
            # Read HTML content
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Extract job content
            extracted_data = extract_job_content(html_content)

            # Try to get original info from existing JSON
            original_info = None
            if existing_json:
                original_info = get_original_info_from_json(existing_json, html_path.name)

            # Build original_info from extracted data if not found
            if not original_info:
                original_info = {
                    'title': extracted_data.get('title'),
                    'url': extracted_data.get('application_link', '').replace('/application', '') if extracted_data.get('application_link') else '',
                    'team': extracted_data.get('team'),
                }

            job_data = {
                'original_info': original_info,
                'extracted': extracted_data,
                'html_file': f"jobs/{html_path.name}",
                'scraped_at': datetime.now().isoformat()
            }

            results.append(job_data)

            # Print summary
            title = extracted_data.get('title', 'Unknown')
            locations = extracted_data.get('location', [])
            compensation = extracted_data.get('compensation', 'N/A')
            responsibilities_count = len(extracted_data.get('responsibilities', []))
            qualifications_count = len(extracted_data.get('qualifications', []))

            print(f"    Title: {title}")
            print(f"    Location: {', '.join(locations) if locations else 'N/A'}")
            print(f"    Compensation: {compensation}")
            print(f"    Responsibilities: {responsibilities_count} items")
            print(f"    Qualifications: {qualifications_count} items")

        except Exception as e:
            print(f"    [ERROR] {e}")
            failed.append({
                'file': html_path.name,
                'error': str(e)
            })

    # Build final output
    final_output = {
        'source': 'reprocessed_html_files',
        'processed_at': datetime.now().isoformat(),
        'total_files_processed': len(html_files),
        'total_jobs_extracted': len(results),
        'total_jobs_failed': len(failed),
        'jobs': results,
        'failed_jobs': failed
    }

    # Save to file
    print(f"\nSaving results to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print("REPROCESSING COMPLETE!")
    print(f"{'='*60}")
    print(f"Total files processed: {len(html_files)}")
    print(f"Successfully extracted: {len(results)}")
    print(f"Failed: {len(failed)}")
    print(f"Output saved to: {output_file}")

    return final_output


def main():
    """Main function to reprocess all job HTML files."""
    script_dir = Path(__file__).parent
    jobs_dir = script_dir / "jobs"
    output_file = script_dir / "all_jobs_extracted.json"
    existing_json = output_file if output_file.exists() else None

    if not jobs_dir.exists():
        print(f"Error: Jobs directory not found: {jobs_dir}")
        return

    reprocess_html_files(jobs_dir, output_file, existing_json)


if __name__ == '__main__':
    main()
