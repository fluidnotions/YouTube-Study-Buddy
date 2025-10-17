"""
Command-line interface for YouTube Study Buddy.

Usage:
    youtube-study-buddy <url1> <url2> ...
    youtube-study-buddy --file urls.txt
    youtube-study-buddy --subject "Topic" <url1> <url2>
"""

import argparse
import os
import sys
import time
import threading

from .assessment_generator import AssessmentGenerator
from .auto_categorizer import AutoCategorizer
from .knowledge_graph import KnowledgeGraph
from .obsidian_linker import ObsidianLinker
from .parallel_processor import ParallelVideoProcessor, ProcessingResult, ProcessingMetrics
from .study_notes_generator import StudyNotesGenerator
from .video_processor import VideoProcessor

try:
    from .pdf_exporter import PDFExporter
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class YouTubeStudyNotes:
    """Main application class for processing YouTube videos into study notes."""

    def __init__(self, subject=None, global_context=True, base_dir="notes",
                 generate_assessments=True, auto_categorize=True,
                 parallel=False, max_workers=3, export_pdf=False, pdf_theme='obsidian'):
        self.subject = subject
        self.global_context = global_context
        self.base_dir = base_dir
        self.output_dir = os.path.join(base_dir, subject) if subject else base_dir
        self.generate_assessments = generate_assessments
        self.auto_categorize = auto_categorize and not subject  # Only auto-categorize when no subject provided
        self.parallel = parallel
        self.max_workers = max_workers
        self.export_pdf = export_pdf
        self.pdf_theme = pdf_theme

        self.video_processor = VideoProcessor("tor")
        self.knowledge_graph = KnowledgeGraph(base_dir, subject, global_context)
        self.notes_generator = StudyNotesGenerator()
        self.obsidian_linker = ObsidianLinker(base_dir, subject, global_context)

        # Initialize new components
        self.auto_categorizer = AutoCategorizer() if self.auto_categorize else None
        self.assessment_generator = AssessmentGenerator(self.notes_generator.client) if generate_assessments else None

        # Initialize PDF exporter if requested
        if self.export_pdf:
            if not PDF_AVAILABLE:
                print("Warning: PDF export requires additional dependencies:")
                print("  uv pip install weasyprint markdown2")
                print("Continuing without PDF export...")
                self.export_pdf = False
                self.pdf_exporter = None
            else:
                self.pdf_exporter = PDFExporter(theme=self.pdf_theme)
        else:
            self.pdf_exporter = None

        # Thread locks for parallel processing
        self._file_lock = threading.Lock()
        self._kg_lock = threading.Lock()

        # Add parallel processor
        if self.parallel:
            self.parallel_processor = ParallelVideoProcessor(
                max_workers=max_workers,
                rate_limit_delay=1.0
            )
            self.metrics = ProcessingMetrics()

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

    def process_single_url(self, url, worker_processor=None):
        """
        Process a single YouTube URL and generate study notes.

        Args:
            url: YouTube URL to process
            worker_processor: Optional VideoProcessor instance for this worker.
                            If None, uses self.video_processor (shared instance).
        """
        start_time = time.time()

        # Use per-worker processor if provided, otherwise use shared instance
        processor = worker_processor if worker_processor else self.video_processor

        # Extract video ID
        video_id = processor.get_video_id(url)
        if not video_id:
            print(f"ERROR: Invalid YouTube URL: {url}")
            return ProcessingResult(
                url=url,
                video_id="invalid",
                success=False,
                error="Invalid YouTube URL"
            )

        print(f"\nFound video ID: {video_id}")
        if self.subject:
            print(f"Subject: {self.subject}")
            print(f"Cross-reference scope: {'Global' if self.global_context else 'Subject-only'}")

        try:
            # Get transcript
            print("Fetching transcript from YouTube via Tor...")
            transcript_data = processor.get_transcript(video_id)
            transcript = transcript_data['transcript']
            method = transcript_data.get('method', 'tor')

            if transcript_data['duration']:
                print(f"Video duration: {transcript_data['duration']}")
            print(f"Transcript length: {transcript_data['length']} characters")

            # Get video title
            print("Fetching video title...")
            video_title = processor.get_video_title(video_id)

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
                transcript=transcript
            )

            # Save to file using the notes generator's method
            sanitized_title = processor.sanitize_filename(video_title)
            filename = f"{sanitized_title}.md"
            filepath = os.path.join(self.output_dir, filename)

            # Create markdown file with header
            original_url = f"https://www.youtube.com/watch?v={video_id}"
            markdown_content = f"# {video_title}\n\n[YouTube Video]({original_url})\n\n---\n\n{study_notes}"

            # ===================================================================
            # PHASE 1: Generate all content (PARALLEL - outside lock)
            # ===================================================================

            # Generate assessment if enabled (expensive Claude API call - do in parallel!)
            assessment_content = None
            assessment_filename = None
            assessment_path = None

            if self.assessment_generator:
                print("Generating learning assessment...")
                try:
                    assessment_content = self.assessment_generator.generate_assessment(
                        transcript, study_notes, video_title, original_url
                    )
                    assessment_filename = self.assessment_generator.create_assessment_filename(video_title)
                    assessment_path = os.path.join(self.output_dir, assessment_filename)
                    print(f"  ✓ Assessment generated")

                except Exception as e:
                    print(f"  ✗ Assessment generation failed: {e}")
                    assessment_content = None

            # ===================================================================
            # PHASE 2: Write files (FAST - needs lock for thread safety)
            # ===================================================================

            with self._file_lock:
                # Write study notes file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                print(f"✓ Study notes saved to {filename}")

                # Write assessment file if generated
                if assessment_content and assessment_path:
                    with open(assessment_path, 'w', encoding='utf-8') as f:
                        f.write(assessment_content)
                    print(f"  ✓ Assessment saved to {assessment_filename}")

                # Add cross-references using Obsidian linker (relatively fast)
                print("Adding cross-references to related notes...")
                self.obsidian_linker.process_file(filepath)

            # ===================================================================
            # PHASE 3: Export PDFs (PARALLEL - outside lock, per-worker)
            # ===================================================================

            if self.pdf_exporter:
                print("Exporting to PDF...")
                try:
                    # Export study notes PDF
                    pdf_path = self.pdf_exporter.markdown_to_pdf(filepath)
                    print(f"  ✓ PDF exported: {pdf_path.name}")

                    # Export assessment PDF if it was generated
                    if assessment_path and os.path.exists(assessment_path):
                        assessment_pdf = self.pdf_exporter.markdown_to_pdf(assessment_path)
                        print(f"  ✓ Assessment PDF: {assessment_pdf.name}")

                except Exception as e:
                    print(f"  ✗ PDF export failed: {e}")

            # Update knowledge graph cache (thread-safe)
            with self._kg_lock:
                # Refresh knowledge graph cache to include the new note
                self.knowledge_graph.refresh_cache()

            duration = time.time() - start_time
            return ProcessingResult(
                url=url,
                video_id=video_id,
                success=True,
                title=video_title,
                filepath=filepath,
                duration_seconds=duration,
                method=method
            )

        except Exception as e:
            duration = time.time() - start_time
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

            return ProcessingResult(
                url=url,
                video_id=video_id,
                success=False,
                error=str(e),
                duration_seconds=duration
            )

    def process_urls(self, urls):
        """Process a list of URLs (sequential or parallel)."""
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

        if self.parallel:
            # Parallel processing with per-worker VideoProcessor instances
            # Factory function creates independent VideoProcessor for each worker
            def video_processor_factory():
                """Create a new VideoProcessor instance for a worker thread."""
                return VideoProcessor("tor")

            results = self.parallel_processor.process_videos_parallel(
                urls,
                self.process_single_url,
                worker_factory=video_processor_factory
            )

            # Collect metrics
            for result in results:
                if hasattr(self, 'metrics'):
                    self.metrics.add_result(result)

            # Show statistics
            if hasattr(self, 'metrics'):
                self.metrics.print_summary()

            successful = sum(1 for r in results if r.success)
            print(f"\n{'='*50}")
            print(f"COMPLETE: {successful}/{len(urls)} URL(s) processed successfully")
            print(f"Output saved to: {self.output_dir}/")

        else:
            # Sequential processing (existing logic)
            successful = 0
            for i, url in enumerate(urls, 1):
                print(f"\n[{i}/{len(urls)}] Processing: {url}")

                # Add delay between requests to avoid rate limiting
                if i > 1:  # Skip delay for first video
                    print("  Waiting 3 seconds to avoid rate limiting...")
                    time.sleep(3)

                result = self.process_single_url(url)
                if result.success:
                    successful += 1

            print(f"\n{'='*50}")
            print(f"COMPLETE: {successful}/{len(urls)} URL(s) processed successfully")
            print(f"Output saved to: {self.output_dir}/")

        # Show knowledge graph stats
        stats = self.knowledge_graph.get_stats()
        print(f"Knowledge Graph ({stats['scope']}): {stats['total_notes']} notes, {stats['total_concepts']} concepts")
        if stats.get('subject_count'):
            print(f"Subjects: {stats['subject_count']} ({', '.join(stats['subjects'])})")
        print("="*50)

        # Show statistics at the end
        if hasattr(self.video_processor.provider, 'print_stats'):
            self.video_processor.provider.print_stats()


