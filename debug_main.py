#!/usr/bin/env python3
"""
Debug entry point for PyCharm debugging.
Loads configuration from .env.debug for easy debugging without command-line setup.

Features:
- Configurable via .env.debug file
- Parallel processing support
- Custom output directory
- All latest features (assessments, auto-categorization, etc.)

Setup:
1. Copy .env.debug.example to .env.debug
2. Edit .env.debug with your settings
3. Run this file in PyCharm debugger
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src directory to path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from yt_study_buddy.cli import YouTubeStudyNotes


def load_debug_config():
    """Load configuration from .env.debug file."""
    debug_env_path = current_dir / ".env.debug"

    if not debug_env_path.exists():
        print("=" * 70)
        print("WARNING: .env.debug not found!")
        print("=" * 70)
        print("Please create .env.debug from .env.debug.example:")
        print(f"  cp .env.debug.example .env.debug")
        print(f"  # Edit .env.debug with your settings")
        print("=" * 70)
        print("\nUsing default configuration...\n")
        return {}

    # Load .env.debug
    load_dotenv(debug_env_path)
    print(f"✓ Loaded configuration from: {debug_env_path}\n")
    return os.environ


def parse_bool(value, default=False):
    """Parse boolean from environment variable."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.lower() in ('true', '1', 'yes', 'on')


def parse_int(value, default):
    """Parse integer from environment variable."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def parse_urls(urls_string):
    """Parse comma-separated URLs."""
    if not urls_string:
        return []
    return [url.strip() for url in urls_string.split(',') if url.strip()]


def main():
    """
    Debug entry point with configuration from .env.debug.

    Configuration is loaded from .env.debug file.
    See .env.debug.example for available options.
    """

    # Load debug configuration
    env = load_debug_config()

    # Parse configuration with defaults
    output_dir = env.get('DEBUG_OUTPUT_DIR', 'notes_debug')
    subject = env.get('DEBUG_SUBJECT') or None
    global_context = parse_bool(env.get('DEBUG_GLOBAL_CONTEXT'), True)
    generate_assessments = parse_bool(env.get('DEBUG_GENERATE_ASSESSMENTS'), True)
    auto_categorize = parse_bool(env.get('DEBUG_AUTO_CATEGORIZE'), True)
    parallel = parse_bool(env.get('DEBUG_PARALLEL'), False)
    max_workers = parse_int(env.get('DEBUG_MAX_WORKERS'), 3)

    # URL configuration
    url_file = env.get('DEBUG_URL_FILE')
    urls_string = env.get('DEBUG_URLS', '')

    # Display configuration
    print("=" * 70)
    print("DEBUG MODE - YouTube Study Buddy")
    print("=" * 70)
    print(f"Output Directory:    {output_dir}")
    print(f"Subject:             {subject or 'Auto-detect'}")
    print(f"Global Context:      {'Enabled' if global_context else 'Subject-only'}")
    print(f"Assessments:         {'Enabled' if generate_assessments else 'Disabled'}")
    print(f"Auto-categorize:     {'Enabled' if auto_categorize else 'Disabled'}")
    print(f"Parallel Processing: {'Enabled' if parallel else 'Disabled'}")
    if parallel:
        print(f"Max Workers:         {max_workers}")
    print(f"Transcript Provider: Tor (exclusive)")
    print("=" * 70)

    # Check for API key
    api_key = env.get('CLAUDE_API_KEY') or env.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("\n❌ ERROR: CLAUDE_API_KEY not found in .env.debug")
        print("Please set CLAUDE_API_KEY in your .env.debug file")
        sys.exit(1)

    # Create app instance
    app = YouTubeStudyNotes(
        subject=subject,
        global_context=global_context,
        base_dir=output_dir,
        generate_assessments=generate_assessments,
        auto_categorize=auto_categorize and not subject,
        parallel=parallel,
        max_workers=max_workers
    )

    # Get URLs to process
    urls_to_process = []

    if url_file:
        # Load from file
        print(f"\n📄 Reading URLs from file: {url_file}")
        urls_to_process = app.read_urls_from_file(url_file)
        if not urls_to_process:
            print(f"❌ No URLs found in {url_file}")
            print("Please check the file exists and contains valid YouTube URLs")
            sys.exit(1)
        print(f"✓ Loaded {len(urls_to_process)} URLs from file\n")

    elif urls_string:
        # Parse from DEBUG_URLS
        urls_to_process = parse_urls(urls_string)
        if not urls_to_process:
            print("❌ No valid URLs found in DEBUG_URLS")
            print("Please set DEBUG_URLS in .env.debug (comma-separated)")
            sys.exit(1)
        print(f"\n📋 Processing {len(urls_to_process)} URL(s) from DEBUG_URLS\n")

    else:
        print("\n❌ No URLs configured!")
        print("Please set either:")
        print("  - DEBUG_URLS=url1,url2,url3")
        print("  - DEBUG_URL_FILE=urls.txt")
        print("in your .env.debug file")
        sys.exit(1)

    # Display URLs
    print("URLs to process:")
    for i, url in enumerate(urls_to_process, 1):
        print(f"  {i}. {url}")
    print()

    # Process URLs
    try:
        app.process_urls(urls_to_process)
        print("\n✓ Debug session completed successfully!")
    except KeyboardInterrupt:
        print("\n\n⚠ Debug session interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during processing: {e}")
        raise


if __name__ == "__main__":
    main()
