# Job Logging Guide

## Overview

The job logging system appends all video processing jobs to a JSON array file (`notes/processing_log.json`), including:
- Complete job data (transcript, notes, assessment)
- File paths and existence checks
- Processing timings and durations
- **Errors with full context**
- Worker assignments and stages

This enables:
- Post-processing analysis
- Error debugging
- Performance monitoring
- Resume/retry logic
- Historical tracking

## Quick Start

```python
from pathlib import Path
from yt_study_buddy.job_logger import create_default_logger
from yt_study_buddy.processing_pipeline import process_video_job

# Create logger (creates notes/processing_log.json)
logger = create_default_logger(Path('notes'))

# Add to components dict
components = {
    'video_processor': processor,
    'notes_generator': generator,
    'job_logger': logger,  # ← Add this
    # ... other components
}

# Process job - will automatically log result
job = process_video_job(job, components)
```

## JSON Structure

Each job in the array contains:

```json
{
  // Input
  "video_id": "abc123",
  "url": "https://youtu.be/abc123",
  "subject": "AI",
  "worker_id": 0,

  // Stage 1: Transcript
  "video_title": "Introduction to Machine Learning",
  "transcript": "full transcript text...",
  "transcript_metadata": {
    "duration": "15:30",
    "length": 12500,
    "method": "api"
  },

  // Stage 2: Generated Content
  "has_notes": true,
  "has_assessment": true,
  "notes_length": 5200,
  "assessment_length": 3400,

  // Stage 3: Files
  "output_dir": "notes/AI",
  "notes_filepath": "notes/AI/Introduction_to_Machine_Learning.md",
  "assessment_filepath": "notes/AI/Assessment_Introduction_to_Machine_Learning.md",
  "notes_file_exists": true,
  "assessment_file_exists": true,

  // Stage 4: PDFs
  "pdf_subdir": "notes/AI/pdfs",
  "notes_pdf_path": "notes/AI/pdfs/Introduction_to_Machine_Learning.pdf",
  "assessment_pdf_path": "notes/AI/pdfs/Assessment_Introduction_to_Machine_Learning.pdf",
  "notes_pdf_exists": true,
  "assessment_pdf_exists": true,

  // Metadata
  "stage": "completed",
  "success": true,
  "error": null,
  "start_time": 1697543210.123,
  "end_time": 1697543255.456,
  "processing_duration": 45.2,
  "timings": {
    "fetch_transcript": 5.2,
    "generate_notes": 25.0,
    "generate_assessment": 10.0,
    "write_files": 0.5,
    "export_pdfs": 4.5
  },

  // Summary
  "files_created": [
    "notes/AI/Introduction_to_Machine_Learning.md",
    "notes/AI/Assessment_Introduction_to_Machine_Learning.md",
    "notes/AI/pdfs/Introduction_to_Machine_Learning.pdf",
    "notes/AI/pdfs/Assessment_Introduction_to_Machine_Learning.pdf"
  ],
  "total_files": 4,
  "logged_at": "2025-10-17T09:33:10.187500"
}
```

## Error Logging

Failed jobs include full error context:

```json
{
  "video_id": "xyz789",
  "video_title": "Failed Video",
  "stage": "generating_notes",
  "success": false,
  "error": "API rate limit exceeded: 429 Too Many Requests",
  "processing_duration": 12.3,
  "timings": {
    "fetch_transcript": 8.3,
    "generate_notes": 4.0
  },
  "logged_at": "2025-10-17T09:35:22.500123"
}
```

## JobLogger API

### Basic Usage

```python
from yt_study_buddy.job_logger import JobLogger
from pathlib import Path

# Create logger
logger = JobLogger(Path('notes/processing_log.json'))

# Log single job
logger.log_job(job)

# Log batch (more efficient)
logger.log_jobs_batch([job1, job2, job3])
```

### Reading Logs

```python
# Get all jobs
all_jobs = logger.get_all_jobs()

# Get failed jobs only
failed = logger.get_failed_jobs()
for job in failed:
    print(f"Failed: {job['video_title']}")
    print(f"  Error: {job['error']}")
    print(f"  Stage: {job['stage']}")

# Get successful jobs
successful = logger.get_successful_jobs()

# Get jobs by stage
pending = logger.get_jobs_by_stage('transcript_fetched')
```

### Statistics

```python
stats = logger.get_statistics()

print(f"Total: {stats['total_jobs']}")
print(f"Success rate: {stats['success_rate']*100:.1f}%")
print(f"Average duration: {stats['average_duration']:.1f}s")
print(f"Files created: {stats['total_files_created']}")

# Error analysis
for error_type, count in stats['error_types'].items():
    print(f"{error_type}: {count}")

# Stage distribution
for stage, count in stats['stages'].items():
    print(f"{stage}: {count}")
```

### Export to CSV

```python
# Export to CSV for Excel/spreadsheet analysis
logger.export_csv(Path('notes/jobs_export.csv'))
```

### Clear Logs

```python
# Clear all logs (use with caution!)
logger.clear_log()
```

## Command-Line Analysis with jq

### View All Jobs

```bash
cat notes/processing_log.json | jq '.'
```

### Count Jobs by Status

```bash
cat notes/processing_log.json | jq '[.[] | .success] | group_by(.) | map({status: .[0], count: length})'
```

Output:
```json
[
  {"status": false, "count": 2},
  {"status": true, "count": 5}
]
```

