# Stateless Pipeline Architecture

## Core Principles

### 1. Pre-allocated Exit Node Pool
- **Queue-based**: Exit nodes pre-allocated in a queue
- **Pop & Use**: Worker pops node, uses it, returns it
- **1-hour rotation**: Used nodes cleared after 1 hour
- **Zero contention**: Always available if pool sized correctly

```
Available Queue: [Exit1, Exit2, Exit3, Exit4, Exit5]
                     ↓ pop
Worker uses Exit1
                     ↓ after use or 1 hour
Available Queue: [Exit2, Exit3, Exit4, Exit5, Exit1]
```

### 2. Stateless Processing Functions
Each function:
- **Input**: VideoProcessingJob object
- **Output**: Same job object (modified)
- **No side effects**: Only transforms the job
- **Idempotent**: Can be re-run safely

```python
def fetch_transcript(job: VideoProcessingJob, processor) -> VideoProcessingJob:
    """Fetch transcript. Stateless - just populates job fields."""
    if job.has_transcript():
        return job  # Already done, skip

    # Fetch and populate job
    job.transcript = ...
    job.video_title = ...
    job.set_stage(ProcessingStage.TRANSCRIPT_FETCHED)
    return job
```

### 3. Job Object Carries All State
- **All data**: transcript, notes, assessment, paths
- **All metadata**: stage, timings, errors
- **Resumable**: Can check stage and continue from there

```python
@dataclass
class VideoProcessingJob:
    # Input
    url: str
    video_id: str

    # Stage 1: Fetched
    transcript: Optional[str] = None
    video_title: Optional[str] = None

    # Stage 2: Generated
    study_notes: Optional[str] = None
    assessment_content: Optional[str] = None

    # Stage 3: Written
    notes_filepath: Optional[Path] = None
    assessment_filepath: Optional[Path] = None

    # Stage 4: Exported
    notes_pdf_path: Optional[Path] = None
    assessment_pdf_path: Optional[Path] = None

    # Metadata
    stage: ProcessingStage = ProcessingStage.CREATED
    exit_node_id: Optional[int] = None
    exit_node_acquired_at: Optional[float] = None
```

## Pipeline Flow

```
┌─────────────┐
│ Create Jobs │
│  from URLs  │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────────┐
│  Stage 1: Fetch (Parallel)          │
│  ┌─────────────────────────────┐    │
│  │ Worker pops exit node       │    │
│  │ Fetch transcript & title    │    │
│  │ Populate job.transcript     │    │
│  │ Return exit node to pool    │    │
│  └─────────────────────────────┘    │
└──────┬──────────────────────────────┘
       │ job.stage = TRANSCRIPT_FETCHED
       ↓
┌─────────────────────────────────────┐
│  Stage 2: Generate (Parallel)       │
│  ┌─────────────────────────────┐    │
│  │ Generate study notes        │    │
│  │ Generate assessment         │    │
│  │ Populate job.study_notes    │    │
│  │ Populate job.assessment     │    │
│  └─────────────────────────────┘    │
└──────┬──────────────────────────────┘
       │ job.stage = ASSESSMENT_GENERATED
       ↓
┌─────────────────────────────────────┐
│  Stage 3: Write (Sequential/Batch)  │
│  ┌─────────────────────────────┐    │
│  │ Write markdown files        │    │
│  │ Write assessment files      │    │
│  │ Process Obsidian links      │    │
│  │ Populate job.notes_filepath │    │
│  └─────────────────────────────┘    │
└──────┬──────────────────────────────┘
       │ job.stage = FILES_WRITTEN
       ↓
┌─────────────────────────────────────┐
│  Stage 4: Export PDFs (Parallel)    │
│  ┌─────────────────────────────┐    │
│  │ Export notes to PDF         │    │
│  │ Export assessment to PDF    │    │
│  │ Save to pdfs/ subfolder     │    │
│  │ Populate job.notes_pdf_path │    │
│  └─────────────────────────────┘    │
└──────┬──────────────────────────────┘
       │ job.stage = COMPLETED
       ↓
  ┌─────────┐
  │ Success │
  └─────────┘
```

## Implementation

### Exit Node Pool (Queue-based)

