#!/usr/bin/env python3
"""
Debug entry point for PyCharm debugging.
Provides predefined arguments for easy debugging without command-line setup.
"""
import sys
import os
from pathlib import Path

# Add src directory to path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from yt_study_buddy.cli import YouTubeStudyNotes


def main():
    """
    Debug entry point with predefined configuration.

    Modify the DEBUG_CONFIG section below to set your debug parameters.
    """

    # ==================== DEBUG CONFIGURATION ====================
    # Modify these values for your debug session

    # URLs to process - can be a list or single URL
    DEBUG_URLS = [
        "https://youtu.be/8w7mv0zjdUg?list=PL4MBLJ9EJIVaMPEU6_FSGdQlorDfU-7VM",
        # Add more URLs here for testing
    ]

    # Or read from file instead (set to filename or None)
    DEBUG_FILE = None  # e.g., "urls.txt" or None

    # Subject/Organization settings:
    DEBUG_SUBJECT = None  # e.g., "Python", "Machine Learning", None for auto-categorize
    DEBUG_SUBJECT_ONLY = False  # True = cross-reference within subject only

    # Note: Transcript provider is now Tor-only (no configuration needed)

    # Feature flags:
    DEBUG_GENERATE_ASSESSMENTS = True
    DEBUG_AUTO_CATEGORIZE = True  # Auto-categorize when no subject specified

    # =============================================================

    print("=" * 60)
    print("DEBUG MODE - YouTube Study Buddy")
    print("=" * 60)
    print(f"Subject: {DEBUG_SUBJECT or 'Auto-detect'}")
    print(f"Provider: Tor (only option)")
    print(f"Assessments: {'Enabled' if DEBUG_GENERATE_ASSESSMENTS else 'Disabled'}")
    print(f"Auto-categorize: {'Enabled' if DEBUG_AUTO_CATEGORIZE else 'Disabled'}")
    print("=" * 60)

    # Create app instance
    app = YouTubeStudyNotes(
        subject=DEBUG_SUBJECT,
        global_context=not DEBUG_SUBJECT_ONLY,
        generate_assessments=DEBUG_GENERATE_ASSESSMENTS,
        auto_categorize=DEBUG_AUTO_CATEGORIZE and not DEBUG_SUBJECT
    )

    # Get URLs to process
    urls_to_process = []
    if DEBUG_FILE:
        print(f"\nReading URLs from file: {DEBUG_FILE}\n")
        urls_to_process = app.read_urls_from_file(DEBUG_FILE)
    else:
        print(f"\nProcessing {len(DEBUG_URLS)} URL(s)\n")
        urls_to_process = DEBUG_URLS

    # Process URLs
    app.process_urls(urls_to_process)


if __name__ == "__main__":
    main()
