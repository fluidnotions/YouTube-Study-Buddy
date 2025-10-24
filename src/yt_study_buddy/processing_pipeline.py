"""
Stateless processing pipeline for video jobs.

Each function takes a VideoProcessingJob and returns it (modified).
Functions are idempotent and resumable - they check if work is already done.
"""
import time
from pathlib import Path
from typing import Optional

from loguru import logger

from .video_job import VideoProcessingJob, ProcessingStage


# ============================================================================
# Stage 1: Fetch Transcript & Title
# ============================================================================

def fetch_transcript_and_title(
    job: VideoProcessingJob,
    video_processor,
    worker_id: Optional[int] = None
) -> VideoProcessingJob:
    """
    Fetch transcript and title from YouTube.

    Stateless: Only fetches data and populates job object.
    Resumable: Skips if transcript already fetched.

    Args:
        job: VideoProcessingJob to process
        video_processor: VideoProcessor instance (with Tor)
        worker_id: Optional worker ID for logging

    Returns:
        Same job object with transcript and title populated
    """
    # Check if already done
    if job.has_transcript():
        logger.warning(f"  [Job {job.video_id}] Transcript already fetched, skipping")
        return job

    stage_start = time.time()
    job.set_stage(ProcessingStage.FETCHING_TRANSCRIPT)

    try:
        # Fetch transcript
        logger.info(f"  [Job {job.video_id}] Fetching transcript...")
        transcript_data = video_processor.get_transcript(job.video_id)

        if not transcript_data:
            raise ValueError("Could not get transcript: Both Tor and yt-dlp fallback failed")

        job.transcript = transcript_data['transcript']
        job.transcript_data = transcript_data

        if transcript_data.get('duration'):
            logger.info(f"    Duration: {transcript_data['duration']}")
        logger.info(f"    Length: {transcript_data['length']} characters")

        # Fetch title (non-critical - use video ID as fallback)
        logger.info(f"  [Job {job.video_id}] Fetching title...")
        title_fetched = False
        try:
            job.video_title = video_processor.get_video_title(
                job.video_id,
                worker_id=worker_id
            )
            if job.video_title and not job.video_title.startswith("Video_"):
                logger.info(f"    Title: {job.video_title}")
                title_fetched = True
            else:
                logger.warning(f"    ⚠️  Got fallback title, will use video ID")
                job.video_title = f"Video_{job.video_id}"
        except Exception as title_error:
            # Title fetch failed - use video ID as fallback
            logger.warning(f"    ⚠️  Title fetch failed: {title_error}")
            logger.info(f"    Using video ID as fallback title")
            job.video_title = f"Video_{job.video_id}"

        # Mark that we need AI title generation later
        job.needs_ai_title = not title_fetched

        job.set_stage(ProcessingStage.TRANSCRIPT_FETCHED)
        job.add_timing('fetch_transcript', time.time() - stage_start)

        return job

    except Exception as e:
        job.mark_failed(f"Transcript fetch failed: {e}", ProcessingStage.FETCHING_TRANSCRIPT)
        raise


# ============================================================================
# Stage 2: Generate Notes & Assessment
# ============================================================================

def generate_study_notes(
    job: VideoProcessingJob,
    notes_generator
) -> VideoProcessingJob:
    """
    Generate study notes using Claude AI.

    Stateless: Only calls AI API and populates job.study_notes.
    Resumable: Skips if notes already generated.

    Args:
        job: VideoProcessingJob to process
        notes_generator: StudyNotesGenerator instance

    Returns:
        Same job object with study_notes populated
    """
    # Check if already done
    if job.has_notes():
        logger.warning(f"  [Job {job.video_id}] Notes already generated, skipping")
        return job

    if not job.has_transcript():
        raise ValueError("Cannot generate notes without transcript")

    stage_start = time.time()
    job.set_stage(ProcessingStage.GENERATING_NOTES)

    try:
        logger.info(f"  [Job {job.video_id}] Generating study notes...")

        # Request title suggestion in the same call if needed (no extra LLM call)
        job.study_notes = notes_generator.generate_notes(
            transcript=job.transcript,
            suggest_title=job.needs_ai_title
        )

        # Extract title from notes if it was requested
        if job.needs_ai_title:
            from .study_notes_generator import StudyNotesGenerator
            extracted_title, cleaned_notes = StudyNotesGenerator.extract_title_from_notes(job.study_notes)

            if extracted_title:
                old_title = job.video_title
                job.video_title = extracted_title
                job.study_notes = cleaned_notes  # Use notes without the title line
                job.needs_ai_title = False  # Mark as resolved
                logger.success(f"    ✓ AI-generated title: {extracted_title}")
                logger.debug(f"    (Replaced fallback: {old_title})")
            else:
                logger.warning(f"    ⚠️  Could not extract title from notes, keeping: {job.video_title}")

        job.set_stage(ProcessingStage.NOTES_GENERATED)
        job.add_timing('generate_notes', time.time() - stage_start)

        logger.success(f"    ✓ Notes generated ({len(job.study_notes)} chars)")
        return job

    except Exception as e:
        job.mark_failed(f"Notes generation failed: {e}", ProcessingStage.GENERATING_NOTES)
        raise


