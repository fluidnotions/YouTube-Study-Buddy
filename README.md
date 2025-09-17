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
- **Learning Assessments** – Generates 4 question types including unique "One-Up Challenges" that ask you to improve upon what you learned
- **Auto-Categorization** – ML-powered subject detection organizes your knowledge base automatically
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
# Process single video for a subject (global cross-referencing)
yt-study-buddy --subject "Machine Learning" "https://youtube.com/watch?v=xyz"

# Batch process URLs for a subject (global cross-referencing)
yt-study-buddy --subject "Python Programming" --batch

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

1. **Curate Your Learning Content** - Add interesting videos to YouTube playlists, then extract URLs using `yt-dlp` to build your `urls.txt` file
2. **Generate All Notes First** - Run batch processing to create structured notes for all videos at once
3. **Copy to Infinite Canvas** - Import generated notes into Miro, Concepts, or similar stylus-friendly tools
4. **Transform Notes into Active Learning Artifacts** – Pre-written, structured notes free you from transcription and let you focus on highlighting, annotating, and visually connecting concepts. By clustering related ideas, drawing links, and layering in your own commentary, you move from passive reading to active engagement. This approach reflects principles of active learning and dual coding—combining text with spatial and visual relationships—which is shown to enhance understanding and retention.

Perfect for stylus-based mind mapping and visual learning workflows!

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

### Assessment Storage & Workflow

**Where assessments are stored:**
- Assessment files are saved **alongside your notes** in the same subject folder
- File naming: `Video_Title_Assessment.md` (companion to `Video_Title.md` notes)
- Example structure:
  ```
  Study notes/
  ├── Machine Learning/
  │   ├── Transformer_Architecture.md          (notes)
  │   ├── Transformer_Architecture_Assessment.md  (questions)
  │   ├── Neural_Networks_Basics.md           (notes)
  │   └── Neural_Networks_Basics_Assessment.md   (questions)
  ```

**Intended workflow:**
1. Generate notes and assessments for multiple videos
2. Import both into your canvas tool (Miro, Concepts, etc.)
3. Review notes first to refresh understanding
4. Attempt assessment questions without looking at notes
5. Check your answers against the model answers at the bottom
6. Use the feedback to identify areas needing deeper study

This separation ensures assessments serve as **active learning checkpoints** rather than passive reference material.

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