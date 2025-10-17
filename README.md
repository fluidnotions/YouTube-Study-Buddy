# YouTube Study Buddy

Transform YouTube videos into organized study notes with AI-powered analysis, automatic retry, and Tor-based transcript fetching.

## Quick Start

### Using Docker (Recommended)

```bash
# 1. Set your Claude API key in .env
echo "CLAUDE_API_KEY=your_key_here" > .env

# 2. Start services
docker-compose up -d

# 3. Open browser
open http://localhost:8501
```

### Using CLI

```bash
# Sequential processing
uv run yt-study-buddy https://youtu.be/VIDEO_ID

# Parallel processing (3 workers)
uv run yt-study-buddy --parallel --workers 3 \
  https://youtu.be/VIDEO1 \
  https://youtu.be/VIDEO2 \
  https://youtu.be/VIDEO3

# View processing logs
cat notes/processing_log.json | jq '.'
```

## Features

### Core Capabilities
- 🤖 **AI-Powered Notes** - Claude Sonnet 4.5 generates comprehensive study materials
- 📝 **Learning Assessments** - Automatic quiz generation with gap analysis
- 🔄 **Automatic Retry** - 15-minute retry system for failed jobs (see [RETRY_GUIDE.md](RETRY_GUIDE.md))
- 🌐 **Tor Integration** - Bypass rate limits with rotating exit nodes
- 🏷️ **Auto-Categorization** - ML-based subject detection
- 📊 **Knowledge Graph** - Cross-reference related concepts
- 📄 **PDF Export** - Multiple themes (Obsidian, Academic, Minimal)

### Reliability Features
- **24-Hour Exit IP Cooldown** - Prevents reusing recently blocked IPs
- **Human-Readable Timestamps** - "2 hours ago", "3 days ago", etc.
- **Failure Tracking** - See which IPs were blocked and why
- **Progress Feedback** - Real-time status updates in UI

## Docker Setup

### Volumes

The docker-compose configuration uses three volumes:

1. **`./notes`** (bind mount) - Study notes output
   - Appears on host at `./notes/`
   - Organized by subject
   - Contains markdown files and PDFs

2. **`tracker-data`** (named volume) - Exit node tracker persistence
   - Tracks which Tor exit IPs were used
   - Enforces 24-hour cooldown
   - Survives container restarts
   - **Location:** Docker managed volume

3. **`tor-data`** (named volume) - Tor configuration
   - Tor circuit state
   - Docker managed volume

### Managing Volumes

```bash
# View volume data
docker volume inspect ytstudybuddy_tracker-data

# Backup tracker data
docker run --rm -v ytstudybuddy_tracker-data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/tracker-backup.tar.gz -C /data .

# Restore tracker data
docker run --rm -v ytstudybuddy_tracker-data:/data \
  -v $(pwd):/backup alpine \
  tar xzf /backup/tracker-backup.tar.gz -C /data

# Reset tracker (clear all IP history)
docker volume rm ytstudybuddy_tracker-data
docker-compose up -d
```

## Retry System

Failed jobs automatically retry every 15 minutes with fresh Tor exit IPs.

### Usage

```bash
# Check retry status
python retry_failed_jobs.py --status

# Retry all eligible jobs once
python retry_failed_jobs.py

# Continuous monitoring (recommended)
python retry_failed_jobs.py --watch

# Custom interval (30 minutes)
python retry_failed_jobs.py --watch --interval 30
```

See [RETRY_GUIDE.md](RETRY_GUIDE.md) for complete documentation.

## Tor Diagnostics

Test Tor connection and exit node diversity:

```bash
python diagnose_tor.py
```

Output shows:
- Current exit IP
- YouTube accessibility test
- 10 random exit nodes tested
- Success rate and recommendations

## File Organization

