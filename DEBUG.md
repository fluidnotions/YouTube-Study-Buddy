# Debug Configuration Guide

Easy debugging setup for PyCharm and other IDEs using `debug_main.py` with `.env.debug` configuration.

## Quick Start

### 1. Create Debug Environment File

```bash
# Copy the example file
cp .env.debug.example .env.debug

# Edit with your settings
nano .env.debug  # or use your preferred editor
```

### 2. Configure Your Debug Session

Edit `.env.debug` with your preferences:

```bash
# Required: Your Claude API key
CLAUDE_API_KEY=sk-ant-api03-xxxxx

# Where to save notes
DEBUG_OUTPUT_DIR=notes_debug

# URLs to process (comma-separated)
DEBUG_URLS=https://www.youtube.com/watch?v=example1,https://www.youtube.com/watch?v=example2

# Or use a file instead (one URL per line)
# DEBUG_URL_FILE=test_urls.txt
```

### 3. Run in PyCharm

1. Open `debug_main.py`
2. Right-click → **Debug 'debug_main'**
3. Set breakpoints as needed
4. Debug!

## Configuration Options

### Basic Settings

```bash
# Output directory (relative to project root)
DEBUG_OUTPUT_DIR=notes_debug

# Subject for organizing notes (empty = auto-detect)
DEBUG_SUBJECT=

# Enable global cross-referencing (vs subject-only)
DEBUG_GLOBAL_CONTEXT=true

# Generate assessment files (*_Assessment.md)
DEBUG_GENERATE_ASSESSMENTS=true

# Auto-categorize videos by subject
DEBUG_AUTO_CATEGORIZE=true
```

### Parallel Processing

```bash
# Enable parallel processing (faster for batches)
DEBUG_PARALLEL=false

# Number of concurrent workers (3-5 recommended)
DEBUG_MAX_WORKERS=3
```

**Per-Worker Tor Connections**: When parallel processing is enabled, each worker gets its own VideoProcessor instance with an independent Tor connection. This provides:
- Different Tor exit nodes per worker
- Better connection isolation
- Improved reliability
- Reduced rate limiting risk

Performance comparison:
- Sequential: ~60s per video
- Parallel (3 workers): ~25s per video (2.5x faster)
- Parallel (5 workers): ~20s per video (3x faster, higher rate limit risk)

### URL Configuration

**Option 1: Direct URLs (comma-separated)**
```bash
DEBUG_URLS=https://www.youtube.com/watch?v=abc123,https://www.youtube.com/watch?v=def456
```

**Option 2: URL File (one per line)**
```bash
DEBUG_URL_FILE=test_urls.txt
```

Create `test_urls.txt`:
```
https://www.youtube.com/watch?v=abc123
https://www.youtube.com/watch?v=def456
# Comments are supported
https://www.youtube.com/watch?v=ghi789
```

## Example Configurations

### Single Video Test

```bash
CLAUDE_API_KEY=sk-ant-api03-xxxxx
DEBUG_OUTPUT_DIR=notes_test
DEBUG_URLS=https://www.youtube.com/watch?v=dQw4w9WgXcQ
DEBUG_PARALLEL=false
```

### Batch Processing (Parallel)

```bash
CLAUDE_API_KEY=sk-ant-api03-xxxxx
DEBUG_OUTPUT_DIR=notes_batch
DEBUG_URL_FILE=playlist_urls.txt
DEBUG_PARALLEL=true
DEBUG_MAX_WORKERS=3
```

### Subject-Specific

```bash
CLAUDE_API_KEY=sk-ant-api03-xxxxx
DEBUG_OUTPUT_DIR=notes
DEBUG_SUBJECT=Machine Learning
DEBUG_GLOBAL_CONTEXT=false
DEBUG_URLS=https://www.youtube.com/watch?v=example
```

### Testing Without Assessments

```bash
CLAUDE_API_KEY=sk-ant-api03-xxxxx
DEBUG_OUTPUT_DIR=notes_quick
DEBUG_GENERATE_ASSESSMENTS=false
DEBUG_AUTO_CATEGORIZE=false
DEBUG_URLS=https://www.youtube.com/watch?v=example
```

## Debug Output

The debug session shows configuration before processing:

```
======================================================================
DEBUG MODE - YouTube Study Buddy
======================================================================
Output Directory:    notes_debug
Subject:             Auto-detect
Global Context:      Enabled
Assessments:         Enabled
Auto-categorize:     Enabled
Parallel Processing: Disabled
Transcript Provider: Tor (exclusive)
======================================================================

📋 Processing 2 URL(s) from DEBUG_URLS

URLs to process:
  1. https://www.youtube.com/watch?v=abc123
  2. https://www.youtube.com/watch?v=def456

Processing 2 URL(s)...
...
```

## Breakpoint Suggestions

### Video Processing Flow

Set breakpoints at:
- `cli.py:62` - `process_single_url()` start
- `cli.py:85` - After transcript fetch
- `cli.py:135` - After note generation
- `cli.py:158` - After Obsidian linking

### Parallel Processing

Set breakpoints at:
- `parallel_processor.py:45` - Worker pool creation
- `parallel_processor.py:78` - Individual video processing
- `cli.py:234` - Parallel result collection

### Assessment Generation

Set breakpoints at:
- `assessment_generator.py:38` - `generate_assessment()` start
- `assessment_generator.py:98` - Claude API call
- `assessment_generator.py:217` - Assessment formatting

## Troubleshooting

### No URLs Found

**Problem**: "❌ No URLs configured!"

**Solution**: Set either `DEBUG_URLS` or `DEBUG_URL_FILE` in `.env.debug`

### API Key Not Found

**Problem**: "❌ ERROR: CLAUDE_API_KEY not found"

**Solution**: Add `CLAUDE_API_KEY=your_key` to `.env.debug`

### File Not Found

**Problem**: ".env.debug not found!"

**Solution**:
```bash
cp .env.debug.example .env.debug
# Edit .env.debug with your settings
```

### Tor Proxy Issues

If running outside Docker and Tor is not available, the script will show:
```
✗ Tor connection not available - cannot fetch transcripts
```

**Solution**:
1. Use Docker: `docker-compose up -d tor-proxy`
2. Or set up local Tor (see main README)

## Tips

1. **Quick Iterations**: Use a single short video for quick testing
2. **Output Separation**: Use different `DEBUG_OUTPUT_DIR` for each test
3. **URL Files**: Maintain test URL files for different scenarios
4. **Parallel Testing**: Start with 2-3 workers, increase cautiously
5. **Rate Limits**: If you hit rate limits, reduce workers or add delays

## Advanced: Multiple Debug Configs

Create multiple debug configurations:

```bash
# Quick single video test
.env.debug.quick

# Parallel batch test
.env.debug.batch

# Subject-specific test
.env.debug.subject
```

Modify `debug_main.py` to load different configs:
```python
# At the top of load_debug_config()
debug_config_name = os.getenv('DEBUG_CONFIG', 'debug')
debug_env_path = current_dir / f".env.{debug_config_name}"
```

Then run:
```bash
DEBUG_CONFIG=debug.quick python debug_main.py
```

## Files

- `.env.debug.example` - Template with all options documented
- `.env.debug` - Your personal config (ignored by git)
- `debug_main.py` - Debug entry point
- `DEBUG.md` - This file

## See Also

- [README.md](README.md) - Main project documentation
- [DOCKER.md](DOCKER.md) - Docker setup and workflow
- [FIXES_APPLIED.md](FIXES_APPLIED.md) - Recent bug fixes
