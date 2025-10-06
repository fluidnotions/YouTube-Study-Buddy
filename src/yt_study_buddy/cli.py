"""
Command-line interface for YouTube Study Buddy.

Usage:
    youtube-study-buddy <url1> <url2> ...
    youtube-study-buddy --file urls.txt
    youtube-study-buddy --subject "Topic" <url1> <url2>
"""

import sys
import os
import argparse
import time

from .video_processor import VideoProcessor
from .knowledge_graph import KnowledgeGraph
from .study_notes_generator import StudyNotesGenerator
from .obsidian_linker import ObsidianLinker
from .auto_categorizer import AutoCategorizer
from .assessment_generator import AssessmentGenerator


class YouTubeStudyNotes:
    """Main application class for processing YouTube videos into study notes."""

    def __init__(self, subject=None, global_context=True, base_dir="Study notes",
                 generate_assessments=True, auto_categorize=True):
        self.subject = subject
        self.global_context = global_context
        self.base_dir = base_dir
        self.output_dir = os.path.join(base_dir, subject) if subject else base_dir
        self.generate_assessments = generate_assessments
        self.auto_categorize = auto_categorize and not subject  # Only auto-categorize when no subject provided

        self.video_processor = VideoProcessor("tor")
        self.knowledge_graph = KnowledgeGraph(base_dir, subject, global_context)
        self.notes_generator = StudyNotesGenerator()
        self.obsidian_linker = ObsidianLinker(base_dir, subject, global_context)

        # Initialize new components
        self.auto_categorizer = AutoCategorizer() if self.auto_categorize else None
        self.assessment_generator = AssessmentGenerator(self.notes_generator.client) if generate_assessments else None

    def read_urls_from_file(self, filename='urls.txt'):
        """Read URLs from a text file, ignoring comments and empty lines."""
        urls = []
        if not os.path.exists(filename):
            return urls

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        urls.append(line)
        except Exception as e:
            print(f"Warning: Could not read {filename}: {e}")

        return urls

    def process_single_url(self, url):
        """Process a single YouTube URL and generate study notes."""
        # Extract video ID
        video_id = self.video_processor.get_video_id(url)
        if not video_id:
            print(f"ERROR: Invalid YouTube URL: {url}")
            return False

        print(f"\nFound video ID: {video_id}")
        if self.subject:
            print(f"Subject: {self.subject}")
            print(f"Cross-reference scope: {'Global' if self.global_context else 'Subject-only'}")

        try:
            # Get transcript
            print("Fetching transcript from YouTube via Tor...")
            transcript_data = self.video_processor.get_transcript(video_id)
            transcript = transcript_data['transcript']

            if transcript_data['duration']:
                print(f"Video duration: {transcript_data['duration']}")
            print(f"Transcript length: {transcript_data['length']} characters")

            # Get video title
            print("Fetching video title...")
            video_title = self.video_processor.get_video_title(video_id)

            # Auto-categorize if no subject provided
            if self.auto_categorizer and not self.subject:
                print("Auto-categorizing video content...")
                detected_subject = self.auto_categorizer.categorize_video(
                    transcript, video_title, self.base_dir
                )
                print(f"Detected subject: {detected_subject}")

                # Update subject and output directory
                self.subject = detected_subject
                self.output_dir = os.path.join(self.base_dir, detected_subject)

                # Update components with new subject
                self.knowledge_graph = KnowledgeGraph(self.base_dir, detected_subject, self.global_context)
                self.obsidian_linker = ObsidianLinker(self.base_dir, detected_subject, self.global_context)

            # Ensure output directory exists
            os.makedirs(self.output_dir, exist_ok=True)

            # Generate study notes with Claude
            print("Generating study notes with Claude AI...")
            study_notes = self.notes_generator.generate_notes(
                transcript=transcript,
                video_title=video_title,
                video_url=url
            )

            # Add cross-references using knowledge graph
            print("Adding cross-references to related notes...")
            linked_notes = self.obsidian_linker.add_links(study_notes, video_title)

            # Update knowledge graph with new note
            self.knowledge_graph.add_note(video_title, linked_notes)

            # Save to file
            sanitized_title = self.video_processor.sanitize_filename(video_title)
            filename = f"{sanitized_title}.md"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(linked_notes)

            print(f"✓ Study notes saved to {filename}")

            # Store original URL for reference
            original_url = url

            # Generate assessment if enabled
            if self.assessment_generator:
                print("Generating learning assessment...")
                try:
                    assessment_content = self.assessment_generator.generate_assessment(
                        transcript, study_notes, video_title, original_url
                    )

                    # Save assessment file
                    assessment_filename = self.assessment_generator.create_assessment_filename(video_title)
                    assessment_path = os.path.join(self.output_dir, assessment_filename)

                    with open(assessment_path, 'w', encoding='utf-8') as f:
                        f.write(assessment_content)

                    print(f"  Assessment saved to {assessment_filename}")

                except Exception as e:
                    print(f"  Warning: Assessment generation failed: {e}")

            # Refresh knowledge graph cache to include the new note
            self.knowledge_graph.refresh_cache()

            return True

        except Exception as e:
            print(f"\nERROR processing {url}: {e}")

            # Special handling for rate limiting
            if "rate limit" in str(e).lower() or "429" in str(e) or "too many requests" in str(e).lower():
                print("\n⚠ RATE LIMITING DETECTED!")
                print("YouTube is temporarily blocking requests. Solutions:")
                print("1. Wait 15-30 minutes before trying again")
                print("2. Process fewer videos at once")
                print("3. Ensure Tor proxy is running: docker-compose up -d tor-proxy")
            else:
                print("\nTroubleshooting:")
                print("1. Check if the video has captions/subtitles enabled")
                print("2. Some videos restrict transcript access")
                print("3. Ensure Tor proxy is running: docker-compose up -d tor-proxy")
            return False

    def process_urls(self, urls):
        """Process a list of URLs."""
        if not urls:
            print("No URLs provided")
            return

        # Check if API is ready
        if not self.notes_generator.is_ready():
            return

        print(f"\nProcessing {len(urls)} URL(s)...")
        if self.subject:
            print(f"Subject: {self.subject}")
            print(f"Cross-reference scope: {'Subject-only' if not self.global_context else 'Global'}")

        successful = 0

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing: {url}")

            # Add delay between requests to avoid rate limiting
            if i > 1:  # Skip delay for first video
                print("  Waiting 3 seconds to avoid rate limiting...")
                time.sleep(3)

            if self.process_single_url(url):
                successful += 1

        print(f"\n" + "="*50)
        print(f"COMPLETE: {successful}/{len(urls)} URL(s) processed successfully")
        print(f"Output saved to: {self.output_dir}/")

        # Show knowledge graph stats
        stats = self.knowledge_graph.get_stats()
        print(f"Knowledge Graph ({stats['scope']}): {stats['total_notes']} notes, {stats['total_concepts']} concepts")
        if stats.get('subject_count'):
            print(f"Subjects: {stats['subject_count']} ({', '.join(stats['subjects'])})")
        print("="*50)


