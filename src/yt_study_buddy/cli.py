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
import threading

from pathlib import Path
from loguru import logger

from .assessment_generator import AssessmentGenerator
from .auto_categorizer import AutoCategorizer
from .job_logger import create_default_logger
from .knowledge_graph import KnowledgeGraph
from .obsidian_linker import ObsidianLinker
from .parallel_processor import ParallelVideoProcessor, ProcessingResult, ProcessingMetrics
from .processing_pipeline import process_video_job
from .study_notes_generator import StudyNotesGenerator
from .video_job import create_job_from_url
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

        # Initialize Tor coordinator for parallel processing
        # Uses SingleTorCoordinator since we have only ONE Tor daemon
        if parallel:
            from .tor_transcript_fetcher import SingleTorCoordinator
            self.tor_coordinator = SingleTorCoordinator(
                tor_host='127.0.0.1',
                tor_port=9050,
                tor_control_port=9051,
                cooldown_hours=1.0
            )
        else:
            self.tor_coordinator = None

        # Initialize new components
        self.auto_categorizer = AutoCategorizer() if self.auto_categorize else None
        self.assessment_generator = AssessmentGenerator(self.notes_generator.client) if generate_assessments else None

        # Initialize PDF exporter if requested
        if self.export_pdf:
            if not PDF_AVAILABLE:
                logger.warning("Warning: PDF export requires additional dependencies:")
                logger.info("  uv pip install weasyprint markdown2")
                logger.info("Continuing without PDF export...")
                self.export_pdf = False
                self.pdf_exporter = None
            else:
                self.pdf_exporter = PDFExporter(theme=self.pdf_theme)
        else:
            self.pdf_exporter = None

        # Thread locks for parallel processing
        self._file_lock = threading.Lock()
        self._kg_lock = threading.Lock()

        # Job logger for tracking all processing results
        self.job_logger = create_default_logger(Path(self.base_dir))

        # Unified processor: Always create ParallelVideoProcessor
        # When parallel=False, max_workers=1 provides sequential behavior
        self.parallel_processor = ParallelVideoProcessor(
            max_workers=max_workers if parallel else 1,
            rate_limit_delay=1.0,
            sequential_delay=3.0
        )

        # Always create metrics for consistent tracking
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
            logger.error(f"Warning: Could not read {filename}: {e}")

        return urls

    def process_single_url(self, url, worker_processor=None, worker_id=None, tor_fetcher=None):
        """
        Process a single YouTube URL using stateless pipeline.

        Args:
            url: YouTube URL to process
            worker_processor: Optional VideoProcessor instance for this worker.
                            If None, uses self.video_processor (shared instance).
            worker_id: Optional worker ID for logging/debugging
            tor_fetcher: Optional TorTranscriptFetcher from pool (for parallel mode)

        Returns:
            ProcessingResult with outcome
        """
        # Use per-worker processor if provided, otherwise use shared instance
        processor = worker_processor if worker_processor else self.video_processor

        # If tor_fetcher provided from pool, inject it into the processor
        if tor_fetcher and hasattr(processor, 'provider'):
            if hasattr(processor.provider, 'tor_fetcher'):
                processor.provider.tor_fetcher = tor_fetcher

        # Extract video ID
        video_id = processor.get_video_id(url)
        if not video_id:
            logger.error(f"ERROR: Invalid YouTube URL: {url}")
            return ProcessingResult(
                url=url,
                video_id="invalid",
                success=False,
                error="Invalid YouTube URL"
            )

        # Handle auto-categorization - need to fetch transcript first
        current_subject = self.subject
        current_output_dir = self.output_dir

        # Pre-fetch transcript and title if auto-categorization is enabled
        # This avoids double-fetching (once for categorization, once in pipeline)
        pre_fetched_transcript = None
        pre_fetched_title = None

        if self.auto_categorizer and not self.subject:
            try:
                logger.info("Fetching transcript for auto-categorization...")
                pre_fetched_transcript = processor.get_transcript(video_id)
                pre_fetched_title = processor.get_video_title(video_id, worker_id=worker_id)

                logger.info("Auto-categorizing video content...")
                detected_subject = self.auto_categorizer.categorize_video(
                    pre_fetched_transcript['transcript'], pre_fetched_title, self.base_dir
                )
                logger.info(f"Detected subject: {detected_subject}")

                current_subject = detected_subject
                current_output_dir = os.path.join(self.base_dir, detected_subject)

                # Update components with new subject (thread-safe)
                with self._kg_lock:
                    self.knowledge_graph = KnowledgeGraph(self.base_dir, detected_subject, self.global_context)
                    self.obsidian_linker = ObsidianLinker(self.base_dir, detected_subject, self.global_context)

            except Exception as e:
                logger.error(f"Auto-categorization failed: {e}, using base directory")
                current_subject = None
                current_output_dir = self.base_dir
                # Clear pre-fetched data on categorization failure
                pre_fetched_transcript = None
                pre_fetched_title = None

        logger.info(f"\nFound video ID: {video_id}")
        if current_subject:
            logger.info(f"Subject: {current_subject}")
            logger.info(f"Cross-reference scope: {'Global' if self.global_context else 'Subject-only'}")

        # Create job object
        job = create_job_from_url(url, video_id, subject=current_subject, worker_id=worker_id)

        # If we pre-fetched for auto-categorization, populate job with that data
        # This skips the fetch stage in the pipeline (avoiding double-fetch)
        if pre_fetched_transcript and pre_fetched_title:
            from .video_job import ProcessingStage
            job.transcript = pre_fetched_transcript['transcript']
            job.transcript_data = pre_fetched_transcript
            job.video_title = pre_fetched_title
            job.set_stage(ProcessingStage.TRANSCRIPT_FETCHED)
            logger.debug("Using pre-fetched transcript from auto-categorization (skip fetch stage)")

        # Build components dict for pipeline
        components = {
            'video_processor': processor,
            'notes_generator': self.notes_generator,
            'assessment_generator': self.assessment_generator,
            'obsidian_linker': self.obsidian_linker,
            'pdf_exporter': self.pdf_exporter,
            'job_logger': self.job_logger,
            'output_dir': Path(current_output_dir),
            'filename_sanitizer': processor.sanitize_filename
        }

        # Process through stateless pipeline
        try:
            job = process_video_job(job, components)

            # Update knowledge graph cache (thread-safe)
            with self._kg_lock:
                self.knowledge_graph.refresh_cache()

            # Convert job to ProcessingResult
            return ProcessingResult(
                url=job.url,
                video_id=job.video_id,
                success=job.success,
                title=job.video_title,
                filepath=str(job.notes_filepath) if job.notes_filepath else None,
                duration_seconds=job.processing_duration,
                method=job.transcript_data.get('method', 'tor') if job.transcript_data else 'unknown'
            )

        except Exception as e:
            logger.error(f"\nERROR processing {url}: {e}")

            # Job was already logged by pipeline, just return failure
            return ProcessingResult(
                url=url,
                video_id=video_id,
                success=False,
                error=str(e),
                duration_seconds=job.processing_duration if hasattr(job, 'processing_duration') else 0
            )

    def _handle_rate_limit_error(self, e):
        """Handle rate limit errors with helpful message."""
        if "rate limit" in str(e).lower() or "429" in str(e) or "too many requests" in str(e).lower():
            logger.warning("\n⚠ RATE LIMITING DETECTED!")
            logger.info("YouTube is temporarily blocking requests. Solutions:")
            logger.info("1. Wait 15-30 minutes before trying again")
            logger.info("2. Process fewer videos at once")
            logger.info("3. Ensure Tor proxy is running: docker-compose up -d tor-proxy")
        else:
            logger.info("\nTroubleshooting:")
            logger.info("1. Check if the video has captions/subtitles enabled")
            logger.info("2. Some videos restrict transcript access")
            logger.info("3. Ensure Tor proxy is running: docker-compose up -d tor-proxy")

    def process_urls(self, urls):
        """Process a list of URLs (sequential or parallel)."""
        if not urls:
            logger.info("No URLs provided")
            return

        # Check if API is ready
        if not self.notes_generator.is_ready():
            return

        logger.debug(f"\nProcessing {len(urls)} URL(s)...")
        if self.subject:
            logger.info(f"Subject: {self.subject}")
            logger.info(f"Cross-reference scope: {'Subject-only' if not self.global_context else 'Global'}")

        # UNIFIED PROCESSING PATH: Single code path for both sequential and parallel modes
        if self.parallel and self.tor_coordinator:
            # Parallel mode with Tor coordinator - synchronized access to single Tor daemon
            def process_with_coordinator_worker(url, worker_id):
                """Process URL using Tor fetcher from coordinator."""
                with self.tor_coordinator.acquire(worker_id=worker_id) as tor_fetcher:
                    return self.process_single_url(url, worker_id=worker_id, tor_fetcher=tor_fetcher)

            results = self.parallel_processor.process_videos_parallel(
                urls,
                process_with_coordinator_worker,
                worker_factory=None  # Don't create per-worker processors
            )
        else:
            # Sequential mode or parallel without pool - use worker factory
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
            self.metrics.add_result(result)

        # Show statistics
        self.metrics.print_summary()

        successful = sum(1 for r in results if r.success)
        logger.info(f"\n{'='*50}")
        logger.success(f"COMPLETE: {successful}/{len(urls)} URL(s) processed successfully")
        logger.info(f"Output saved to: {self.output_dir}/")

        # Show knowledge graph stats
        stats = self.knowledge_graph.get_stats()
        logger.info(f"Knowledge Graph ({stats['scope']}): {stats['total_notes']} notes, {stats['total_concepts']} concepts")
        if stats.get('subject_count'):
            logger.info(f"Subjects: {stats['subject_count']} ({', '.join(stats['subjects'])})")
        logger.info("="*50)

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
        logger.success(f"✓ Debug logging enabled")
        logger.info(f"  Session log: {logger.session_log}")
        logger.info(f"  API log: {logger.api_log}")
        

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
            logger.info(f"No URLs found in {args.file}")
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
        logger.info("\n" + "="*60)
        from .debug_logger import get_logger
        debug_logger = get_logger()
        debug_logger.analyze_logs()


if __name__ == "__main__":
    main()
