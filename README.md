# YouTube Study Buddy

Convert YouTube videos into comprehensive study notes with automatic cross-referencing between related topics. Build a connected knowledge base that grows smarter with each video you process.

## 🧠 The Science: Active Learning vs Passive Watching

**Traditional passive note-taking** often leads to the "illusion of competence" – where learners feel they understand content simply because they've transcribed it. YouTube Study Buddy implements research-backed learning principles:

- **Dual Coding Theory** – Combines text with visual spatial organization for stronger memory formation
- **Generation Effect** – Assessment questions force active answer generation, improving retention
- **Desirable Difficulties** – "One-up" challenges introduce productive struggle beyond the presented material
- **Elaborative Interrogation** – Gap analysis questions reveal what your brain filtered out
- **Spaced Retrieval Practice** – Separation of note generation from video watching enables spaced review

**Result:** Instead of passive consumption, you get an active learning system with notes AND assessment questions that test understanding beyond surface-level recall.

## 💰 Why This Tool Exists (Free vs Paid Alternatives)

Most AI-powered YouTube note-taking solutions require expensive subscriptions ($10-50+/month) like NoteGPT, Notta, Eightify, and Maestra. Free alternatives offer limited features or just basic transcript extraction with no analysis.

**YouTube Study Buddy is completely free** and provides AI-powered study note generation with intelligent cross-referencing and Obsidian integration. Perfect for students, lifelong learners, and professionals who want to build a connected knowledge base without subscription costs.

## Features

- **Automatic Transcript Extraction** from YouTube videos
- **AI-Generated Study Notes** using Claude API with structured sections
- **Learning Assessments** – Generates 4 question types including unique "One-Up Challenges"
- **Semantic Cross-Referencing** – Finds conceptually related content across your knowledge base
- **Auto-Categorization** – ML-powered subject detection organizes notes automatically
- **Obsidian Auto-Linking** – Automatically creates `[[wiki-style]]` links between related notes
- **PDF Export** – Generate formatted PDF study materials from your notes
- **Batch Processing** – Process multiple videos efficiently with URL file support
- **Knowledge Graph Growth** – Each new video strengthens connections in your existing notes

## 🚀 Quick Start

### Docker (Recommended)
```bash
# 1. Clone and configure
git clone https://github.com/fluidnotions/YouTube-Study-Buddy.git
cd YouTube-Study-Buddy
cp .env.example .env
# Edit .env and add your CLAUDE_API_KEY

# 2. Start services
docker-compose up -d

# 3. Open browser
open http://localhost:8501
```

See [Docker Setup Guide](docs/DOCKER_SETUP.md) for configuration options, troubleshooting, and advanced features.

### Local Installation
```bash
# 1. Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Configure API key
echo "CLAUDE_API_KEY=your_key_here" > .env

# 4. Run Streamlit interface
uv run streamlit run streamlit_app.py

# Or use CLI
uv run python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 💡 Usage

### Web Interface (Streamlit)
1. Start the app: `uv run streamlit run streamlit_app.py`
2. Paste YouTube URL
3. Select subject (optional)
4. Click "Generate Notes"
5. Notes automatically saved to `notes/` directory

### Command Line Interface

**Single Video:**
```bash
# With subject organization
uv run python main.py --subject "Machine Learning" "https://youtube.com/watch?v=xyz"

# Without subject (global knowledge base)
uv run python main.py "https://youtube.com/watch?v=xyz"
```

**Batch Processing:**
```bash
# Create urls.txt with one URL per line
echo "https://youtube.com/watch?v=abc123" > urls.txt
echo "https://youtube.com/watch?v=def456" >> urls.txt

# Process all URLs
uv run python main.py --batch
```

**Subject-Specific Cross-Referencing:**
```bash
# Cross-reference within subject only
uv run python main.py --subject "AI Ethics" --subject-only --batch

# Cross-reference globally (default)
uv run python main.py --subject "Python Programming" --batch
```

## 📚 Example Output

Each generated note includes:

### 1. Structured Content
- Main concepts and key ideas
- Definitions and terminology
- Examples and applications
- Summary and takeaways

### 2. Learning Assessments
- **Comprehension Questions** - Test basic understanding
- **Application Questions** - Apply concepts to new scenarios
- **Gap Analysis** - Identify what wasn't explicitly covered
- **One-Up Challenges** - Extend beyond the material

### 3. Intelligent Cross-References
- `[[Related Topic 1]]` - Semantically similar content
- `[[Related Topic 2]]` - Connected concepts from other notes
- Links ranked by relevance across your knowledge base

## 🛠️ Technical Details

Built with:
- **AI:** Claude API (Anthropic) for intelligent note generation
- **Cross-Referencing:** Semantic embeddings with ChromaDB vector store
- **ML Models:** Sentence transformers for concept similarity
- **Transcript:** youtube-transcript-api with yt-dlp fallback
- **Interface:** Streamlit web UI + CLI
- **Integration:** Obsidian-compatible markdown output

Python 3.10+ required.

## 📖 Documentation

- [Docker Setup Guide](docs/DOCKER_SETUP.md) - Complete Docker configuration and troubleshooting
- [RAG Design](docs/rag-design.md) - How semantic cross-referencing works
- [RAG Integration](docs/rag-integration.md) - Migration guide and technical details
- [Retry Guide](docs/RETRY_GUIDE.md) - Error handling and retry system

---

**Built for learners, by learners.** Transform your YouTube learning from passive watching to active knowledge building.