def show_help():
    """Display help information."""
    print("""
YouTube Study Buddy - Transform YouTube videos into AI-powered study notes

Usage:
  youtube-study-buddy <url1> <url2> ...                    # Process URLs sequentially
  youtube-study-buddy --parallel --file urls.txt           # Process URLs in parallel
  youtube-study-buddy --workers 5 -p --file urls.txt      # Parallel with 5 workers

Options:
  --subject <name>         Organize notes by subject (creates notes/<subject>/ folder)
  --subject-only           Cross-reference only within the specified subject (default: global)
  --file <filename>        Read URLs from file (one per line)
  --parallel, -p           Enable parallel processing (faster for batches)
  --workers, -w <num>      Number of parallel workers (default: 3, max: 10)
  --no-assessments         Disable assessment generation
  --no-auto-categorize     Disable auto-categorization
  --export-pdf             Export notes to PDF with Obsidian-style formatting
  --pdf-theme <theme>      PDF theme: default, obsidian, academic, minimal (default: obsidian)
  --help, -h               Show this help message

Examples:
  # Sequential processing
  youtube-study-buddy https://youtube.com/watch?v=xyz

  # Parallel processing (3 workers)
  youtube-study-buddy --parallel --file playlist.txt

  # Parallel with 5 workers
  youtube-study-buddy -p -w 5 --file large-playlist.txt

  # With subject organization
  youtube-study-buddy --subject "Machine Learning" https://youtube.com/watch?v=xyz

  # Export to PDF with Obsidian theme
  youtube-study-buddy --export-pdf https://youtube.com/watch?v=xyz

  # Export with academic theme
  youtube-study-buddy --export-pdf --pdf-theme academic --file urls.txt

Performance:
  Sequential: ~60s per video
  Parallel (3 workers): ~25s per video (2.5x faster)
  Parallel (5 workers): ~20s per video (3x faster, higher rate limit risk)

Playlist Extraction:
  # Extract URLs from a YouTube playlist using yt-dlp
  yt-dlp --flat-playlist --print url "PLAYLIST_URL" > urls.txt
  youtube-study-buddy --parallel --file urls.txt

Requirements:
  - Claude API key (set CLAUDE_API_KEY or ANTHROPIC_API_KEY environment variable)
    Get it from: https://console.anthropic.com/
  - Tor proxy running: docker-compose up -d tor-proxy

Output:
  - Notes saved in notes/<subject>/ folders
  - Cross-references to related notes automatically included
  - Obsidian [[links]] automatically added between related notes

For interactive GUI: streamlit run streamlit_app.py
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
    parser.add_argument('--parallel', '-p', action='store_true', help='Enable parallel processing of videos')
    parser.add_argument('--workers', '-w', type=int, default=3, help='Number of parallel workers (default: 3)')
    parser.add_argument('--no-assessments', action='store_true', help='Disable assessment generation')
    parser.add_argument('--no-auto-categorize', action='store_true', help='Disable auto-categorization')
    parser.add_argument('--export-pdf', action='store_true', help='Export notes to PDF (requires: uv pip install weasyprint markdown2)')
    parser.add_argument('--pdf-theme', default='obsidian', choices=['default', 'obsidian', 'academic', 'minimal'],
                       help='PDF theme style (default: obsidian)')
    parser.add_argument('--debug-logging', action='store_true', help='Enable detailed debug logging to debug_logs/ directory')
    parser.add_argument('--help', '-h', action='store_true', help='Show help message')

    args = parser.parse_args()

    if args.help:
        show_help()
        sys.exit(0)

    # Enable debug logging if requested
    if args.debug_logging:
        from .debug_logger import enable_debug_logging
        logger = enable_debug_logging()
        print(f"✓ Debug logging enabled")
        print(f"  Session log: {logger.session_log}")
        print(f"  API log: {logger.api_log}")
        print()

    # Create app instance with configuration
    app = YouTubeStudyNotes(
        subject=args.subject,
        global_context=not args.subject_only,
        generate_assessments=not args.no_assessments,
        auto_categorize=not args.no_auto_categorize,
        parallel=args.parallel,
        max_workers=args.workers,
        export_pdf=args.export_pdf,
        pdf_theme=args.pdf_theme
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

    # Show debug log analysis if enabled
    if args.debug_logging:
        print("\n" + "="*60)
        from .debug_logger import get_logger
        logger = get_logger()
        logger.analyze_logs()


if __name__ == "__main__":
    main()