```
notes/
├── processing_log.json           # Complete job history
├── exit_nodes.json               # Tor IP tracker (24h cooldown)
├── AI/
│   ├── video_title_1.md
│   ├── Assessment_video_title_1.md
│   └── pdfs/
│       ├── video_title_1.pdf
│       └── Assessment_video_title_1.pdf
└── Programming/
    └── ...
```

## Processing Log

Every job (success/failure) logged to `notes/processing_log.json`:

```json
{
  "video_id": "abc123",
  "worker_id": 2,
  "success": true,
  "processing_duration": 58.8,
  "exit_ip": "192.42.116.184",
  "retry_count": 0,
  "timings": {
    "fetch_transcript": 5.2,
    "generate_notes": 20.3,
    "generate_assessment": 28.1,
    "write_files": 0.7
  },
  "error": null
}
```

### Query Examples

```bash
# Failed jobs only
cat notes/processing_log.json | jq '.[] | select(.success == false)'

# Jobs that used Tor
cat notes/processing_log.json | jq '.[] | select(.transcript_metadata.method == "tor")'

# Average processing time
cat notes/processing_log.json | jq '[.[] | select(.success) | .processing_duration] | add / length'

# Blocked exit IPs
cat notes/processing_log.json | jq '.[] | select(.success == false) | .transcript_metadata.tor_exit_ip' | sort | uniq
```

## Exit Node Tracking

The exit node tracker (`notes/exit_nodes.json`) prevents reusing recently blocked IPs:

```json
{
  "192.42.116.184": {
    "last_used": "2025-10-17T14:30:45.123456",
    "first_seen": "2025-10-17T12:15:30.000000",
    "use_count": 5,
    "last_worker_id": 2
  }
}
```

**Cooldown Period:** 24 hours (configurable)

**Why 24 hours?** YouTube blocks persist for extended periods. Using fresh IPs dramatically improves success rate.

## Web Interface

The Streamlit UI shows:

- **Process Videos** - Batch processing with playlist extraction
- **Results** - Knowledge graph and cross-references
- **Logs** - Processing history with failure details
  - Exit IP used for each attempt
  - Human-readable timestamps ("2 hours ago")
  - Failure reasons
  - Retry count
- **Exit Nodes** - IP cooldown status
  - IPs in cooldown (24h)
  - Available IPs
  - Last used times
  - Use counts

## Performance

### Parallel Processing
- **3 Workers:** ~54% faster than sequential
- **Per-Worker Tor Connections:** Unique exit IPs
- **Job Logging:** Complete audit trail

### Retry System Impact
- **Without Retry:** 60% failure rate (temporary blocks)
- **With Retry:** ~90% eventual success rate
- **24h IP Cooldown:** Prevents repeated blocks

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Development mode with source mounting
docker-compose -f docker-compose.dev.yml up --build
```

## Troubleshooting

### All Jobs Failing

1. **Check Tor connection:**
   ```bash
   python diagnose_tor.py
   ```

2. **Restart Tor:**
   ```bash
   docker-compose restart tor-proxy
   ```

3. **Check API key:**
   ```bash
   echo $CLAUDE_API_KEY
   ```

### YouTube Blocking All Exits

1. **Increase retry interval:**
   ```bash
   python retry_failed_jobs.py --watch --interval 30
   ```

2. **Reduce parallel workers:**
   - Use `--workers 1` or `--workers 2`
   - Fewer simultaneous requests = less blocking

3. **Check exit node tracker:**
   ```bash
   cat notes/exit_nodes.json | jq 'length'
   ```
   If many IPs tracked, they may all be in cooldown

## Documentation

- [RETRY_GUIDE.md](RETRY_GUIDE.md) - Complete retry system guide
- [docs/architecture.md](docs/architecture.md) - Pipeline architecture
- [docs/debugging.md](docs/debugging.md) - PyCharm debugging
- [docs/job-logging.md](docs/job-logging.md) - Log analysis
- [docs/pdf-export.md](docs/pdf-export.md) - PDF themes
- [docs/docker.md](docs/docker.md) - Docker setup

## License

MIT License - See LICENSE file