```python
class TorExitNodePool:
    def __init__(self, pool_size: int):
        # Pre-allocate all connections
        self._available = deque(range(pool_size))
        self._in_use = {}  # node_id -> acquired_timestamp
        self._lock = threading.Lock()
        self._rotation_interval = 3600  # 1 hour

    def acquire(self) -> int:
        """Pop an exit node from queue."""
        with self._lock:
            if not self._available:
                raise RuntimeError("No exit nodes available")

            node_id = self._available.popleft()
            self._in_use[node_id] = time.time()
            return node_id

    def release(self, node_id: int):
        """Return exit node to queue (or rotate if >1 hour)."""
        with self._lock:
            acquired_at = self._in_use.pop(node_id)
            age = time.time() - acquired_at

            if age > self._rotation_interval:
                # Rotate circuit before returning
                self._rotate_circuit(node_id)

            self._available.append(node_id)
```

### Stateless Processing Functions

```python
def fetch_transcript_and_title(
    job: VideoProcessingJob,
    processor: VideoProcessor,
    exit_node_id: int
) -> VideoProcessingJob:
    """
    Stage 1: Fetch transcript and title.

    Stateless: Only reads from API, writes to job object.
    Resumable: Checks if already done.
    """
    # Check if already done
    if job.has_transcript():
        print(f"Transcript already fetched for {job.video_id}, skipping")
        return job

    job.set_stage(ProcessingStage.FETCHING_TRANSCRIPT)

    # Fetch transcript
    transcript_data = processor.get_transcript(job.video_id)
    job.transcript = transcript_data['transcript']
    job.transcript_data = transcript_data

    # Fetch title
    job.video_title = processor.get_video_title(job.video_id)

    job.set_stage(ProcessingStage.TRANSCRIPT_FETCHED)
    return job


def generate_notes_and_assessment(
    job: VideoProcessingJob,
    notes_generator,
    assessment_generator
) -> VideoProcessingJob:
    """
    Stage 2: Generate notes and assessment.

    Stateless: Only calls AI APIs, writes to job object.
    Resumable: Checks what's already done.
    """
    # Generate notes if not done
    if not job.has_notes():
        job.set_stage(ProcessingStage.GENERATING_NOTES)
        job.study_notes = notes_generator.generate_notes(
            transcript=job.transcript
        )
        job.set_stage(ProcessingStage.NOTES_GENERATED)

    # Generate assessment if not done
    if not job.has_assessment() and assessment_generator:
        job.set_stage(ProcessingStage.GENERATING_ASSESSMENT)
        job.assessment_content = assessment_generator.generate_assessment(
            job.transcript,
            job.study_notes,
            job.video_title,
            job.get_youtube_url()
        )
        job.set_stage(ProcessingStage.ASSESSMENT_GENERATED)

    return job


def write_files(
    job: VideoProcessingJob,
    output_dir: Path,
    sanitizer
) -> VideoProcessingJob:
    """
    Stage 3: Write markdown files.

    Stateless: Only writes files, updates job paths.
    Resumable: Checks if files exist.
    """
    if job.has_files_written():
        print(f"Files already written for {job.video_id}, skipping")
        return job

    job.set_stage(ProcessingStage.WRITING_FILES)
    job.output_dir = output_dir

    # Write notes file
    sanitized_title = sanitizer(job.video_title)
    job.notes_filepath = output_dir / f"{sanitized_title}.md"

    markdown_content = job.get_markdown_content()
    job.notes_filepath.write_text(markdown_content, encoding='utf-8')

    # Write assessment file if exists
    if job.assessment_content:
        assessment_filename = f"Assessment_{sanitized_title}.md"
        job.assessment_filepath = output_dir / assessment_filename
        job.assessment_filepath.write_text(
            job.assessment_content,
            encoding='utf-8'
        )

    job.set_stage(ProcessingStage.FILES_WRITTEN)
    return job


def export_pdfs(
    job: VideoProcessingJob,
    pdf_exporter
) -> VideoProcessingJob:
    """
    Stage 4: Export PDFs to pdfs/ subfolder.

    Stateless: Only creates PDFs, updates job paths.
    Resumable: Checks if PDFs exist.
    """
    if job.has_pdfs_exported():
        print(f"PDFs already exported for {job.video_id}, skipping")
        return job

    job.set_stage(ProcessingStage.EXPORTING_PDFS)

    # Create pdfs/ subdirectory
    job.pdf_subdir = job.output_dir / "pdfs"
    job.pdf_subdir.mkdir(exist_ok=True)

    # Export notes PDF
    if job.notes_filepath:
        pdf_filename = job.notes_filepath.stem + ".pdf"
        job.notes_pdf_path = job.pdf_subdir / pdf_filename
        pdf_exporter.markdown_to_pdf(
            job.notes_filepath,
            job.notes_pdf_path
        )

    # Export assessment PDF
    if job.assessment_filepath:
        pdf_filename = job.assessment_filepath.stem + ".pdf"
        job.assessment_pdf_path = job.pdf_subdir / pdf_filename
        pdf_exporter.markdown_to_pdf(
            job.assessment_filepath,
            job.assessment_pdf_path
        )

    job.set_stage(ProcessingStage.COMPLETED)
    job.mark_completed()
    return job
```

