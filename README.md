# YouTube Study Buddy 📚

**Technology moves faster than traditional education.** YouTube has become the world's largest university, but watching videos is passive learning. **YouTube Study Buddy** transforms YouTube content into an active learning system using AI-powered note generation, learning assessments, and knowledge graph building.

## 🧠 Why This Matters

Traditional note-taking creates the "illusion of competence" – you transcribe content but don't truly learn. YouTube Study Buddy applies cognitive science:
- **Active recall** through assessment questions
- **Spaced repetition** by separating note review from watching
- **Interconnected learning** with cross-referenced knowledge graphs

**Result:** Turn passive watching into deep understanding with structured notes, learning questions, and automatic connections to everything you've studied.

## 💰 The Value

**Paid alternatives** ($10-50/month): NoteGPT, Notta, Eightify – subscription required
**YouTube Study Buddy**: 100% free, runs locally, unlimited use, your data stays private

⭐ **If you find this useful, please give it a star on GitHub!** It helps others discover the project.

## ✨ What You Get

- 🤖 **AI Study Notes** – Claude AI transforms transcripts into structured notes with key concepts, examples, and connections
- 📝 **Learning Assessments** – Auto-generated questions that test deep understanding, not just recall
- 🔗 **Knowledge Graph** – Automatic cross-referencing finds connections across all your notes
- 🗺️ **Obsidian Integration** – Notes include `[[wiki-style]]` links that create an interconnected knowledge base
- 🏷️ **Auto-Organization** – ML-powered categorization sorts notes by subject automatically
- 📋 **Playlist Support** – Process entire YouTube playlists with one click

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Claude API key ([Get free key](https://console.anthropic.com/))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/fluidnotions/YouTube-Study-Buddy.git
cd YouTube-Study-Buddy

# 2. Create .env file with your API key
echo "CLAUDE_API_KEY=your_key_here" > .env
echo "USER_ID=$(id -u)" >> .env
echo "GROUP_ID=$(id -g)" >> .env

# 3. Pull and start the pre-built image (recommended)
docker-compose pull
docker-compose up -d

# 4. Access the app at http://localhost:8501
```

**For development:** See [DOCKER.md](DOCKER.md) for building from source and development workflow.

**Manage containers**:
```bash
# View logs
docker logs -f youtube-study-buddy  # App logs
docker logs -f tor-proxy            # Tor logs

# Stop
docker compose down

# Restart
docker compose restart

# Rebuild and restart
docker compose up -d --build
```

### Architecture

This project uses a **two-container architecture**:
- **tor-proxy**: Dedicated Tor SOCKS proxy for bypassing YouTube rate limiting
- **app**: Python application with Streamlit UI

See [Why Separate Containers Work Better](docs/WHY_SEPARATE_CONTAINERS.md) for technical details.

### Features

- **Tor Integration**: Bypasses YouTube IP blocks via separate Tor container
- **Circuit Rotation**: Automatically rotates Tor circuits on retry attempts
- **Health Checks**: Built-in monitoring for both Tor and Streamlit
- **Easy Debugging**: Clear separation between Tor and app logs
- **Reliable**: Proven architecture using battle-tested `dperson/torproxy` image

## 📡 Transcript Fetching Methods

YouTube Study Buddy uses a two-tier approach for reliable transcript fetching:

### 1. Primary: Tor Proxy (Recommended)
- Routes requests through Tor network to bypass IP blocking
- Circuit rotation for retry attempts
- Most reliable for batch processing

### 2. Fallback: yt-dlp
- Automatically used when Tor fails
- Direct connection to YouTube
- Provides additional reliability layer

### Success Rate
With the dual-method approach:
- **Tor success rate**: ~70-80%
- **YT-DLP fallback**: Covers remaining 20-30%
- **Combined success rate**: >95%

Statistics are displayed after processing showing which method was used for each video.

## 🗺️ Using With Obsidian

[Obsidian](https://obsidian.md) is a free knowledge base app that lets you build a "second brain." YouTube Study Buddy generates notes with:
- **Wiki-style links** (`[[Related Topic]]`) that connect concepts across videos
- **Graph view** showing how your knowledge interconnects
- **Bidirectional linking** – see what relates to each note
- **Local storage** – all your notes stay on your machine

**Setup:**
1. Download [Obsidian](https://obsidian.md) (free)
2. Open your configured output folder as a vault in Obsidian
3. Enable "Graph View" to see your knowledge connections
4. As you process videos, watch your knowledge graph grow automatically

## 📄 What Gets Created

Every video generates two files in your configured output folder:

**1. Study Notes** (`Video_Title.md`)
- Structured summaries with key concepts
- `[[Wiki-style links]]` connecting to related topics
- Opens in Obsidian with full graph view

**2. Learning Assessment** (`Video_Title_Assessment.md`)
- Gap analysis questions (what did your brain filter out?)
- Application questions (how would you use this?)
- One-up challenges (how could you improve it?)
- Synthesis questions (how does this connect to other topics?)

**Example Output:**

```markdown
## Core Concepts
- Self-attention mechanism replaces recurrent layers
- Multi-head attention enables parallel processing

## Connections & Relationships
This connects to [[Neural Machine Translation]] and [[BERT Architecture]]...
```

Your notes automatically link together, building a knowledge graph you can visualize in Obsidian.

---

## 🛠️ Development & Advanced Usage

See the [docs](docs/) folder for:
- **[Quick Start Guide](docs/QUICKSTART.md)** - Detailed Docker usage
- **[Build Instructions](docs/BUILD_INSTRUCTIONS.md)** - Building from source
- **[Technical Setup](docs/technical/alternative-setup.md)** - Running without Docker
- **[Solution Summary](docs/SOLUTION_SUMMARY.md)** - Architecture details

### CLI Usage (Development)

```bash
# Install package locally
uv sync

# Process URLs directly
uv run youtube-study-buddy "https://youtube.com/watch?v=xyz"

# Process from file (sequential)
uv run youtube-study-buddy --file playlist-urls.txt

# Parallel processing (faster for batches)
uv run youtube-study-buddy --parallel --file playlist-urls.txt

# Parallel with 5 workers
uv run youtube-study-buddy -p -w 5 --file playlist-urls.txt

# Full help
uv run youtube-study-buddy --help
```

## ⚡ Parallel Processing

Process multiple videos simultaneously for faster batch operations:

### Performance

| Mode | Time per Video | 10 Videos | Speedup |
|------|---------------|-----------|---------|
| Sequential | ~60s | 10 minutes | 1x |
| Parallel (3 workers) | ~25s | 4 minutes | **2.5x** |
| Parallel (5 workers) | ~20s | 3.3 minutes | **3x** |

### CLI Usage

```bash
# Sequential (default)
uv run youtube-study-buddy --file urls.txt

# Parallel with 3 workers (recommended)
uv run youtube-study-buddy --parallel --file urls.txt

# Parallel with 5 workers (faster but higher rate limit risk)
uv run youtube-study-buddy --parallel --workers 5 --file urls.txt
```

### Streamlit UI

The web interface automatically supports parallel processing:
1. Open the Processing Settings section
2. Enable "Parallel Processing" checkbox
3. Adjust worker count (1-5, default: 3)
4. Process your videos with 2-3x speedup

### Per-Worker Tor Connections

**NEW:** Each parallel worker now gets its own independent Tor connection! This provides:

- **Different Exit Nodes**: Each worker likely uses a different Tor exit node
- **Better Isolation**: Connection failures in one worker don't affect others
- **Improved Reliability**: No contention for shared Tor circuit
- **Rate Limit Protection**: Different exit IPs reduce YouTube rate limiting risk

This is automatically enabled for all parallel processing (CLI, Streamlit, and debug mode).

### Considerations

- **Rate Limiting**: More workers = more concurrent requests, but per-worker Tor connections help
- **Recommended**: 3-5 workers for optimal balance
- **Memory**: Each worker has its own VideoProcessor instance (increased memory usage)
- **API Limits**: Claude API rate limits still apply
- **Thread Safety**: File operations and knowledge graph updates are thread-safe
- **Tor Circuits**: Each worker establishes its own Tor circuit through the shared proxy

---

## 📜 License & Contributing

MIT License - Free to use, modify, and distribute.

Contributions welcome! Open an issue or pull request on GitHub.