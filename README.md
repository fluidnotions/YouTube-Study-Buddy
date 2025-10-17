# YouTube Study Buddy

Learning from educational YouTube videos and want to maximize retention and build meaningful connections? **YouTube Study Buddy** transforms any YouTube video into structured study notes with intelligent cross-referencing that builds your personal knowledge graph over time, turning scattered video content into an interconnected learning system.

## 🧠 The Science: Active Learning vs Passive Watching

**Traditional passive note-taking** often leads to the "illusion of competence" – where learners feel they understand content simply because they've transcribed it. YouTube Study Buddy implements research-backed learning principles:

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

**YouTube Study Buddy is completely free** and provides AI-powered study note generation with intelligent cross-referencing and Obsidian integration. Perfect for students, lifelong learners, and professionals who want to build a connected knowledge base without subscription costs.

Unlike simple transcript extractors, YouTube Study Buddy creates **structured study materials** with cross-references that grow smarter with each video you process, building an interconnected web of knowledge over time.

## ✨ Key Features

### Core Learning Features
- **AI-Powered Study Notes** – Transforms raw transcripts into structured learning materials with defined sections
- **Learning Assessments** – Generates 4 question types including unique "One-Up Challenges" that ask you to improve upon what you learned
- **Auto-Categorization** – ML-powered subject detection organizes your knowledge base automatically
- **Batch Processing** – Process multiple videos efficiently with URL file support
- **Markdown Output** – Compatible with Obsidian, Notion, and other markdown-based tools

### Intelligent Cross-Referencing (RAG)
- **Semantic Understanding** – Goes beyond keyword matching to find conceptually related content
- **Smart Connections** – Automatically links "neural networks" with "deep learning" and similar concepts
- **Knowledge Graph Growth** – Each new video strengthens connections in your existing knowledge base
- **Obsidian Integration** – Creates `[[wiki-style]]` links for seamless knowledge graph building
- **Subject Organization** – Organize notes by topic with global or subject-specific cross-referencing

### What Makes RAG Special?

Traditional keyword matching misses conceptual relationships. YouTube Study Buddy uses **RAG (Retrieval-Augmented Generation)** with semantic embeddings to understand meaning, not just match words:

**Before (Keyword Matching):**
- "machine learning" only finds exact text matches
- Misses related concepts like "neural networks" or "deep learning"
- Limited relevance ranking

**After (Semantic RAG):**
- Understands that "gradient descent" relates to "backpropagation"
- Finds conceptual connections across your entire knowledge base
- Relevance-ranked results prioritize the most meaningful links

## 🎯 Why It Matters

For students, researchers, and lifelong learners, this solves the pain of information overload and disconnected knowledge. Instead of isolated notes that sit unused, you get **interconnected study materials** that reveal patterns, reinforce learning, and help you build genuine understanding across topics.

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

See [Docker Setup Guide](docs/DOCKER_SETUP.md) for configuration options, troubleshooting, and RAG features.

### Local Installation
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API key
echo "CLAUDE_API_KEY=your_key_here" > .env

# 3. Run Streamlit interface
streamlit run streamlit_app.py

# Or use CLI
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 💡 Usage Examples

### Web Interface (Streamlit)
The easiest way to use YouTube Study Buddy:
1. Start the app: `streamlit run streamlit_app.py`
2. Paste YouTube URL
3. Select subject (optional)
4. Click "Generate Notes"
5. Download markdown or view in browser

### Command Line Interface

**Single Video:**
```bash
# With subject organization
python main.py --subject "Machine Learning" "https://youtube.com/watch?v=xyz"

# Without subject (global knowledge base)
python main.py "https://youtube.com/watch?v=xyz"
```

**Batch Processing:**
```bash
# Create urls.txt with one URL per line
echo "https://youtube.com/watch?v=abc123" > urls.txt
echo "https://youtube.com/watch?v=def456" >> urls.txt

# Process all URLs
python main.py --batch
```

**Subject-Specific Organization:**
```bash
# Cross-reference within subject only
python main.py --subject "AI Ethics" --subject-only --batch

# Cross-reference globally (default)
python main.py --subject "Python Programming" --batch
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
- Links ranked by relevance using RAG similarity scores

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

## 🤝 Contributing

Contributions welcome! This project is actively developed and open to improvements in:
- Learning assessment quality
- Cross-referencing algorithms
- Additional AI model support
- UI/UX enhancements

## 📝 License

MIT License - Free to use, modify, and distribute.

## 🌟 Support

If you find this tool helpful:
- ⭐ Star the repository
- 🐛 Report bugs via GitHub Issues
- 💡 Suggest features or improvements
- 📢 Share with fellow learners

---

**Built for learners, by learners.** Transform your YouTube learning from passive watching to active knowledge building.
