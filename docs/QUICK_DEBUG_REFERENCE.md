# Quick Debug Reference Card

## 🚀 Fastest Way to Debug CLI Commands

### Method 1: Pre-configured Run Configs (Instant)
1. Look at top toolbar in PyCharm
2. Select from dropdown:
   - `CLI - Single Video`
   - `CLI - Parallel Processing`
   - `CLI - With Subject`
   - `Debug CLI Wrapper` ⭐ (Most Flexible)
3. Set breakpoints in any `.py` file
4. Click Debug (bug icon) 🐛

### Method 2: Quick Custom Config (30 seconds)
1. Top toolbar → "Edit Configurations..."
2. Click `+` → Python
3. Fill in:
   ```
   Script: src/yt_study_buddy/cli.py
   Parameters: <your args>
   Interpreter: .venv/bin/python
   ```
4. Click Debug

### Method 3: Edit debug_cli.py (Easiest for Testing)
1. Open `debug_cli.py`
2. Edit the `CLI_ARGS` list:
   ```python
   CLI_ARGS = ['--parallel', '--file', 'urls.txt']
   ```
3. Right-click file → Debug 'debug_cli'
4. Done! ✅

## 🎯 Common Debug Scenarios

| What to Debug | Where to Set Breakpoint | Run Config |
|---------------|------------------------|------------|
| Tor exit node selection | `tor_transcript_fetcher.py:219` | CLI - Parallel Processing |
| Transcript fetching | `tor_transcript_fetcher.py:125` | CLI - Single Video |
| Worker pool | `parallel_processor.py:95` | CLI - Parallel Processing |
| Claude API | `study_notes_generator.py:66` | CLI - Single Video |
| Auto-categorize | `auto_categorizer.py:83` | CLI - Single Video |
| CLI argument parsing | `cli.py:382` | Any |
| Video processing flow | `cli.py:79` | Any |

## 🔍 Breakpoint Tips

**Conditional Breakpoint** (right-click breakpoint):
```python
worker_id == 2
video_id == "dQw4w9WgXcQ"
attempt > 3
```

**Logging Breakpoint** (logs without stopping):
```python
f"Worker {worker_id} processing {url}"
```

## 🛠️ The Three Files You Need

1. **`debug_cli.py`** - Edit args, debug instantly
2. **`DEBUGGING_GUIDE.md`** - Full documentation
3. **`.run/*.xml`** - Pre-made configs (auto-loaded)

## 💡 Pro Tips

- Use `Debug CLI Wrapper` for quick iterations
- Edit `debug_cli.py` to test different argument combinations
- All breakpoints work across the entire codebase
- Debug Console (when paused): execute Python code live!

## ⚡ Example Workflow

```python
# 1. Open debug_cli.py
# 2. Change CLI_ARGS:
CLI_ARGS = ['--parallel', '--workers', '3', '--file', 'urls.txt']

# 3. Set breakpoint in tor_transcript_fetcher.py:
#    Line 219 (_ensure_unique_exit method)

# 4. Right-click debug_cli.py → Debug

# 5. When it hits breakpoint:
#    - Inspect variables: worker_id, connection_id, exit_ip
#    - Step through code (F8)
#    - Evaluate expressions in Debug Console
```

That's it! No more guessing, no more print statements. Full debugging power! 🎉