def generate_assessment(
    job: VideoProcessingJob,
    assessment_generator
) -> VideoProcessingJob:
    """
    Generate learning assessment using Claude AI.

    Stateless: Only calls AI API and populates job.assessment_content.
    Resumable: Skips if assessment already generated.

    Args:
        job: VideoProcessingJob to process
        assessment_generator: AssessmentGenerator instance

    Returns:
        Same job object with assessment_content populated
    """
    # Check if already done
    if job.has_assessment():
        logger.warning(f"  [Job {job.video_id}] Assessment already generated, skipping")
        return job

    if not job.has_notes():
        raise ValueError("Cannot generate assessment without notes")

    if not assessment_generator:
        logger.warning(f"  [Job {job.video_id}] Assessment generation disabled, skipping")
        return job

    stage_start = time.time()
    job.set_stage(ProcessingStage.GENERATING_ASSESSMENT)

    try:
        logger.info(f"  [Job {job.video_id}] Generating assessment...")
        job.assessment_content = assessment_generator.generate_assessment(
            job.transcript,
            job.study_notes,
            job.video_title,
            job.get_youtube_url()
        )

        job.set_stage(ProcessingStage.ASSESSMENT_GENERATED)
        job.add_timing('generate_assessment', time.time() - stage_start)

        logger.success(f"    ✓ Assessment generated ({len(job.assessment_content)} chars)")
        return job

    except Exception as e:
        # Assessment failure is not critical, just log and continue
        logger.error(f"    ✗ Assessment generation failed: {e}")
        job.assessment_content = None
        return job


# ============================================================================
# Stage 3: Write Files
# ============================================================================

def write_markdown_files(
    job: VideoProcessingJob,
    output_dir: Path,
    filename_sanitizer
) -> VideoProcessingJob:
    """
    Write markdown files to disk.

    Stateless: Only writes files and populates job file paths.
    Resumable: Skips if files already exist.

    Args:
        job: VideoProcessingJob to process
        output_dir: Base output directory
        filename_sanitizer: Function to sanitize filenames

    Returns:
        Same job object with file paths populated
    """
    # Check if already done
    if job.has_files_written():
        logger.warning(f"  [Job {job.video_id}] Files already written, skipping")
        return job

    if not job.has_notes():
        raise ValueError("Cannot write files without notes")

    stage_start = time.time()
    job.set_stage(ProcessingStage.WRITING_FILES)

    try:
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        job.output_dir = output_dir

        # Write study notes file
        sanitized_title = filename_sanitizer(job.video_title)
        job.notes_filepath = output_dir / f"{sanitized_title}.md"

        markdown_content = job.get_markdown_content()
        job.notes_filepath.write_text(markdown_content, encoding='utf-8')

        logger.success(f"  [Job {job.video_id}] ✓ Notes saved: {job.notes_filepath.name}")

        # Write assessment file if exists
        if job.assessment_content:
            assessment_filename = f"Assessment_{sanitized_title}.md"
            job.assessment_filepath = output_dir / assessment_filename
            job.assessment_filepath.write_text(
                job.assessment_content,
                encoding='utf-8'
            )
            logger.success(f"  [Job {job.video_id}] ✓ Assessment saved: {job.assessment_filepath.name}")

        job.set_stage(ProcessingStage.FILES_WRITTEN)
        job.add_timing('write_files', time.time() - stage_start)

        return job

    except Exception as e:
        job.mark_failed(f"File writing failed: {e}", ProcessingStage.WRITING_FILES)
        raise


def process_obsidian_links(
    job: VideoProcessingJob,
    obsidian_linker
) -> VideoProcessingJob:
    """
    Add Obsidian cross-reference links to markdown files.

    Stateless: Only modifies files on disk.
    Resumable: Can be re-run safely (idempotent).

    Args:
        job: VideoProcessingJob to process
        obsidian_linker: ObsidianLinker instance

    Returns:
        Same job object (unchanged)
    """
    if not job.has_files_written():
        logger.warning(f"  [Job {job.video_id}] Files not written yet, skipping link processing")
        return job

    try:
        logger.info(f"  [Job {job.video_id}] Adding cross-references...")
        obsidian_linker.process_file(job.notes_filepath)
        logger.success(f"    ✓ Links processed")
        return job

    except Exception as e:
        # Link processing failure is not critical
        logger.error(f"    ✗ Link processing failed: {e}")
        return job


# ============================================================================
# Stage 4: Export PDFs
# ============================================================================

