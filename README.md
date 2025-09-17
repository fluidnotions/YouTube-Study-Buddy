# YT Study Buddy

Learning from educational YouTube videos and want to maximize retention and build meaningful connections? **YT Study Buddy** transforms any YouTube video into structured study notes with intelligent cross-referencing that builds your personal knowledge graph over time, turning scattered video content into an interconnected learning system.

## 🧠 The Science: Active Learning vs Passive Watching

**Traditional passive note-taking** often leads to the "illusion of competence" – where learners feel they understand content simply because they've transcribed it. YT Study Buddy implements research-backed learning principles:

- **Dual Coding Theory** – Combines text with visual spatial organization for stronger memory formation
- **Generation Effect** – Assessment questions force active answer generation, improving retention
- **Desirable Difficulties** – "One-up" challenges introduce productive struggle beyond the presented material
- **Elaborative Interrogation** – Gap analysis questions reveal what your brain filtered out
- **Spaced Retrieval Practice** – Separation of note generation from video watching enables spaced review

**Result:** Instead of passive consumption, you get an active learning system with notes AND assessment questions that test understanding beyond surface-level recall.

## 💰 Free vs Paid Alternatives

**Paid ($10-50+/month):** NoteGPT, Notta, Eightify, Maestra – all require subscriptions for full features

**Free (Limited):** Basic transcripts, no AI analysis, no cross-referencing, no assessments

**YT Study Buddy:** Completely free with AI-powered notes, learning assessments, auto-categorization, and knowledge graph building. No subscriptions, no limits.

## Key Features
- **AI-Powered Study Notes** – Transforms raw transcripts into structured learning materials with defined sections
- **Learning Assessments** – Generates 4 question types including unique "One-Up Challenges" that ask you to improve upon what you learned
- **Smart Auto-Categorization** – When no subject specified, ML model detects best-fit from existing folders or creates new ones
- **Intelligent Cross-Referencing** – Same ML model finds semantically related concepts across your entire note collection
- **Obsidian Integration** – Creates `[[wiki-style]]` links for seamless knowledge graph building
- **Subject Override** – Use `--subject` flag to bypass auto-categorization when you know where content belongs
- **Batch Processing** – Process multiple videos efficiently with URL file support
- **Knowledge Graph Growth** – Each new video strengthens connections in your existing knowledge base

## Technical Stack

- **Python 3.13+** with Poetry package management
- **Claude AI API** – Generates notes and assessment questions (remote)
- **Sentence Transformers** – One local ML model powers both auto-categorization AND semantic cross-referencing
- **Graceful Fallbacks** – Works without ML models (manual subject + keyword matching)
- **Obsidian-compatible** Markdown with wiki-style linking

## Setup

