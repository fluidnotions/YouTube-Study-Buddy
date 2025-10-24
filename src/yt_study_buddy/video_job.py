"""
Video processing job data class.

This dataclass holds all data for a video processing job as it flows through
the processing pipeline:
  1. Fetch transcript & title
  2. Generate notes & assessment
  3. Write files & export PDFs
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum


class ProcessingStage(Enum):
    """Processing stage for tracking progress."""
    CREATED = "created"
    FETCHING_TRANSCRIPT = "fetching_transcript"
    TRANSCRIPT_FETCHED = "transcript_fetched"
    GENERATING_NOTES = "generating_notes"
    NOTES_GENERATED = "notes_generated"
    GENERATING_ASSESSMENT = "generating_assessment"
    ASSESSMENT_GENERATED = "assessment_generated"
    WRITING_FILES = "writing_files"
    FILES_WRITTEN = "files_written"
    EXPORTING_PDFS = "exporting_pdfs"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class VideoProcessingJob:
    """
    Complete data for a video processing job.

    This object flows through the processing pipeline, accumulating data
    at each stage. Enables true pipelining and parallel processing.

    Pipeline flow:
        1. Create job with URL
        2. Fetch transcript & title → populate transcript_data, video_title
        3. Generate notes → populate study_notes
        4. Generate assessment → populate assessment_content
        5. Write files → populate file paths
        6. Export PDFs → populate pdf_paths
    """

    # ========================================================================
    # Input data (provided at creation)
    # ========================================================================
    url: str
    video_id: str
    subject: Optional[str] = None
    worker_id: Optional[int] = None

    # ========================================================================
    # Stage 1: Transcript & Title
    # ========================================================================
    video_title: Optional[str] = None
    transcript: Optional[str] = None
    transcript_data: Optional[Dict[str, Any]] = None  # duration, length, segments, method
    needs_ai_title: bool = False  # True if title fetch failed and we need AI to suggest one

    # ========================================================================
    # Stage 2: Content Generation
    # ========================================================================
    study_notes: Optional[str] = None
    assessment_content: Optional[str] = None

    # ========================================================================
    # Stage 3: File Paths (determined during write)
    # ========================================================================
    output_dir: Optional[Path] = None
    notes_filepath: Optional[Path] = None
    assessment_filepath: Optional[Path] = None

    # ========================================================================
    # Stage 4: PDF Export
    # ========================================================================
    notes_pdf_path: Optional[Path] = None
    assessment_pdf_path: Optional[Path] = None
    pdf_subdir: Optional[Path] = None  # pdfs/ subfolder

    # ========================================================================
    # Metadata
    # ========================================================================
    stage: ProcessingStage = ProcessingStage.CREATED
    success: bool = False
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    processing_duration: Optional[float] = None

    # Retry metadata
    retry_count: int = 0
    last_retry_time: Optional[float] = None
    next_retry_time: Optional[float] = None
    is_retryable: bool = True  # Can be set to False for permanent failures

    # Stage timings for analysis
    timings: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure Path objects are created."""
        if self.output_dir and not isinstance(self.output_dir, Path):
            self.output_dir = Path(self.output_dir)
        if self.notes_filepath and not isinstance(self.notes_filepath, Path):
            self.notes_filepath = Path(self.notes_filepath)
        if self.assessment_filepath and not isinstance(self.assessment_filepath, Path):
            self.assessment_filepath = Path(self.assessment_filepath)
        if self.notes_pdf_path and not isinstance(self.notes_pdf_path, Path):
            self.notes_pdf_path = Path(self.notes_pdf_path)
        if self.assessment_pdf_path and not isinstance(self.assessment_pdf_path, Path):
            self.assessment_pdf_path = Path(self.assessment_pdf_path)
        if self.pdf_subdir and not isinstance(self.pdf_subdir, Path):
            self.pdf_subdir = Path(self.pdf_subdir)

    # ========================================================================
    # Helper methods
    # ========================================================================

    def set_stage(self, stage: ProcessingStage):
        """Update processing stage."""
        self.stage = stage

    def mark_completed(self, duration: Optional[float] = None):
        """Mark job as successfully completed."""
        self.success = True
        self.stage = ProcessingStage.COMPLETED
        if duration:
            self.processing_duration = duration

    def mark_failed(self, error: str, stage: Optional[ProcessingStage] = None):
        """Mark job as failed with error."""
        self.success = False
        self.error = error
        self.stage = stage or ProcessingStage.FAILED

        # Classify if error is retryable
        self._classify_retryability(error)

    def add_timing(self, stage_name: str, duration: float):
        """Record timing for a stage."""
        self.timings[stage_name] = duration

    def get_youtube_url(self) -> str:
        """Get the full YouTube URL."""
        if self.url:
            return self.url
        return f"https://www.youtube.com/watch?v={self.video_id}"

    def get_markdown_content(self) -> Optional[str]:
        """Generate markdown content for notes file."""
        if not self.study_notes or not self.video_title:
            return None

        youtube_url = self.get_youtube_url()
        return f"# {self.video_title}\n\n[YouTube Video]({youtube_url})\n\n---\n\n{self.study_notes}"

    def has_transcript(self) -> bool:
        """Check if transcript was successfully fetched."""
        return self.transcript is not None and self.video_title is not None

    def has_notes(self) -> bool:
        """Check if notes were successfully generated."""
        return self.study_notes is not None

    def has_assessment(self) -> bool:
        """Check if assessment was successfully generated."""
        return self.assessment_content is not None

    def has_files_written(self) -> bool:
        """Check if files were written."""
        return self.notes_filepath is not None and self.notes_filepath.exists()

    def has_pdfs_exported(self) -> bool:
        """Check if PDFs were exported."""
        return self.notes_pdf_path is not None and self.notes_pdf_path.exists()

    def get_all_files(self) -> List[Path]:
        """Get list of all files created for this job."""
        files = []
        if self.notes_filepath:
            files.append(self.notes_filepath)
        if self.assessment_filepath:
            files.append(self.assessment_filepath)
        if self.notes_pdf_path:
            files.append(self.notes_pdf_path)
        if self.assessment_pdf_path:
            files.append(self.assessment_pdf_path)
        return [f for f in files if f.exists()]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of job for logging/reporting."""
        return {
            'video_id': self.video_id,
            'title': self.video_title,
            'url': self.url,
            'subject': self.subject,
            'worker_id': self.worker_id,
            'stage': self.stage.value,
            'success': self.success,
            'error': self.error,
            'duration': self.processing_duration,
            'files_created': len(self.get_all_files()),
            'timings': self.timings
        }

    # ========================================================================
    # Retry logic
    # ========================================================================

    def _classify_retryability(self, error: str):
        """
        Classify if error is retryable based on error message.

        Non-retryable errors:
        - No subtitles/transcripts available
        - Video is private/deleted/unavailable
        - Invalid video ID

        Retryable errors:
        - Network timeouts
        - IP blocking / rate limits
        - Connection failures
        """
        error_lower = error.lower()

        # Non-retryable errors
        non_retryable_patterns = [
            'no subtitle',
            'no transcript',
            'video unavailable',
            'video is private',
            'deleted',
            'invalid video id',
            'members-only'
        ]

        for pattern in non_retryable_patterns:
            if pattern in error_lower:
                self.is_retryable = False
                return

        # All other errors are retryable (blocking, timeout, connection, etc.)
        self.is_retryable = True

    def schedule_retry(self, retry_delay_minutes: int = 15):
        """
        Schedule next retry attempt.

        Args:
            retry_delay_minutes: Minutes to wait before retry (default: 15)
        """
        import time

        if not self.is_retryable:
            return

        self.retry_count += 1
        self.last_retry_time = time.time()
        self.next_retry_time = self.last_retry_time + (retry_delay_minutes * 60)

    def should_retry_now(self) -> bool:
        """
        Check if job should be retried now.

        Returns:
            True if job failed, is retryable, and enough time has passed
        """
        import time

        if self.success or not self.is_retryable:
            return False

        if self.next_retry_time is None:
            # Never scheduled for retry
            return False

        return time.time() >= self.next_retry_time

    def get_retry_status(self) -> Dict[str, Any]:
        """Get retry status information."""
        import time

        status = {
            'is_retryable': self.is_retryable,
            'retry_count': self.retry_count,
            'last_retry_time': self.last_retry_time,
            'next_retry_time': self.next_retry_time,
        }

        if self.next_retry_time:
            time_until_retry = self.next_retry_time - time.time()
            status['minutes_until_retry'] = max(0, time_until_retry / 60)
            status['ready_to_retry'] = self.should_retry_now()

        return status

    def to_json(self) -> Dict[str, Any]:
        """
        Export complete job data as JSON-serializable dict.

        Includes all state, metadata, errors, and file paths.
        """
        # Extract only JSON-serializable fields from transcript_data
        transcript_metadata = None
        if self.transcript_data:
            transcript_metadata = {
                'duration': self.transcript_data.get('duration'),
                'length': self.transcript_data.get('length'),
                'method': self.transcript_data.get('method'),
                # Skip 'segments' as they contain FetchedTranscriptSnippet objects
            }

        return {
            # Input
            'video_id': self.video_id,
            'url': self.url,
            'subject': self.subject,
            'worker_id': self.worker_id,

            # Stage 1: Transcript
            'video_title': self.video_title,
            'transcript': self.transcript,
            'transcript_metadata': transcript_metadata,

            # Stage 2: Generated content
            'has_notes': self.has_notes(),
            'has_assessment': self.has_assessment(),
            'notes_length': len(self.study_notes) if self.study_notes else 0,
            'assessment_length': len(self.assessment_content) if self.assessment_content else 0,

            # Stage 3: Files
            'output_dir': str(self.output_dir) if self.output_dir else None,
            'notes_filepath': str(self.notes_filepath) if self.notes_filepath else None,
            'assessment_filepath': str(self.assessment_filepath) if self.assessment_filepath else None,
            'notes_file_exists': self.notes_filepath.exists() if self.notes_filepath else False,
            'assessment_file_exists': self.assessment_filepath.exists() if self.assessment_filepath else False,

            # Stage 4: PDFs
            'pdf_subdir': str(self.pdf_subdir) if self.pdf_subdir else None,
            'notes_pdf_path': str(self.notes_pdf_path) if self.notes_pdf_path else None,
            'assessment_pdf_path': str(self.assessment_pdf_path) if self.assessment_pdf_path else None,
            'notes_pdf_exists': self.notes_pdf_path.exists() if self.notes_pdf_path else False,
            'assessment_pdf_exists': self.assessment_pdf_path.exists() if self.assessment_pdf_path else False,

            # Metadata
            'stage': self.stage.value,
            'success': self.success,
            'error': self.error,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'processing_duration': self.processing_duration,
            'timings': self.timings,

            # Retry metadata
            'retry_count': self.retry_count,
            'last_retry_time': self.last_retry_time,
            'next_retry_time': self.next_retry_time,
            'is_retryable': self.is_retryable,

            # Summary
            'files_created': [str(f) for f in self.get_all_files()],
            'total_files': len(self.get_all_files())
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        status = "✓" if self.success else "✗" if self.error else "⋯"
        title = self.video_title or self.video_id
        stage = self.stage.value
        return f"VideoJob({status} {title} [{stage}])"


# Factory functions for creating jobs

def create_job_from_url(url: str, video_id: str, subject: Optional[str] = None,
                       worker_id: Optional[int] = None) -> VideoProcessingJob:
    """
    Create a new video processing job from URL.

    Args:
        url: YouTube URL
        video_id: Extracted video ID
        subject: Subject category
        worker_id: Worker ID for parallel processing

    Returns:
        New VideoProcessingJob instance
    """
    return VideoProcessingJob(
        url=url,
        video_id=video_id,
        subject=subject,
        worker_id=worker_id,
        stage=ProcessingStage.CREATED
    )


def create_job_batch(urls: List[str], subject: Optional[str] = None) -> List[VideoProcessingJob]:
    """
    Create a batch of jobs from URLs.

    Args:
        urls: List of YouTube URLs
        subject: Subject category for all videos

    Returns:
        List of VideoProcessingJob instances
    """
    from .video_processor import VideoProcessor

    jobs = []
    processor = VideoProcessor("tor")

    for i, url in enumerate(urls):
        video_id = processor.get_video_id(url)
        if video_id:
            job = create_job_from_url(url, video_id, subject, worker_id=i)
            jobs.append(job)

    return jobs
