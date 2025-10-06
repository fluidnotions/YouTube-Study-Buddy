# Alternative Setup Methods

This guide covers non-Docker ways to run YouTube Study Buddy, including CLI usage, development setup, and manual installation.

---

## Quick Links

- [Running from Source](#running-from-source)
- [Web Interface (Streamlit)](#web-interface-streamlit)
- [Command-Line Usage](#command-line-usage)
- [Playlist Extraction](#playlist-extraction)
- [Development Setup](#development-setup)

---

## Running from Source

### Prerequisites
- Python 3.13+
- UV package manager

### Installation

**Option 1: Install as Package (Recommended)**
```bash
# Install UV
pip install uv

# Clone repository
git clone https://github.com/fluidnotions/YouTube-Study-Buddy.git
cd YouTube-Study-Buddy

# Install package with dependencies
uv sync --dev

# Now you can run: youtube-study-buddy <urls>
```

**Option 2: Development Mode**
```bash
# Clone and install in editable mode
git clone https://github.com/fluidnotions/YouTube-Study-Buddy.git
cd YouTube-Study-Buddy
uv sync --dev

# Run directly with: python main.py or uv run youtube-study-buddy
```

### Configuration

Create a `.env` file in the project directory:

```bash
# Required
CLAUDE_API_KEY=your_api_key_here

# Optional - ML Model Configuration
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
```

**Get Claude API Key:**
- Visit [https://console.anthropic.com/](https://console.anthropic.com/)
- Create account (free tier available)
- Generate API key

**Model Options:**
- `all-MiniLM-L6-v2` - Fast, good quality (default)
- `all-mpnet-base-v2` - Higher quality, slower
- `all-distilroberta-v1` - Alternative architecture

Or set environment variables:
```bash
export CLAUDE_API_KEY=your_api_key_here
export SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
```

---

## Web Interface (Streamlit)

### Launch the Web App

```bash
# Using UV
uv run streamlit run streamlit_app.py

# Using Python directly
streamlit run streamlit_app.py
```

Open browser to **http://localhost:8501**

### Features

- **Unified workflow** - All settings and URL input in one place
- **Playlist extraction** - Extract URLs directly from YouTube playlists
- **Inline configuration** - Subject, transcript method, features all visible together
- **Real-time progress** - Watch processing status for each video
- **Results tracking** - Review all processed videos in your session
- **No command-line needed** - Perfect for users who prefer GUIs

### Using the Interface

1. **Configure Settings** (top of Process Videos tab):
   - Subject (optional - leave blank for auto-categorization)
   - Transcript method (API/Scraper/Tor)
   - Enable/disable assessments and auto-categorization

2. **Add Videos**:
   - **Option A**: Paste playlist URL → Click "Extract URLs"
   - **Option B**: Paste video URLs directly (one per line)

3. **Process**: Click "Process Videos" button

4. **View Results**: Switch to Results tab to see processed videos

---

## Command-Line Usage

### Basic Commands

**Process URLs from Command Line:**
```bash
# Single URL
uv run youtube-study-buddy "https://youtube.com/watch?v=VIDEO_ID"

# Multiple URLs
uv run youtube-study-buddy "https://youtube.com/watch?v=abc" "https://youtube.com/watch?v=xyz"

# With Python directly
python main.py "https://youtube.com/watch?v=VIDEO_ID"
```

**With Subject Organization:**
```bash
# Manual subject (bypasses auto-categorization)
uv run youtube-study-buddy --subject "Machine Learning" "https://youtube.com/watch?v=xyz"

# Subject-only cross-referencing (no global connections)
uv run youtube-study-buddy --subject "AI Ethics" --subject-only "https://youtube.com/watch?v=xyz"
```

**Process URLs from File:**
```bash
# Process URLs from urls.txt (default)
uv run youtube-study-buddy --file urls.txt

# Custom URL file
uv run youtube-study-buddy --file my_videos.txt

# With subject
uv run youtube-study-buddy --subject "Data Science" --file python-videos.txt
```

### Command-Line Flags

| Flag | Description |
|------|-------------|
| `--subject <name>` | Organize notes by subject (creates `Study notes/<subject>/` folder) |
| `--subject-only` | Cross-reference only within that subject (default: global) |
| `--file <filename>` | Read URLs from file (one per line) |
| `--no-assessments` | Disable assessment generation |
| `--no-auto-categorize` | Disable auto-categorization |
| `--help` | Show help message |

### Transcript Method

**Tor (Only Option):**
- Routes through Tor proxy for reliable fetching
- Best for bypassing IP blocks and rate limits
- Automatically set up via docker-compose
- No configuration needed for Docker users

### Tor Proxy Setup

**Using Docker:**
```bash
docker-compose up -d tor-proxy
```

**Manual Installation:**
```bash
# Linux
sudo apt-get install tor

# Mac
brew install tor

# Start Tor
tor
```

**Using the App:**
```bash
# Tor is now the default and only method
uv run youtube-study-buddy "https://youtube.com/watch?v=xyz"
```

---

## Playlist Extraction

### Option 1: Web Interface (Easiest)
1. Open Streamlit app
2. Go to "Process Videos" tab
3. Paste playlist URL
4. Click "Extract URLs"
5. Edit if needed, then process

### Option 2: yt-dlp Command Line

**Install yt-dlp:**
```bash
uv pip install yt-dlp
```

**Extract URLs:**
```bash
# Save to urls.txt
yt-dlp --flat-playlist --print url "https://www.youtube.com/playlist?list=PLAYLIST_ID" > urls.txt

# Get URLs with titles for reference
yt-dlp --flat-playlist --print "%(title)s - %(url)s" "PLAYLIST_URL"
```

**Process extracted URLs:**
```bash
uv run youtube-study-buddy --file urls.txt
```

### URLs File Format

Create `urls.txt` with one YouTube URL per line:

```
https://www.youtube.com/watch?v=abc123
https://youtu.be/def456
# Comments start with # and are ignored

https://www.youtube.com/watch?v=ghi789
```

---

## Development Setup

### For Contributors

```bash
# Clone repository
git clone https://github.com/fluidnotions/YouTube-Study-Buddy.git
cd YouTube-Study-Buddy

# Install with development dependencies
uv sync --dev

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Format code
uv run black .
```

### Project Structure

```
YouTube-Study-Buddy/
├── src/
│   └── yt_study_buddy/
│       ├── video_processor.py
│       ├── study_notes_generator.py
│       ├── assessment_generator.py
│       ├── auto_categorizer.py
│       ├── knowledge_graph.py
│       ├── obsidian_linker.py
│       └── transcript_provider.py
├── main.py              # CLI entry point
├── streamlit_app.py     # Web interface
├── debug_main.py        # Debug entry point
└── tests/              # Test suite
```

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_video_processor.py

# With coverage
uv run pytest --cov=src/yt_study_buddy
```

---

## Output Structure

Notes are saved in organized folders:

```
Study notes/
├── Machine Learning/
│   ├── Transformers_Explained.md
│   ├── Transformers_Explained_Assessment.md
│   ├── Neural_Networks_Intro.md
│   └── Neural_Networks_Intro_Assessment.md
├── Python/
│   ├── Async_Programming.md
│   └── Async_Programming_Assessment.md
└── General/
    └── Other_Videos.md
```

---

## Troubleshooting

### API Key Issues

**Error: Claude API key not found**
- Ensure `.env` file exists in project directory
- Check `CLAUDE_API_KEY` is set correctly
- Verify no extra spaces in the key

### Rate Limiting

**Error: 429 Too Many Requests**
- Tor proxy is now used by default to minimize rate limiting
- Ensure docker-compose tor-proxy service is running
- Add longer delays between videos in batch processing if needed

### Tor Connection Issues

**Error: Tor connection failed**
- Ensure Tor is running: `docker-compose up -d tor-proxy`
- Check port 9050 is available
- Verify firewall isn't blocking connections

### Import Errors

**Error: Module not found**
- Ensure you're in the project directory
- Reinstall dependencies: `uv sync` or `pip install -r requirements.txt`
- Check Python version: `python --version` (needs 3.13+)

---

## FAQ

**Q: Can I use this without Claude API?**
A: No, Claude API is required for note generation. However, there's a free tier available.

**Q: How much does Claude API cost?**
A: Claude has a free tier. Beyond that, costs are based on token usage (typically pennies per video).

**Q: Can I customize the note template?**
A: Yes, edit `src/yt_study_buddy/study_notes_generator.py` to modify the prompt template.

**Q: Does this work with private/unlisted videos?**
A: Yes, as long as you have the URL and the video has captions enabled.

**Q: Can I process videos in languages other than English?**
A: Yes, the transcript API supports multiple languages. Auto-detection works, or specify with transcript method settings.

---

## Need Help?

- **Issues**: [GitHub Issues](https://github.com/fluidnotions/YouTube-Study-Buddy/issues)
- **Discussions**: [GitHub Discussions](https://github.com/fluidnotions/YouTube-Study-Buddy/discussions)
- **Documentation**: See [PLAN.md](../../PLAN.md) for roadmap and future features
