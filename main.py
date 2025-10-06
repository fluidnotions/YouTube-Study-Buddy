#!/usr/bin/env python3
"""
Legacy entry point for YouTube Study Buddy.
For new installations, use: uv run youtube-study-buddy

This file remains for backward compatibility with existing scripts.
"""
import sys
from pathlib import Path

# Add src directory to path for development mode
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from yt_study_buddy.cli import main

if __name__ == "__main__":
    main()
