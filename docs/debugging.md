# PyCharm Debugging Guide for CLI Commands

This guide shows you how to debug any CLI command in PyCharm with full breakpoint support.

## Quick Start

I've created pre-configured run configurations in the `.run/` folder. They'll appear in your PyCharm toolbar automatically:

- **CLI - Single Video**: Debug single video processing
- **CLI - Parallel Processing**: Debug parallel batch processing
- **CLI - With Subject**: Debug with subject categorization
- **CLI - Help**: Debug help display

Just select one from the dropdown and click the **Debug** button (bug icon)!

## Technique 1: Direct Python Script (Recommended)

This is the best approach for debugging CLI commands with full breakpoint support.

### Setup Steps:

1. **Open Run/Debug Configurations**
   - Top toolbar → dropdown next to Run button → "Edit Configurations..."
   - Or: Run → Edit Configurations...

2. **Add New Python Configuration**
   - Click `+` → Python

3. **Configure**:
   ```
   Name:           CLI - Custom Command
   Script path:    /path/to/ytstudybuddy/src/yt_study_buddy/cli.py
   Parameters:     <your CLI arguments>
   Python interpreter: Project Default (Python 3.13 ytstudybuddy)
   Working directory:  /path/to/ytstudybuddy
   ```

4. **Example Configurations**:

   **Single Video**:
   ```
   Parameters: https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ```

   **Parallel Processing**:
   ```
   Parameters: --parallel --workers 3 --file urls.txt
   ```

   **With Subject**:
   ```
   Parameters: --subject "Machine Learning" https://youtube.com/watch?v=xyz
   ```

   **Multiple Options**:
   ```
   Parameters: --parallel --workers 5 --subject "Python" --file videos.txt
   ```

5. **Set Breakpoints**:
   - Click in the gutter (left of line numbers) in any Python file
   - Breakpoints work in:
     - `cli.py:main()` - Entry point
     - `cli.py:process_single_url()` - Video processing
     - `video_processor.py` - Transcript fetching
     - `study_notes_generator.py` - Claude API calls
     - `parallel_processor.py` - Parallel execution

6. **Click Debug** (bug icon)
   - Program stops at breakpoints
   - Inspect variables, step through code, evaluate expressions

## Technique 2: Parameterized Run Configuration Templates

Create reusable templates that you can quickly modify:

### Create Template:

1. Create configuration as above
2. In Parameters field, use placeholders:
   ```
   $Prompt$
   ```

3. When you run it, PyCharm will ask for the parameters each time

### Example Template:
```
Name: CLI - Ask Parameters
Script: src/yt_study_buddy/cli.py
Parameters: $VIDEO_URL$
Prompt variables:
  VIDEO_URL: "Enter YouTube URL"
```

## Technique 3: Debug with sys.argv Override

For testing different argument combinations quickly:

### Create a debug wrapper script:

**`debug_cli_wrapper.py`**:
```python
#!/usr/bin/env python3
"""Wrapper for debugging CLI with different arguments."""
import sys
from yt_study_buddy.cli import main

# Override sys.argv to simulate CLI arguments
# Change these to test different commands:
sys.argv = [
    'youtube-study-buddy',
    '--parallel',
    '--workers', '3',
    '--file', 'urls.txt'
]

# Run the CLI
if __name__ == '__main__':
    main()
```

Then debug `debug_cli_wrapper.py` directly!

**Benefits**:
- Change arguments by editing the file
- No need to reconfigure run settings
- Version control your test scenarios

## Technique 4: pytest-style Debugging

For testing specific CLI argument combinations:

**`tests/test_cli_debug.py`**:
```python
import sys
from yt_study_buddy.cli import main

def test_single_video_debug():
    """Debug single video processing."""
    sys.argv = ['cli', 'https://youtube.com/watch?v=dQw4w9WgXcQ']
    main()  # Set breakpoint here

def test_parallel_debug():
    """Debug parallel processing."""
    sys.argv = ['cli', '--parallel', '--workers', '3', '--file', 'urls.txt']
    main()  # Set breakpoint here

def test_with_subject_debug():
    """Debug with subject."""
    sys.argv = ['cli', '--subject', 'Python', 'https://youtube.com/watch?v=xyz']
    main()  # Set breakpoint here
```

Run/Debug individual test functions from PyCharm!

## Debugging Specific Components

