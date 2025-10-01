#!/usr/bin/env python3
"""
YouTube to Study Notes - Direct API Access + Claude Integration
Gets transcripts directly from YouTube and generates study notes with cross-referencing
"""
import sys
import os
import argparse
import time
from pathlib import Path

# Add src directory to path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from yt_study_buddy.video_processor import VideoProcessor
from yt_study_buddy.knowledge_graph import KnowledgeGraph
from yt_study_buddy.study_notes_generator import StudyNotesGenerator
from yt_study_buddy.obsidian_linker import ObsidianLinker
from yt_study_buddy.auto_categorizer import AutoCategorizer
from yt_study_buddy.assessment_generator import AssessmentGenerator


class YouTubeStudyNotes:
    """Main application class for processing YouTube videos into study notes."""

    def __init__(self, subject=None, global_context=True, base_dir="Study notes", provider_type="api",
                 generate_assessments=True, auto_categorize=True):
        self.subject = subject
        self.global_context = global_context
        self.base_dir = base_dir
        self.output_dir = os.path.join(base_dir, subject) if subject else base_dir
        self.provider_type = provider_type
        self.generate_assessments = generate_assessments
        self.auto_categorize = auto_categorize and not subject  # Only auto-categorize when no subject provided

        self.video_processor = VideoProcessor(provider_type)
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
            print("Fetching transcript from YouTube API...")
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

                # Reinitialize components with new subject
                self.knowledge_graph = KnowledgeGraph(self.base_dir, detected_subject, self.global_context)
                self.obsidian_linker = ObsidianLinker(self.base_dir, detected_subject, self.global_context)

            # Find related notes
            scope_msg = "globally" if self.global_context else f"within {self.subject} subject"
            print(f"Analyzing existing notes for connections ({scope_msg})...")
            related_notes = self.knowledge_graph.find_related_notes(transcript)

            if related_notes:
                print(f"Found {len(related_notes)} related notes for cross-referencing")
                for note in related_notes[:3]:  # Show top 3
                    subject_info = f" ({note['subject']})" if note.get('subject') else ""
                    print(f"  - {note['title']}{subject_info}")
            else:
                print("No related notes found (this might be your first note!)")

            # Ensure output directory exists
            os.makedirs(self.output_dir, exist_ok=True)

            # Generate study notes
            print("Calling Claude API for summarization...")
            if not self.notes_generator.is_ready():
                return False

            study_notes = self.notes_generator.generate_notes(transcript, related_notes)
            if not study_notes:
                print("ERROR: Claude API call failed")
                return False

            # Save to markdown file
            original_url = f"https://www.youtube.com/watch?v={video_id}"
            filename = self.notes_generator.create_markdown_file(
                video_title, original_url, study_notes, self.output_dir, video_id
            )

            print(f"SUCCESS: Saved to {filename}")

            # Add Obsidian links to connect with other notes
            print("Adding Obsidian links...")
            links_added = self.obsidian_linker.process_file(filename)
            if links_added:
                print("  Obsidian links added successfully")
            else:
                print("  No additional links found")

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
                print("3. Use longer delays between videos")
                print("4. Try from a different IP address/network")
            else:
                print("\nTroubleshooting:")
                print("1. Check if the video has captions/subtitles enabled")
                print("2. Some videos restrict transcript access")
                print("3. Try a different video to test if the tool works")
                print("4. Make sure you installed dependencies: pip install youtube-transcript-api anthropic python-dotenv requests")
            return False

    def process_urls_from_file(self, filename='urls.txt'):
        """Process multiple URLs from a file."""
        urls = self.read_urls_from_file(filename)
        if not urls:
            print(f"No URLs found in {filename}")
            return

        # Check if API is ready
        if not self.notes_generator.is_ready():
            return

        print(f"\nProcessing {len(urls)} URLs from {filename}...")
        if self.subject:
            print(f"Subject: {self.subject}")
            print(f"Cross-reference scope: {'Global' if self.global_context else 'Subject-only'}")

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
        print(f"BATCH COMPLETE: {successful}/{len(urls)} URLs processed successfully")
        print(f"Output saved to: {self.output_dir}/")

        # Show knowledge graph stats
        stats = self.knowledge_graph.get_stats()
        print(f"Knowledge Graph ({stats['scope']}): {stats['total_notes']} notes, {stats['total_concepts']} concepts")
        if stats.get('subject_count'):
            print(f"Subjects: {stats['subject_count']} ({', '.join(stats['subjects'])})")
        print("="*50)

    def show_help(self):
        """Display help information."""
        print("""
Usage:
  python main.py --subject <subject> <url>                    # Process single URL for subject
  python main.py --subject <subject> --batch                  # Process URLs from urls.txt for subject
  python main.py --subject <subject> --batch --file custom.txt # Process URLs from custom file
  python main.py --subject <subject> --subject-only <url>     # Cross-reference only within subject

Global Operations (no subject specified):
  python main.py <url>                     # Process single URL (no subject organization)
  python main.py --batch                   # Process URLs from urls.txt

Options:
  --subject <name>        Organize notes by subject (creates Study notes/<subject>/ folder)
  --subject-only          Cross-reference only within the specified subject (default: global)
  --batch                 Process multiple URLs from file
  --file <filename>       Use custom URL file (default: urls.txt)
  --method <api|scraper|tor>  Transcript extraction method (default: api)
                          - api: YouTube Transcript API (may hit rate limits)
                          - scraper: Web scraping (bypasses rate limits)
                          - tor: Via Tor proxy (best for bypassing IP blocks)
  --tor-host <host>       Tor SOCKS proxy host (default: 127.0.0.1)
  --tor-port <port>       Tor SOCKS proxy port (default: 9050)
  --no-tor-fallback       Disable fallback to direct connection if Tor fails
  --help                  Show this help message

Examples:
  python main.py --subject "Machine Learning" https://youtube.com/watch?v=xyz
  python main.py --subject "Python" --batch
  python main.py --subject "AI" --subject-only --batch
  python main.py --method scraper --batch                # Use web scraping to avoid rate limits
  python main.py --method tor --batch                    # Use Tor proxy to bypass IP blocks
  python main.py --method tor --tor-port 9050 --batch    # Tor with custom port

Requirements:
  Claude API key is required (set CLAUDE_API_KEY or ANTHROPIC_API_KEY)
  Get API key from: https://console.anthropic.com/

  For Tor proxy method:
  - Run Tor proxy: docker-compose up -d tor-proxy
  - Or install Tor locally: apt-get install tor (Linux) / brew install tor (Mac)

Output:
  Notes saved in Study notes/<subject>/ folders
  Cross-references to related notes automatically included
  Obsidian [[links]] automatically added between related notes
        """)

    def run_interactive(self):
        """Run in interactive mode."""
        print("Choose mode:")
        print("1. Process single URL")
        print("2. Process URLs from file (batch mode)")
        print("3. Show knowledge graph stats")
        print("4. Quit")
        choice = input("> ").strip()

        if choice == '2':
            filename = input("Enter filename (default: urls.txt): ").strip() or 'urls.txt'
            self.process_urls_from_file(filename)
        elif choice == '3':
            print("\n1. Subject-specific stats")
            print("2. Global stats")
            stats_choice = input("> ").strip()

            global_scope = stats_choice == '2'
            stats = self.knowledge_graph.get_stats(global_scope=global_scope)
            print(f"\nKnowledge Graph Statistics ({stats['scope']}):")
            print(f"  Total notes: {stats['total_notes']}")
            print(f"  Total concepts: {stats['total_concepts']}")
            print(f"  Average concepts per note: {stats['avg_concepts_per_note']}")
            if stats.get('subject_count'):
                print(f"  Subjects: {stats['subject_count']} ({', '.join(stats['subjects'])})")
        elif choice == '4':
            return
        else:
            print("Paste YouTube URL:")
            url = input("> ").strip()
            if url.lower() != 'quit':
                self.process_single_url(url)

    def main(self):
        """Main entry point."""
        print("""
========================================
   YouTube to Study Notes Tool
   Direct API Access + Claude Integration
========================================
        """)

        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Convert YouTube videos to organized study notes', add_help=False)
        parser.add_argument('url', nargs='?', help='YouTube URL to process')
        parser.add_argument('--subject', '-s', help='Subject for organizing notes')
        parser.add_argument('--subject-only', action='store_true', help='Cross-reference only within subject')
        parser.add_argument('--batch', '-b', action='store_true', help='Process URLs from file')
        parser.add_argument('--file', '-f', default='urls.txt', help='URL file (default: urls.txt)')
        parser.add_argument('--delay', '-d', type=int, default=3, help='Delay between requests in seconds (default: 3)')
        parser.add_argument('--aggressive', action='store_true', help='Aggressive mode - shorter delays, more retries')
        parser.add_argument('--conservative', action='store_true', help='Conservative mode - longer delays, fewer retries')
        parser.add_argument('--method', '-m', choices=['api', 'scraper', 'tor'], default='api',
                          help='Transcript extraction method: api (YouTube API), scraper (web scraping), or tor (via Tor proxy)')
        parser.add_argument('--tor-host', default='127.0.0.1', help='Tor SOCKS proxy host (default: 127.0.0.1)')
        parser.add_argument('--tor-port', type=int, default=9050, help='Tor SOCKS proxy port (default: 9050)')
        parser.add_argument('--no-tor-fallback', action='store_true', help='Disable fallback to direct connection if Tor fails')
        parser.add_argument('--no-assessments', action='store_true', help='Disable assessment generation')
        parser.add_argument('--no-auto-categorize', action='store_true', help='Disable auto-categorization')
        parser.add_argument('--help', '-h', action='store_true', help='Show help message')

        args = parser.parse_args()

        if args.help:
            self.show_help()
            sys.exit(0)

        # Update instance settings based on arguments

        # Update transcript provider if specified
        if args.method != self.provider_type:
            self.provider_type = args.method

            # Build provider kwargs for Tor
            provider_kwargs = {}
            if args.method == 'tor':
                provider_kwargs['tor_host'] = args.tor_host
                provider_kwargs['tor_port'] = args.tor_port
                provider_kwargs['use_tor_first'] = not args.no_tor_fallback

            self.video_processor = VideoProcessor(args.method, **provider_kwargs)
            print(f"Using {args.method} transcript method")

            if args.method == 'tor':
                print(f"  Tor proxy: {args.tor_host}:{args.tor_port}")
                print(f"  Fallback to direct: {'disabled' if args.no_tor_fallback else 'enabled'}")

        if args.subject:
            self.subject = args.subject
            self.output_dir = os.path.join(self.base_dir, args.subject)
            self.knowledge_graph = KnowledgeGraph(self.base_dir, args.subject, not args.subject_only)
            self.obsidian_linker = ObsidianLinker(self.base_dir, args.subject, not args.subject_only)
            self.global_context = not args.subject_only
            print(f"Subject: {args.subject}")
            print(f"Cross-reference scope: {'Subject-only' if args.subject_only else 'Global'}")

        if args.batch:
            self.process_urls_from_file(args.file)
        elif args.url:
            self.process_single_url(args.url)
        else:
            # Interactive mode
            if not args.subject:
                print("\nNote: No subject specified. Use --subject <name> to organize notes by subject.")
            self.run_interactive()


if __name__ == "__main__":
    # Parse arguments first to get configuration options
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--no-assessments', action='store_true')
    parser.add_argument('--no-auto-categorize', action='store_true')
    # Add all other arguments but only parse the options we need for initialization
    parser.add_argument('--subject', '-s')
    parser.add_argument('--subject-only', action='store_true')
    parser.add_argument('--method', '-m', default='api')
    parser.add_argument('--help', '-h', action='store_true')
    parser.add_argument('url', nargs='?')
    parser.add_argument('--batch', '-b', action='store_true')
    parser.add_argument('--file', '-f', default='urls.txt')
    parser.add_argument('--delay', '-d', type=int, default=3)
    parser.add_argument('--aggressive', action='store_true')
    parser.add_argument('--conservative', action='store_true')

    args, _ = parser.parse_known_args()  # Parse known args, ignore unknown

    # Create app instance with configuration
    app = YouTubeStudyNotes(
        subject=args.subject,
        global_context=not args.subject_only,
        provider_type=args.method,
        generate_assessments=not args.no_assessments,
        auto_categorize=not args.no_auto_categorize
    )
    app.main()