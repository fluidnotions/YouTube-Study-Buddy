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

from main import YouTubeStudyNotes


def main():
    """
    Debug entry point with predefined configuration.

    Modify the DEBUG_CONFIG section below to set your debug parameters.
    """

    # ==================== DEBUG CONFIGURATION ====================
    # Modify these values for your debug session

    # Debug mode - choose one:
    DEBUG_MODE = "single_url"  # Options: "single_url", "batch", "interactive"

    # Single URL mode settings:
    DEBUG_URL = "https://youtu.be/8w7mv0zjdUg?list=PL4MBLJ9EJIVaMPEU6_FSGdQlorDfU-7VM"  # Replace with your test URL

    # Batch mode settings:
    DEBUG_BATCH_FILE = "urls.txt"  # File containing URLs for batch processing

    # Subject/Organization settings:
    DEBUG_SUBJECT = None  # e.g., "Python", "Machine Learning", None for auto-categorize
    DEBUG_SUBJECT_ONLY = False  # True = cross-reference within subject only

    # Provider settings:
    DEBUG_PROVIDER = "tor"  # Options: "api", "scraper", "tor"

    # Tor settings (only used if DEBUG_PROVIDER = "tor"):
    DEBUG_TOR_HOST = "127.0.0.1"
    DEBUG_TOR_PORT = 9050
    DEBUG_TOR_FALLBACK = True  # Allow fallback to direct connection

    # Feature flags:
    DEBUG_GENERATE_ASSESSMENTS = True
    DEBUG_AUTO_CATEGORIZE = True  # Auto-categorize when no subject specified

    # =============================================================

    print("=" * 60)
    print("DEBUG MODE - YT Study Buddy")
    print("=" * 60)
    print(f"Mode: {DEBUG_MODE}")
    print(f"Subject: {DEBUG_SUBJECT or 'Auto-detect'}")
    print(f"Provider: {DEBUG_PROVIDER}")
    print(f"Assessments: {'Enabled' if DEBUG_GENERATE_ASSESSMENTS else 'Disabled'}")
    print(f"Auto-categorize: {'Enabled' if DEBUG_AUTO_CATEGORIZE else 'Disabled'}")
    print("=" * 60)

    # Build provider kwargs
    provider_kwargs = {}
    if DEBUG_PROVIDER == "tor":
        provider_kwargs['tor_host'] = DEBUG_TOR_HOST
        provider_kwargs['tor_port'] = DEBUG_TOR_PORT
        provider_kwargs['use_tor_first'] = DEBUG_TOR_FALLBACK

    # Create app instance
    app = YouTubeStudyNotes(
        subject=DEBUG_SUBJECT,
        global_context=not DEBUG_SUBJECT_ONLY,
        provider_type=DEBUG_PROVIDER,
        generate_assessments=DEBUG_GENERATE_ASSESSMENTS,
        auto_categorize=DEBUG_AUTO_CATEGORIZE and not DEBUG_SUBJECT
    )

    # Update provider with kwargs if needed
    if provider_kwargs:
        from yt_study_buddy.video_processor import VideoProcessor
        app.video_processor = VideoProcessor(DEBUG_PROVIDER, **provider_kwargs)

    # Run based on debug mode
    if DEBUG_MODE == "single_url":
        print(f"\nProcessing single URL: {DEBUG_URL}\n")
        app.process_single_url(DEBUG_URL)

    elif DEBUG_MODE == "batch":
        print(f"\nProcessing batch from file: {DEBUG_BATCH_FILE}\n")
        app.process_urls_from_file(DEBUG_BATCH_FILE)

    elif DEBUG_MODE == "interactive":
        print("\nStarting interactive mode...\n")
        app.run_interactive()

    else:
        print(f"\nERROR: Unknown DEBUG_MODE: {DEBUG_MODE}")
        print("Valid options: 'single_url', 'batch', 'interactive'")
        sys.exit(1)


if __name__ == "__main__":
    main()
