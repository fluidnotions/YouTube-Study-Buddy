"""
Application interface layer for Streamlit and other UIs.

Provides a stable API that decouples UI code from implementation details.
If internal method names or signatures change, only this interface needs updating.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

from .cli import YouTubeStudyNotes
from .video_job import create_job_from_url
from .processing_pipeline import process_video_job


@dataclass
class ProcessingResult:
    """Result of processing a single video."""
    success: bool
    video_id: str
    video_title: Optional[str] = None
    url: Optional[str] = None
    notes_filepath: Optional[Path] = None
    assessment_filepath: Optional[Path] = None
    notes_pdf_path: Optional[Path] = None
    assessment_pdf_path: Optional[Path] = None
    transcript_length: int = 0
    related_notes_count: int = 0
    processing_duration: float = 0.0
    error: Optional[str] = None
    timings: Dict[str, float] = None


class StudyBuddyInterface:
    """
    Stable interface for YouTube Study Buddy operations.

    This interface shields UI code from internal implementation changes.
    """

    def __init__(
        self,
        subject: Optional[str] = None,
        global_context: bool = True,
        base_dir: str = "notes",
        generate_assessments: bool = True,
        auto_categorize: bool = True,
        parallel: bool = False,
        max_workers: int = 3,
        export_pdf: bool = False,
        pdf_theme: str = 'obsidian'
    ):
        """
        Initialize the Study Buddy interface.

        Args:
            subject: Subject category for organizing notes
            global_context: Enable global cross-referencing
            base_dir: Base directory for output
            generate_assessments: Generate learning assessments
            auto_categorize: Auto-detect subject categories
            parallel: Enable parallel processing
            max_workers: Number of parallel workers
            export_pdf: Export notes to PDF
            pdf_theme: PDF theme (obsidian, academic, minimal, default)
        """
        self._cli = YouTubeStudyNotes(
            subject=subject,
            global_context=global_context,
            base_dir=base_dir,
            generate_assessments=generate_assessments,
            auto_categorize=auto_categorize,
            parallel=parallel,
            max_workers=max_workers,
            export_pdf=export_pdf,
            pdf_theme=pdf_theme
        )
        self.base_dir = Path(base_dir)

    def validate_video_url(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Validate YouTube URL and extract video ID.

        Args:
            url: YouTube URL to validate

        Returns:
            Tuple of (video_id, error_message)
            If valid: (video_id, None)
            If invalid: (None, error_message)
        """
        try:
            video_id = self._cli.video_processor.get_video_id(url)
            if video_id:
                return video_id, None
            return None, "Invalid YouTube URL"
        except Exception as e:
            return None, str(e)

    def process_video(self, url: str, worker_id: int = 0) -> ProcessingResult:
        """
        Process a single YouTube video.

        Args:
            url: YouTube URL to process
            worker_id: Worker ID for tracking (default: 0)

        Returns:
            ProcessingResult with outcome and details
        """
        try:
            # Validate URL
            video_id, error = self.validate_video_url(url)
            if error:
                return ProcessingResult(
                    success=False,
                    video_id="invalid",
                    url=url,
                    error=error
                )

            # Use the stateless pipeline via CLI
            result = self._cli.process_single_url(url, worker_id=worker_id)

            # Convert to our interface result
            return ProcessingResult(
                success=result.success,
                video_id=result.video_id,
                video_title=result.title,
                url=result.url,
                notes_filepath=Path(result.filepath) if result.filepath else None,
                transcript_length=0,  # Not available in current result
                related_notes_count=0,  # Not available in current result
                processing_duration=result.duration_seconds,
                error=result.error if hasattr(result, 'error') else None
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                video_id=video_id if 'video_id' in locals() else "unknown",
                url=url,
                error=str(e)
            )

    def process_videos_batch(self, urls: List[str]) -> None:
        """
        Process multiple videos (parallel or sequential based on settings).

        Results are logged to processing_log.json automatically.
        Use get_job_log() to retrieve results after processing.

        Args:
            urls: List of YouTube URLs to process
        """
        self._cli.process_urls(urls)

    def get_knowledge_graph_stats(self) -> Dict[str, Any]:
        """
        Get knowledge graph statistics.

        Returns:
            Dictionary with stats:
            - total_notes: Number of notes
            - total_concepts: Number of concepts
            - subject_count: Number of subjects
            - subjects: List of subject names
            - scope: 'global' or 'subject'
        """
        try:
            return self._cli.knowledge_graph.get_stats()
        except Exception as e:
            return {
                'total_notes': 0,
                'total_concepts': 0,
                'subject_count': 0,
                'subjects': [],
                'scope': 'unknown',
                'error': str(e)
            }

    def get_job_log(self) -> List[Dict[str, Any]]:
        """
        Get all logged jobs from processing_log.json.

        Returns:
            List of job dictionaries with complete metadata
        """
        try:
            return self._cli.job_logger.get_all_jobs()
        except Exception:
            return []

    def get_failed_jobs(self) -> List[Dict[str, Any]]:
        """Get all failed jobs from log."""
        try:
            return self._cli.job_logger.get_failed_jobs()
        except Exception:
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.

        Returns:
            Dictionary with:
            - total_jobs: Total number of jobs
            - successful: Number of successful jobs
            - failed: Number of failed jobs
            - success_rate: Success rate (0.0-1.0)
            - average_duration: Average processing time
            - error_types: Dictionary of error counts
        """
        try:
            return self._cli.job_logger.get_statistics()
        except Exception:
            return {
                'total_jobs': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0,
                'average_duration': None,
                'error_types': {}
            }

    def check_api_ready(self) -> bool:
        """Check if Claude API is ready."""
        try:
            return self._cli.notes_generator.is_ready()
        except Exception:
            return False

    @property
    def output_dir(self) -> Path:
        """Get current output directory."""
        return Path(self._cli.output_dir)

    @property
    def subject(self) -> Optional[str]:
        """Get current subject."""
        return self._cli.subject


def create_interface(
    subject: Optional[str] = None,
    global_context: bool = True,
    generate_assessments: bool = True,
    auto_categorize: bool = True,
    base_dir: str = "notes",
    parallel: bool = False,
    max_workers: int = 3,
    export_pdf: bool = False,
    pdf_theme: str = 'obsidian'
) -> StudyBuddyInterface:
    """
    Factory function to create StudyBuddyInterface.

    This is the recommended way to create an interface instance.

    Args:
        subject: Subject category
        global_context: Enable global cross-referencing
        generate_assessments: Generate learning assessments
        auto_categorize: Auto-detect subject
        base_dir: Base output directory
        parallel: Enable parallel processing
        max_workers: Number of workers
        export_pdf: Export to PDF
        pdf_theme: PDF theme name

    Returns:
        StudyBuddyInterface instance
    """
    return StudyBuddyInterface(
        subject=subject,
        global_context=global_context,
        base_dir=base_dir,
        generate_assessments=generate_assessments,
        auto_categorize=auto_categorize,
        parallel=parallel,
        max_workers=max_workers,
        export_pdf=export_pdf,
        pdf_theme=pdf_theme
    )