def export_pdfs(
    job: VideoProcessingJob,
    pdf_exporter
) -> VideoProcessingJob:
    """
    Export markdown files to PDF in pdfs/ subfolder.

    Stateless: Only creates PDF files and populates job PDF paths.
    Resumable: Skips if PDFs already exist.

    Args:
        job: VideoProcessingJob to process
        pdf_exporter: PDFExporter instance

    Returns:
        Same job object with PDF paths populated
    """
    if not pdf_exporter:
        logger.warning(f"  [Job {job.video_id}] PDF export disabled, skipping")
        return job

    # Check if already done
    if job.has_pdfs_exported():
        logger.warning(f"  [Job {job.video_id}] PDFs already exported, skipping")
        return job

    if not job.has_files_written():
        raise ValueError("Cannot export PDFs without markdown files")

    stage_start = time.time()
    job.set_stage(ProcessingStage.EXPORTING_PDFS)

    try:
        # Create pdfs/ subdirectory
        job.pdf_subdir = job.output_dir / "pdfs"
        job.pdf_subdir.mkdir(exist_ok=True)

        # Export notes PDF
        if job.notes_filepath and job.notes_filepath.exists():
            pdf_filename = job.notes_filepath.stem + ".pdf"
            job.notes_pdf_path = job.pdf_subdir / pdf_filename

            pdf_exporter.markdown_to_pdf(
                job.notes_filepath,
                job.notes_pdf_path
            )
            logger.success(f"  [Job {job.video_id}] ✓ Notes PDF: {job.notes_pdf_path.name}")

        # Assessment PDFs disabled - only export notes
        # if job.assessment_filepath and job.assessment_filepath.exists():
        #     pdf_filename = job.assessment_filepath.stem + ".pdf"
        #     job.assessment_pdf_path = job.pdf_subdir / pdf_filename
        #
        #     pdf_exporter.markdown_to_pdf(
        #         job.assessment_filepath,
        #         job.assessment_pdf_path
        #     )
        #     logger.success(f"  [Job {job.video_id}] ✓ Assessment PDF: {job.assessment_pdf_path.name}")

        job.set_stage(ProcessingStage.COMPLETED)
        job.add_timing('export_pdfs', time.time() - stage_start)

        return job

    except Exception as e:
        # PDF export failure is not critical
        logger.error(f"  [Job {job.video_id}] ✗ PDF export failed: {e}")
        return job


# ============================================================================
# Complete Pipeline
# ============================================================================

def process_video_job(
    job: VideoProcessingJob,
    components: dict
) -> VideoProcessingJob:
    """
    Process a video job through all stages.

    Each stage is stateless and resumable. The job object carries all state.

    Args:
        job: VideoProcessingJob to process
        components: Dictionary with all required components:
            - 'video_processor': VideoProcessor instance
            - 'notes_generator': StudyNotesGenerator instance
            - 'assessment_generator': AssessmentGenerator instance (optional)
            - 'obsidian_linker': ObsidianLinker instance
            - 'pdf_exporter': PDFExporter instance (optional)
            - 'job_logger': JobLogger instance (optional)
            - 'output_dir': Path to output directory
            - 'filename_sanitizer': Function to sanitize filenames

    Returns:
        Processed job object (also logged if job_logger provided)
    """
    start_time = time.time()
    job.start_time = start_time

    try:
        logger.info(f"\n{'='*60}")
        logger.debug(f"Processing Job: {job.video_id}")
        logger.info(f"{'='*60}")

        # Stage 1: Fetch
        job = fetch_transcript_and_title(
            job,
            components['video_processor'],
            worker_id=job.worker_id
        )

        # Stage 2: Generate
        job = generate_study_notes(job, components['notes_generator'])
        job = generate_assessment(job, components.get('assessment_generator'))

        # Stage 3: Write
        job = write_markdown_files(
            job,
            components['output_dir'],
            components['filename_sanitizer']
        )
        job = process_obsidian_links(job, components['obsidian_linker'])

        # Stage 4: Export
        job = export_pdfs(job, components.get('pdf_exporter'))

        # Mark as completed
        job.end_time = time.time()
        job.processing_duration = job.end_time - start_time
        job.mark_completed(job.processing_duration)

        logger.success(f"  ✓ Job completed in {job.processing_duration:.1f}s")
        logger.info(f"{'='*60}\n")

        # Log job if logger provided
        if components.get('job_logger'):
            components['job_logger'].log_job(job)

        return job

    except Exception as e:
        job.end_time = time.time()
        job.processing_duration = job.end_time - start_time
        job.mark_failed(str(e))

        logger.error(f"  ✗ Job failed: {e}")
        logger.info(f"{'='*60}\n")

        # Log failed job if logger provided
        if components.get('job_logger'):
            components['job_logger'].log_job(job)

        return job