### Debug Tor Transcript Fetching:
```python
# Set breakpoint in: src/yt_study_buddy/tor_transcript_fetcher.py
# At line: 219 (inside _ensure_unique_exit)
# Or line: 125 (inside fetch_transcript)
```

**Run**: CLI - Single Video (with breakpoints set)

### Debug Parallel Worker Pool:
```python
# Set breakpoint in: src/yt_study_buddy/parallel_processor.py
# At line: 95 (worker_task function)
# Or: src/yt_study_buddy/tor_transcript_fetcher.py
# At line: 168 (TorExitNodePool.acquire)
```

**Run**: CLI - Parallel Processing

### Debug Claude API Calls:
```python
# Set breakpoint in: src/yt_study_buddy/study_notes_generator.py
# At line: 66 (generate_notes method)
```

### Debug Auto-categorization:
```python
# Set breakpoint in: src/yt_study_buddy/auto_categorizer.py
# At line: 83 (categorize_video method)
```

## Environment Variables

If your CLI needs environment variables (like API keys), add them to the run configuration:

1. Edit configuration
2. Expand "Environment variables"
3. Add:
   ```
   CLAUDE_API_KEY=your_key_here
   ANTHROPIC_API_KEY=your_key_here
   ```

Or create `.env` file (already supported by the app):
```bash
CLAUDE_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

## Tips & Tricks

### 1. Conditional Breakpoints
Right-click breakpoint → Edit → Add condition:
```python
video_id == "dQw4w9WgXcQ"
worker_id == 2
attempt > 3
```

### 2. Logging Breakpoints
Right-click breakpoint → Edit → Check "Evaluate and log"
```python
f"Processing {url} with worker {worker_id}"
```
Logs without stopping execution!

### 3. Debug Console
When stopped at breakpoint, use Debug Console to:
```python
# Inspect variables
print(video_id)
print(fetcher.proxies)

# Call methods
result = fetcher.check_tor_connection()

# Modify state
self.max_workers = 5
```

### 4. Step Filters
Configure to skip library code:
- Settings → Build, Execution, Deployment → Python Debugger
- Add patterns to skip: `*/site-packages/*`, `*/anthropic/*`

### 5. Attach to Process
For debugging running processes:
- Run → Attach to Process
- Select Python process
- Works if process has `pydevd` available

## Quick Reference

| Want to Debug | Script Path | Example Parameters |
|---------------|-------------|-------------------|
| Single video | `src/yt_study_buddy/cli.py` | `https://youtube.com/watch?v=xyz` |
| Multiple videos | `src/yt_study_buddy/cli.py` | `URL1 URL2 URL3` |
| From file | `src/yt_study_buddy/cli.py` | `--file urls.txt` |
| Parallel | `src/yt_study_buddy/cli.py` | `--parallel --file urls.txt` |
| With workers | `src/yt_study_buddy/cli.py` | `--parallel --workers 5 --file urls.txt` |
| Subject | `src/yt_study_buddy/cli.py` | `--subject "Python" URL` |
| No assessments | `src/yt_study_buddy/cli.py` | `--no-assessments URL` |
| Help | `src/yt_study_buddy/cli.py` | `--help` |

## Debugging UV-specific Issues

If you need to debug UV's environment handling:

1. **See what UV does**:
   ```bash
   uv run --verbose python src/yt_study_buddy/cli.py --help
   ```

2. **Use UV's Python directly**:
   - Find UV's Python: `which python` (when in uv environment)
   - Set that as interpreter: `.venv/bin/python`

3. **Check UV environment**:
   ```bash
   uv run python -c "import sys; print(sys.path)"
   ```

## Common Issues

### "Module not found" when debugging
**Solution**: Check Working Directory is set to project root

### Breakpoints not hit
**Solution**: Ensure you're using the correct Python interpreter (`.venv/bin/python`)

### Environment variables not loaded
**Solution**: Add them to run configuration or ensure `.env` file exists

### Can't debug parallel workers
**Solution**: Set breakpoints in worker function, or use logging breakpoints

---

## The Bottom Line

You **never** need to rely on `debug_main.py` again!

Just point PyCharm at:
- **Script**: `src/yt_study_buddy/cli.py`
- **Parameters**: Whatever CLI args you want
- **Interpreter**: Project's `.venv/bin/python`

Set breakpoints anywhere in your codebase and debug away! 🐛