def show_help():
    """Display help information."""
    print("""
YouTube Study Buddy - Transform YouTube videos into AI-powered study notes

Usage:
  youtube-study-buddy <url1> <url2> ...                    # Process URLs from command line
  youtube-study-buddy --file urls.txt                      # Process URLs from file
  youtube-study-buddy --subject "Topic" <url1> <url2> ...  # Process URLs with subject organization

Options:
  --subject <name>         Organize notes by subject (creates Study notes/<subject>/ folder)
  --subject-only           Cross-reference only within the specified subject (default: global)
  --file <filename>        Read URLs from file (one per line)
  --no-assessments         Disable assessment generation
  --no-auto-categorize     Disable auto-categorization
  --help, -h               Show this help message

Examples:
  youtube-study-buddy https://youtube.com/watch?v=xyz https://youtube.com/watch?v=abc
  youtube-study-buddy --subject "Machine Learning" https://youtube.com/watch?v=xyz
  youtube-study-buddy --file my-playlist-urls.txt
  youtube-study-buddy --subject "Python" --subject-only --file python-videos.txt

Playlist Extraction:
  # Extract URLs from a YouTube playlist using yt-dlp
  yt-dlp --flat-playlist --print url "PLAYLIST_URL" > urls.txt
  youtube-study-buddy --file urls.txt

Requirements:
  - Claude API key (set CLAUDE_API_KEY or ANTHROPIC_API_KEY environment variable)
    Get it from: https://console.anthropic.com/
  - Tor proxy running: docker-compose up -d tor-proxy

Output:
  - Notes saved in Study notes/<subject>/ folders
  - Cross-references to related notes automatically included
  - Obsidian [[links]] automatically added between related notes

For interactive GUI, use: streamlit run streamlit_app.py
    """)


def main():
    """Main CLI entry point."""
    print("""
========================================
   YouTube to Study Notes Tool
   Tor-based Transcript + Claude AI
========================================
    """)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert YouTube videos to organized study notes', add_help=False)
    parser.add_argument('urls', nargs='*', help='YouTube URLs to process')
    parser.add_argument('--subject', '-s', help='Subject for organizing notes')
    parser.add_argument('--subject-only', action='store_true', help='Cross-reference only within subject')
    parser.add_argument('--file', '-f', help='Read URLs from file (one per line)')
    parser.add_argument('--no-assessments', action='store_true', help='Disable assessment generation')
    parser.add_argument('--no-auto-categorize', action='store_true', help='Disable auto-categorization')
    parser.add_argument('--help', '-h', action='store_true', help='Show help message')

    args = parser.parse_args()

    if args.help:
        show_help()
        sys.exit(0)

    # Create app instance with configuration
    app = YouTubeStudyNotes(
        subject=args.subject,
        global_context=not args.subject_only,
        generate_assessments=not args.no_assessments,
        auto_categorize=not args.no_auto_categorize
    )

    # Collect URLs from either command line or file
    urls_to_process = []

    if args.file:
        # Read from file
        urls_to_process = app.read_urls_from_file(args.file)
        if not urls_to_process:
            print(f"No URLs found in {args.file}")
            sys.exit(1)
    elif args.urls:
        # Use URLs from command line
        urls_to_process = args.urls
    else:
        # No URLs provided
        show_help()
        sys.exit(1)

    # Process the URLs
    app.process_urls(urls_to_process)


if __name__ == "__main__":
    main()