### Show Failed Jobs Only

```bash
cat notes/processing_log.json | jq '[.[] | select(.success == false)]'
```

### Show Failed Jobs with Error Messages

```bash
cat notes/processing_log.json | jq '.[] | select(.success == false) | {video_id, title: .video_title, error, stage}'
```

Output:
```json
{
  "video_id": "xyz789",
  "title": "Failed Video",
  "error": "API rate limit exceeded",
  "stage": "generating_notes"
}
```

### Calculate Average Duration (Successful Jobs)

```bash
cat notes/processing_log.json | jq '[.[] | select(.success == true) | .processing_duration] | add / length'
```

Output: `45.2`

### Group Errors by Type

```bash
cat notes/processing_log.json | jq '[.[] | select(.success == false) | .error] | group_by(.) | map({error: .[0], count: length})'
```

Output:
```json
[
  {"error": "API rate limit exceeded", "count": 3},
  {"error": "Network timeout", "count": 1},
  {"error": "Transcript not available", "count": 2}
]
```

### Find Longest Processing Jobs

```bash
cat notes/processing_log.json | jq 'sort_by(.processing_duration) | reverse | .[0:5] | .[] | {title: .video_title, duration: .processing_duration}'
```

### Show Jobs by Worker

```bash
cat notes/processing_log.json | jq 'group_by(.worker_id) | map({worker: .[0].worker_id, count: length, success: [.[] | select(.success == true)] | length})'
```

### Extract URLs of Failed Videos for Retry

```bash
cat notes/processing_log.json | jq -r '.[] | select(.success == false) | .url'
```

Output:
```
https://youtu.be/xyz789
https://youtu.be/abc456
```

### Filter by Subject

```bash
cat notes/processing_log.json | jq '.[] | select(.subject == "AI")'
```

### Show Timing Breakdown

```bash
cat notes/processing_log.json | jq '.[] | select(.success == true) | {title: .video_title, timings}'
```

## Integration with Processing Pipeline

The `process_video_job()` function automatically logs jobs if a logger is provided:

```python
# In processing_pipeline.py
def process_video_job(job, components):
    try:
        # ... process all stages ...
        job.mark_completed(duration)

        # Automatically log successful job
        if components.get('job_logger'):
            components['job_logger'].log_job(job)

        return job

    except Exception as e:
        job.mark_failed(str(e))

        # Automatically log failed job with error
        if components.get('job_logger'):
            components['job_logger'].log_job(job)

        return job
```

## Thread Safety

JobLogger is thread-safe for parallel processing:

```python
from concurrent.futures import ThreadPoolExecutor

# Multiple workers can safely log to same file
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(process_video_job, job, components)
        for job in jobs
    ]

    # Each job will be safely appended to log
    results = [f.result() for f in futures]
```

## Use Cases

### 1. Error Analysis

Identify common failure patterns:

```python
failed = logger.get_failed_jobs()
errors = {}
for job in failed:
    error_type = job['error'].split(':')[0]
    errors[error_type] = errors.get(error_type, 0) + 1

print("Common errors:")
for error, count in sorted(errors.items(), key=lambda x: -x[1]):
    print(f"  {error}: {count}")
```

### 2. Performance Monitoring

Track processing times by stage:

```python
import statistics

successful = logger.get_successful_jobs()
fetch_times = [j['timings'].get('fetch_transcript', 0) for j in successful]
notes_times = [j['timings'].get('generate_notes', 0) for j in successful]

print(f"Fetch transcript: {statistics.mean(fetch_times):.1f}s avg")
print(f"Generate notes: {statistics.mean(notes_times):.1f}s avg")
```

### 3. Resume Failed Jobs

Extract failed video IDs for retry:

```python
failed = logger.get_failed_jobs()
failed_urls = [job['url'] for job in failed]

print(f"Retrying {len(failed_urls)} failed videos...")
# Re-process with original URLs
```

### 4. Export Report

```python
stats = logger.get_statistics()

report = f"""
Processing Report
=================

Total Jobs: {stats['total_jobs']}
Successful: {stats['successful']} ({stats['success_rate']*100:.1f}%)
Failed: {stats['failed']}
Average Duration: {stats['average_duration']:.1f}s
Files Created: {stats['total_files_created']}

Error Breakdown:
"""

for error_type, count in stats['error_types'].items():
    report += f"  - {error_type}: {count}\n"

print(report)
```

## Example Output

Run `example_job_logging.py` to see the system in action:

```bash
uv run python example_job_logging.py
```

This demonstrates:
- Basic logging
- Batch logging
- Statistics generation
- Error tracking
- JSON structure

## Best Practices

1. **Always provide job_logger**: Add it to components dict for automatic logging
2. **Use batch logging**: More efficient for multiple jobs
3. **Preserve logs**: Don't clear logs in production
4. **Analyze errors**: Use jq queries to identify patterns
5. **Export for analysis**: Use CSV export for spreadsheet analysis
6. **Monitor duration**: Track timing trends over time

## File Location

Default location: `notes/processing_log.json`

Customize:
```python
logger = JobLogger(Path('custom/location/jobs.json'))
```

## Performance

- **Thread-safe**: Lock protects concurrent writes
- **Append-only**: Jobs are appended to array
- **JSON formatting**: Pretty-printed for readability
- **Batch support**: Efficient multi-job logging

Average overhead per job: **< 10ms**
