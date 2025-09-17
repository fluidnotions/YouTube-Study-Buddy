"""CLI entry point for YT Study Buddy."""

import sys
import os

# Add the parent directory to the path so we can import from the main module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from main import YouTubeStudyNotes


def main():
    """Main CLI entry point."""
    app = YouTubeStudyNotes()
    app.main()


if __name__ == "__main__":
    main()