# YT Study Buddy

Watching educational YouTube videos but struggling to retain the information? Manually taking notes slows you down, and you lose track of connections between concepts across different videos. **YT Study Buddy** transforms any YouTube video into structured study notes with intelligent cross-referencing that builds your personal knowledge graph over time.

## 💰 Why This Tool Exists (Free vs Paid Alternatives)

Most AI-powered YouTube note-taking solutions in 2025 require expensive subscriptions or have significant limitations:

**Paid Solutions ($10-50+/month):**
- **NoteGPT** - Comprehensive AI learning assistant (premium features require subscription)
- **Notta** - Professional transcription service (98.86% accuracy, limited free tier)
- **Eightify** - AI video summarizer (subscription for unlimited summaries)
- **Maestra** - Multi-language support (subscription for full feature access)

**Free Alternatives (Limited Features):**
- **Basic transcript generators** - No AI analysis, just raw text extraction
- **Tactiq** - Chrome extension transcription (no study note formatting)
- **YouTube auto-captions** - Inaccurate, no structure or cross-referencing
- **Manual note-taking** - Time-consuming, no automation or connections

**YT Study Buddy is completely free** and provides AI-powered study note generation with intelligent cross-referencing and Obsidian integration. Perfect for students, lifelong learners, and professionals who want to build a connected knowledge base without subscription costs.

Unlike simple transcript extractors, YT Study Buddy creates **structured study materials** with cross-references that grow smarter with each video you process, building an interconnected web of knowledge over time.

## Key Features
- **AI-Powered Study Notes** – Transforms raw transcripts into structured learning materials with defined sections
- **Intelligent Cross-Referencing** – Automatically connects related concepts across your entire note collection
- **Obsidian Integration** – Creates `[[wiki-style]]` links for seamless knowledge graph building
- **Subject Organization** – Organize notes by topic with global or subject-specific cross-referencing
- **Batch Processing** – Process multiple videos efficiently with URL file support
- **Knowledge Graph Growth** – Each new video strengthens connections in your existing knowledge base

## Why It Matters

For students, researchers, and lifelong learners, this solves the pain of information overload and disconnected knowledge. Instead of isolated notes that sit unused, you get **interconnected study materials** that reveal patterns, reinforce learning, and help you build genuine understanding across topics.

## Technical

YT Study Buddy integrates with the Claude AI API for intelligent note generation and uses fuzzy matching algorithms to identify conceptual connections across your knowledge base. Built for Python 3.10+ and designed to work seamlessly with Obsidian's linking system.

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

3. **Configure API Key**

   Create a `.env` file in this directory:
   ```
   CLAUDE_API_KEY=your_api_key_here
   ```

   Or set environment variable:
   ```bash
   export CLAUDE_API_KEY=your_api_key_here
   ```

## Usage

### Subject-Based Processing
```bash
# Process single video for a subject (global cross-referencing)
python main.py --subject "Machine Learning" "https://youtube.com/watch?v=xyz"

# Batch process URLs for a subject (global cross-referencing)
python main.py --subject "Python Programming" --batch

# Subject-only cross-referencing (no global connections)
python main.py --subject "AI Ethics" --subject-only --batch
```

### Global Processing (No Subject Organization)
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

### Command Line Examples
```bash
# Custom URL file
python main.py --subject "Data Science" --batch --file my_videos.txt

# Interactive mode
python main.py

# Help
python main.py --help
```

## URLs File Format

Create a `urls.txt` file with one YouTube URL per line:
```
https://www.youtube.com/watch?v=abc123
https://youtu.be/def456
# Comments start with # and are ignored

https://www.youtube.com/watch?v=ghi789
```

### Generated Notes Example
Files are saved as `Study notes/Subject Name/Video_Title.md`. Here's an example of generated output:

```markdown
# Attention Is All You Need - Transformers Explained

[YouTube Video](https://www.youtube.com/watch?v=kCc8FmEb1nY)

---

## Core Concepts
- **Self-attention mechanism** replaces recurrent and convolutional layers entirely
- **Multi-head attention** allows model to attend to information from different representation subspaces
- **Positional encoding** provides sequence order information without recurrence

## Key Points
1. **Encoder-Decoder Architecture**: Stack of 6 identical layers in both encoder and decoder
2. **Attention Function**: Mapping query and key-value pairs to output weights
3. **Scaled Dot-Product Attention**: Attention(Q,K,V) = softmax(QK^T/√dk)V

## Connections & Relationships
This connects to your [[Neural Machine Translation]] and [[BERT Architecture]] notes - all use attention mechanisms but Transformers eliminate the need for RNNs entirely.

## Questions for Further Study
- How does the computational complexity of O(n²d) for self-attention compare to O(nd²) for recurrent layers?
- What are the trade-offs between multi-head attention and single attention mechanisms?

## Action Items & Practice
1. Implement basic self-attention mechanism from scratch
2. Compare Transformer performance vs LSTM on sequence tasks
3. Experiment with different numbers of attention heads
```

## Recommended Workflow

YT Study Buddy is designed for this efficient learning process:

1. **Build Your Video List** - Collect interesting YouTube URLs in `urls.txt` as you discover them
2. **Generate All Notes First** - Run batch processing to create structured notes for all videos at once
3. **Copy to Infinite Canvas** - Import generated notes into Miro, Concepts, or similar stylus-friendly tools
4. **Watch with Notes Available** - Use the summary notes for highlighting, adding thoughts, and active learning

Perfect for stylus-based mind mapping and visual learning workflows!

## Cross-Referencing

The tool automatically:
- Analyzes existing notes for key concepts
- Identifies related topics in new videos
- Adds connection notes in the "Connections & Relationships" section
- Builds a growing knowledge web across all your study materials

## Output Structure

Notes are saved in `study_notes_output/` with:
- **Filename**: Based on actual video title
- **Header**: Video title + YouTube link
- **Sections**: Core Concepts, Key Points, Connections & Relationships, Questions for Further Study, Action Items & Practice
- **Cross-references**: Automatic `[[wiki-style]]` links to related notes when concepts overlap

## Requirements

- Python 3.10+
- Claude API key
- Internet connection for YouTube and Claude API access