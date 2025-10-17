# YouTube Study Buddy Documentation

Complete guide to the stateless pipeline architecture with parallel processing and automatic job logging.

## Quick Start

```bash
# Sequential processing
uv run yt-study-buddy https://youtu.be/VIDEO_ID

# Parallel processing (3 workers)
uv run yt-study-buddy --parallel --workers 3 \
  https://youtu.be/VIDEO1 \
  https://youtu.be/VIDEO2 \
  https://youtu.be/VIDEO3

# View processing results
cat notes/processing_log.json | jq '.'
```

## Core Concepts

### Stateless Pipeline Architecture

**Key Achievement:** Assessment generation now happens **in parallel** across workers (54% faster)

**How it works:**
- Each worker processes jobs independently through stages: Fetch → Notes → Assessment → Write → Export
- File lock only held for fast writes (~700ms vs 36s before)
- All jobs automatically logged with complete metadata

### Job Logging

Every job (success/failure) logged to `notes/processing_log.json`:

```json
{
  "video_id": "abc123",
  "worker_id": 2,
  "success": true,
  "processing_duration": 58.8,
  "timings": {
    "fetch_transcript": 5.2,
    "generate_notes": 20.3,
    "generate_assessment": 28.1,
    "write_files": 0.7
  },
  "error": null
}
```

**Query examples:**
```bash
# Failed jobs only
cat notes/processing_log.json | jq '.[] | select(.success == false)'

# Average duration
cat notes/processing_log.json | jq '[.[] | select(.success) | .processing_duration] | add / length'

# Performance by worker
cat notes/processing_log.json | jq 'group_by(.worker_id) | map({worker: .[0].worker_id, count: length})'
```

## Documentation Index

### Essential Guides

1. **[docs/architecture.md](docs/architecture.md)** - Complete stateless pipeline architecture
   - Components overview (VideoProcessingJob, pipeline functions, JobLogger)
   - Performance comparison (before/after)
   - Migration status

2. **[docs/debugging.md](docs/debugging.md)** - Debugging with PyCharm & CLI
   - PyCharm run configurations
   - Debug CLI wrapper
   - Breakpoint debugging

3. **[docs/job-logging.md](docs/job-logging.md)** - Job logging and analysis
   - JobLogger API
   - JSON structure
   - Query examples with jq
   - Statistics and CSV export

### Feature Guides

4. **[docs/pdf-export.md](docs/pdf-export.md)** - PDF export with themes
   - WeasyPrint setup
   - 4 themes (obsidian, academic, minimal, default)
   - Batch export

5. **[docs/docker.md](docs/docker.md)** - Docker setup for Tor proxy
   - docker-compose configuration
   - Tor SOCKS proxy setup

### Advanced Topics

6. **[docs/parallel-architecture.md](docs/parallel-architecture.md)** - Parallel processing deep dive
   - 3 optimization approaches analyzed
   - Lock contention reduction
   - Performance metrics

7. **[docs/tor-connections.md](docs/tor-connections.md)** - Per-worker Tor connections
   - Exit node pool architecture
   - Circuit rotation
   - Future: Queue-based pool

## File Organization

```
notes/
├── processing_log.json           # All job results
├── AI/
│   ├── video_title_1.md
│   ├── assessment_video_title_1.md
│   └── pdfs/
│       ├── video_title_1.pdf
│       └── assessment_video_title_1.pdf
└── Programming/
    └── ...
```

## Key Features

✅ **Parallel Assessment Generation** - 54% performance improvement
✅ **Automatic Job Logging** - Complete audit trail with errors
✅ **Stateless Pipeline** - Idempotent, resumable operations
✅ **Worker ID Tracking** - Per-worker debugging and analysis
✅ **PDF Export** - Obsidian-style themes
✅ **Auto-categorization** - AI-powered subject detection

## Performance

**Before (Sequential):**
- Worker 1: 65.7s
- Worker 2: 101.4s (waiting for lock)
- Worker 3: 137.1s (waiting for lock)
- **Total: 137s**

**After (Parallel):**
- Worker 1: 65.7s
- Worker 2: 65.7s
- Worker 3: 65.7s
- **Total: 66s (54% faster!)**

## Next Steps

- [ ] Tor exit node queue with 1-hour rotation
- [ ] Resume failed jobs from log
- [ ] Real-time progress tracking
- [ ] Distributed processing

## Examples

See `example_job_logging.py` for complete usage examples.
