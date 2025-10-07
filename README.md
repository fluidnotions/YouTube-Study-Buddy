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

```bash
# 1. Get a free Claude API key from https://console.anthropic.com/

# 2. Run with Docker (simplest method)
docker run -d \
  --name youtube-study-buddy \
  -p 8501:8501 \
  -e CLAUDE_API_KEY=your_key_here \
  -v ./notes:/app/notes \
  fluidnotions/youtube-study-buddy:latest
```

Or use Docker Compose:

```bash
# Create .env file with your API key
echo "CLAUDE_API_KEY=your_key_here" > .env

# Run with Docker Compose
docker compose up -d
```

**That's it!** Open http://localhost:8501 in your browser.

### CLI Usage (For Automation)

```bash
# Install package
uv sync

# Process URLs directly
uv run youtube-study-buddy "https://youtube.com/watch?v=xyz"

# Process from file
uv run youtube-study-buddy --file playlist-urls.txt

# With subject organization
uv run youtube-study-buddy --subject "Machine Learning" url1 url2

# Full help
uv run youtube-study-buddy --help
```

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

## 🛠️ Alternative Ways to Run

Don't want to use Docker? See **[Alternative Setup Methods](docs/technical/alternative-setup.md)** for:
- Running from source with Python/UV
- CLI usage and command-line flags
- Development setup for contributors
- Manual installation instructions

---

## 📜 License & Contributing

MIT License - Free to use, modify, and distribute.

Contributions welcome! Open an issue or pull request on GitHub.