### Pipeline Orchestration

```python
def process_video_pipeline(
    job: VideoProcessingJob,
    exit_node_pool: TorExitNodePool,
    components: Dict[str, Any]
) -> VideoProcessingJob:
    """
    Process a video through all stages.

    Each stage is stateless and resumable.
    Exit node acquired once for stage 1, then released.
    """
    try:
        # Stage 1: Fetch (needs exit node)
        exit_node_id = exit_node_pool.acquire()
        job.exit_node_id = exit_node_id
        job.exit_node_acquired_at = time.time()

        try:
            job = fetch_transcript_and_title(
                job,
                components['processor'],
                exit_node_id
            )
        finally:
            exit_node_pool.release(exit_node_id)

        # Stage 2: Generate (no exit node needed)
        job = generate_notes_and_assessment(
            job,
            components['notes_generator'],
            components['assessment_generator']
        )

        # Stage 3: Write (no exit node needed)
        job = write_files(
            job,
            components['output_dir'],
            components['sanitizer']
        )

        # Stage 4: Export PDFs (no exit node needed)
        if components.get('pdf_exporter'):
            job = export_pdfs(job, components['pdf_exporter'])

        return job

    except Exception as e:
        job.mark_failed(str(e))
        return job
```

## Benefits

### 1. Resumability
```python
# Can resume from any stage
if job.stage == ProcessingStage.TRANSCRIPT_FETCHED:
    # Skip fetch, start from generate
    job = generate_notes_and_assessment(job, ...)
```

### 2. Testability
```python
# Each function can be tested independently
def test_fetch_transcript():
    job = VideoProcessingJob(url="...", video_id="abc")
    job = fetch_transcript_and_title(job, mock_processor, 0)
    assert job.has_transcript()
    assert job.stage == ProcessingStage.TRANSCRIPT_FETCHED
```

### 3. Parallelism
```python
# Stage 1: Parallel with exit nodes
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(fetch_transcript_and_title, job, processor, node_id)
        for job, node_id in zip(jobs, exit_node_ids)
    ]
    fetched_jobs = [f.result() for f in futures]

# Stage 2: Parallel without exit nodes
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(generate_notes_and_assessment, job, gen, assess)
        for job in fetched_jobs
    ]
    generated_jobs = [f.result() for f in futures]
```

### 4. Monitoring
```python
# Job object has all timing data
print(job.timings)
# {'fetch': 10.5, 'generate_notes': 20.3, 'generate_assessment': 30.2, ...}

print(job.get_summary())
# {'video_id': 'abc', 'stage': 'completed', 'duration': 65.2, ...}
```

## File Organization

```
notes/
└── Subject/
    ├── Video_Title_1.md
    ├── Video_Title_2.md
    ├── Assessment_Video_Title_1.md
    ├── Assessment_Video_Title_2.md
    └── pdfs/
        ├── Video_Title_1.pdf
        ├── Video_Title_2.pdf
        ├── Assessment_Video_Title_1.pdf
        └── Assessment_Video_Title_2.pdf
```

## Migration Path

1. ✅ Create VideoProcessingJob dataclass
2. ✅ Create stateless processing functions
3. ⏳ Refactor exit node pool to queue-based
4. ⏳ Update CLI to use pipeline
5. ⏳ Add resume capability
6. ⏳ Add progress tracking

This architecture is clean, testable, and enables future enhancements like:
- Pause/resume processing
- Distributed processing
- Fine-grained progress tracking
- Replay failed jobs
- Batch optimizations