1. **Install Dependencies**

   **Option 1: Poetry (Recommended)**
   ```bash
   pip install poetry
   poetry install
   ```

   **Option 2: pip**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get Claude API Key**
   - Visit [https://console.anthropic.com/](https://console.anthropic.com/)
   - Create an account and generate an API key

3. **Configure API Key & Models**

   Create a `.env` file in this directory:
   ```
   CLAUDE_API_KEY=your_api_key_here

   # ML Model Configuration (optional - defaults shown)
   SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
   ```

   Or set environment variables:
   ```bash
   export CLAUDE_API_KEY=your_api_key_here
   export SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
   ```

   **Model Options:**
   - `all-MiniLM-L6-v2` - Fast, good quality (default)
   - `all-mpnet-base-v2` - Higher quality, slower
   - `all-distilroberta-v1` - Alternative architecture

## Usage

### Using Poetry (Recommended)
```bash
# Manual subject (bypasses auto-categorization)
yt-study-buddy --subject "Machine Learning" "https://youtube.com/watch?v=xyz"

# Auto-categorization (ML model picks best subject folder)
yt-study-buddy "https://youtube.com/watch?v=xyz"

# Batch with auto-categorization
yt-study-buddy --batch

# Subject-only cross-referencing (no global connections)
yt-study-buddy --subject "AI Ethics" --subject-only --batch
```

### Using Python Directly
```bash
# Single video (saved to base Study notes/ folder)
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Batch processing
python main.py --batch
```

### Command Line Flags

| Flag | Description |
|------|-------------|
| `--subject <name>` | Organize notes by subject (creates `Study notes/<subject>/` folder) |
| `--subject-only` | **Used with --subject**: Cross-reference only within that subject (default: global) |
| `--batch` | Process multiple URLs from file |
| `--file <filename>` | Use custom URL file (default: urls.txt) |

### Web Interface (Easy Setup)
```bash
# Run the Streamlit web interface
streamlit run streamlit_app.py
```
Then open your browser to **http://localhost:8501** for a user-friendly interface with drag & drop URL input.

### Command Line Examples
```bash
# Custom URL file (Poetry)
yt-study-buddy --subject "Data Science" --batch --file my_videos.txt

# Custom URL file (Python)
python main.py --subject "Data Science" --batch --file my_videos.txt

# Help
yt-study-buddy --help
```

## URLs File Format

Create a `urls.txt` file with one YouTube URL per line:
```
https://www.youtube.com/watch?v=abc123
https://youtu.be/def456
# Comments start with # and are ignored

https://www.youtube.com/watch?v=ghi789
```

### Extracting URLs from Playlists

Instead of manually copying URLs, you can extract them from playlists using `yt-dlp`:

```bash
# Install yt-dlp
pip install yt-dlp

# Extract all video URLs from a playlist and save to urls.txt
yt-dlp --get-url --flat-playlist "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID" > urls.txt

# Or get URLs with titles for reference
yt-dlp --get-title --get-url --flat-playlist "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
```

This eliminates the tedious manual process of copying URLs from your playlists!

### Generated Output Examples

**Notes File:** `Transformers_Explained.md`
```markdown
# Attention Is All You Need - Transformers Explained
[YouTube Video](https://www.youtube.com/watch?v=kCc8FmEb1nY)

## Core Concepts
- **Self-attention mechanism** replaces recurrent layers entirely
- **Multi-head attention** allows attending to different representation subspaces
- **Positional encoding** provides sequence order information

## Connections & Relationships
This connects to your [[Neural Machine Translation]] and [[BERT Architecture]] notes...
```

**Assessment File:** `Transformers_Explained_Assessment.md`
```markdown
# Learning Assessment

## Gap Analysis
Q: What complexity details were mentioned but not captured in notes?
Your Answer: [Write here]

## Application
Q: How would you implement this for real-time inference on mobile?
Your Answer: [Write here]

## One-Up Challenge
Q: The video shows O(n²) complexity. How would you optimize for 100k+ tokens?
Your Answer: [Write here]

## Synthesis
Q: How does this relate to graph neural networks?
Your Answer: [Write here]

[Model answers at bottom of file for self-checking]
```

## Workflow

1. **Curate** – Add videos to YouTube playlists, extract URLs with `yt-dlp` → `urls.txt`
2. **Generate** – Batch process all videos → notes + assessments in organized folders
3. **Canvas** – Import into Miro/Concepts for spatial learning with stylus
4. **Learn Actively** – Review notes, attempt assessments, make visual connections

## Assessment System

### Four Types of Questions Generated:

1. **Gap Analysis** – "What important details were in the video but NOT in your notes?" (reveals blind spots)
2. **Application** – "How would you implement this in a real project?" (tests practical understanding)
3. **One-Up Challenges** – "How could you improve/optimize what was shown?" (promotes innovation thinking)
4. **Synthesis** – "How does this connect to other concepts?" (builds knowledge connections)

### What Makes One-Up Challenges Special:

Instead of asking "What did you learn?", we ask **"How would you make it better?"** Examples:
- Video shows basic algorithm → "How would you optimize this for distributed systems?"
- Tutorial uses standard approach → "How would you enhance this with modern ML techniques?"
- Explains current limitation → "Design a solution that overcomes this constraint"

This transforms learners from **knowledge consumers into knowledge creators**.

### Where Files Are Saved

```
Study notes/
├── Machine Learning/
│   ├── Video_Title.md           # Notes
│   └── Video_Title_Assessment.md # Questions
```

Assessments are **active learning checkpoints**

## Requirements

- Python 3.13+ with Poetry
- Claude API key (from console.anthropic.com)
- Optional: Sentence transformer models (auto-downloads on first use)