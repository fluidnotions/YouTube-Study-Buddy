#!/usr/bin/env python3
"""
Debug wrapper for CLI - easily debug any CLI command.

Usage:
    1. Edit the CLI_ARGS list below with your desired arguments
    2. Set breakpoints in any file (cli.py, tor_transcript_fetcher.py, etc.)
    3. Right-click this file → Debug 'debug_cli'

Examples of CLI_ARGS:
    ['https://youtube.com/watch?v=dQw4w9WgXcQ']
    ['--parallel', '--workers', '3', '--file', 'urls.txt']
    ['--subject', 'Python', 'https://youtube.com/watch?v=xyz']
    ['--help']
"""
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from yt_study_buddy.cli import main

# ============================================================
# EDIT THIS SECTION TO TEST DIFFERENT CLI COMMANDS
# ============================================================


CLI_ARGS = [
    '--debug-logging',
    '--parallel',
    '--workers', '3',
    '--export-pdf',
    'https://youtu.be/2VauS2awvMw',
    'https://youtu.be/3le-v1Pme44',
    'https://youtu.be/g80Q1sVtikE'
]

def debug_with_args(args):
    """
    Run the CLI with specified arguments.

    This simulates: uv run yt-study-buddy <args>
    """
    print("=" * 60)
    print("DEBUG MODE - CLI Arguments:")
    print(f"  {' '.join(args)}")
    print("=" * 60)
    print()

    # Set sys.argv to simulate CLI execution
    sys.argv = ['yt-study-buddy'] + args

    # Run the CLI (set breakpoints in cli.py or other files)
    main()


if __name__ == '__main__':
    debug_with_args(CLI_ARGS)
