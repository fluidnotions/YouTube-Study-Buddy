# RAG Quickstart Guide

Get RAG-powered semantic cross-referencing running in 5 minutes!

## What You'll Get

- Semantic understanding of your study notes
- Automatic cross-references between related concepts
- [[Obsidian-style wiki links]] in your notes
- Better learning connections

## Prerequisites

- Docker and Docker Compose installed
- Claude API key
- 2GB RAM available
- 5 minutes of your time

## Quick Setup (Docker)

### Step 1: Clone and Configure (1 minute)

```bash
# Navigate to your project directory
cd youtube-study-buddy

# Create environment file
cp .env.example .env

# Edit .env and add your API key
nano .env
# Set: CLAUDE_API_KEY=your-key-here
# RAG_ENABLED=true (already set by default)
```

### Step 2: Start the Container (2 minutes)

```bash
# Start services
docker-compose up -d

# Wait for first-time model download (~80MB)
# This happens automatically on first run

# Check logs to see progress
docker logs -f youtube-study-buddy
```

**What's happening:**
- Container starts
- Sentence-transformer model downloads (~80MB)
- ChromaDB vector database initializes
- Application is ready!

### Step 3: Verify RAG is Working (30 seconds)

```bash
# Run health check
./scripts/check_rag_health.sh

# Expected output:
# ✓ Container is running
# ✓ RAG is enabled
# ✓ Vector store is operational
# ✓ Embedding service is working
# ✓ All systems go!
```

### Step 4: Process Your First Video (1 minute)

Open your browser to `http://localhost:8501` and:

1. Paste a YouTube URL (e.g., a short educational video)
2. Select a subject (e.g., "AI")
3. Click "Process Video"
4. Wait for processing to complete

**What's happening:**
- Video transcript is fetched
- Study notes are generated with Claude
- Notes are chunked into sections
- Embeddings are generated (happens in background)
- Notes are indexed for semantic search
- Cross-references are added automatically!

### Step 5: Check Your Note (30 seconds)

```bash
# Navigate to notes directory
cd notes/AI/

# Open the generated note
cat "Your Video Title.md"
```

**Look for:**
- `## Related Concepts` sections
- `[[Wiki-style links]]` to other notes
- Semantically related connections (not just keyword matches!)

## Quick Setup (Local, No Docker)

### Step 1: Install Dependencies (1 minute)

```bash
# Using UV (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### Step 2: Configure Environment (30 seconds)

```bash
# Create .env file
cat > .env << EOF
CLAUDE_API_KEY=your-key-here
RAG_ENABLED=true
RAG_MODEL=all-mpnet-base-v2
RAG_SIMILARITY_THRESHOLD=0.3
RAG_MAX_RESULTS=5
EOF
```

### Step 3: Run the App (30 seconds)

```bash
# Start Streamlit interface
uv run streamlit run streamlit_app.py

# Or use CLI
uv run yt-study-buddy --url "youtube-url" --subject "AI"
```

### Step 4: Verify and Test (same as Docker steps 3-5)

## What's Next?

### Migrate Existing Notes

If you have notes from before RAG:

```bash
# Docker
docker exec youtube-study-buddy python scripts/migrate_notes_to_rag.py --notes-dir /app/notes

# Local
uv run python scripts/migrate_notes_to_rag.py
```

This will index all your existing notes for semantic search!

### Explore Your Knowledge Graph

Use the interactive query tool:

```bash
# Docker
docker exec -it youtube-study-buddy python scripts/query_rag_interactive.py --notes-dir /app/notes

# Local
uv run python scripts/query_rag_interactive.py
```

Try queries like:
- "How do neural networks learn?"
- "What is backpropagation?"
- "subject:AI optimization"

### Customize Configuration

Edit `.env` to adjust RAG behavior:

```bash
# Be more selective with links (fewer, more relevant)
RAG_SIMILARITY_THRESHOLD=0.4

# Get more cross-references per section
RAG_MAX_RESULTS=10

# Use faster, smaller model (less memory)
RAG_MODEL=all-MiniLM-L6-v2
```

Then restart:
```bash
docker-compose restart
```

## Common Issues

### Model Download Takes Forever

**Problem:** First run is very slow

**Solution:**
- Model downloads ~80MB on first use
- Check your internet connection
- Or pre-download: `docker exec youtube-study-buddy python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"`

### No Cross-References in Notes

**Problem:** Notes don't have [[links]]

**Solutions:**
1. Check RAG is enabled: `docker exec youtube-study-buddy printenv RAG_ENABLED`
2. Check logs: `docker logs youtube-study-buddy | grep RAG`
3. Run health check: `./scripts/check_rag_health.sh`
4. Index might be empty (process more videos or migrate existing notes)

### Out of Memory

**Problem:** Container crashes with "Killed"

**Solutions:**
1. Increase Docker memory to 3GB:
   ```yaml
   # docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 3G
   ```

2. Or use smaller model:
   ```bash
   # .env
   RAG_MODEL=all-MiniLM-L6-v2
   RAG_BATCH_SIZE=16
   ```

## Understanding Your Results

### What RAG Links Look Like

**In your note:**
```markdown
## Neural Network Basics

Neural networks consist of layers of interconnected nodes...

**Related Concepts:**
- [[Deep Learning Fundamentals#Neural Architecture]] (0.85)
- [[Backpropagation Algorithm#Gradient Descent]] (0.78)
- [[Activation Functions#ReLU and Sigmoid]] (0.72)
```

**What the numbers mean:**
- 0.8-1.0: Very strongly related
- 0.6-0.8: Related
- 0.4-0.6: Somewhat related
- 0.3-0.4: Loosely related (your threshold)

### Before vs After RAG

**Before RAG (keyword matching):**
- Found: 2-3 links per note
- Based on: Exact word matches
- Misses: Conceptually related content

**After RAG (semantic understanding):**
- Found: 5-8 links per note (average)
- Based on: Meaning and context
- Discovers: Hidden connections between concepts

**Example:**
- Query: "neural networks"
- Before: Only finds notes with "neural networks" in text
- After: Also finds "deep learning", "backpropagation", "gradient descent", "activation functions"

## 5-Minute Checklist

Use this checklist to ensure everything is working:

- [ ] Docker installed and running
- [ ] `.env` file created with API key
- [ ] `docker-compose up -d` successful
- [ ] Model downloaded (check logs)
- [ ] Health check passes
- [ ] Processed at least one video
- [ ] See cross-references in generated note
- [ ] Links work in Obsidian (if using)

**All checked?** You're ready to go! Your study notes now have semantic superpowers.

## Next Steps

### Learn More

- **[RAG User Guide](RAG_USER_GUIDE.md)** - Comprehensive user documentation
- **[RAG Developer Guide](RAG_DEVELOPER_GUIDE.md)** - Architecture and development
- **[RAG API Reference](RAG_API.md)** - Complete API documentation

### Optimize Your Setup

1. **Adjust similarity threshold** based on your needs (more/fewer links)
2. **Migrate existing notes** to get cross-references for old content
3. **Evaluate quality** with the evaluation script
4. **Backup your vector database** regularly

### Advanced Features

- **Interactive queries**: Test RAG without processing videos
- **Quality evaluation**: Compare RAG vs keyword matching
- **Vector store maintenance**: Clean, rebuild, optimize
- **Custom configuration**: Fine-tune for your use case

## Getting Help

**Something not working?**

1. Check logs: `docker logs youtube-study-buddy`
2. Run health check: `./scripts/check_rag_health.sh --verbose`
3. Review this guide: Most issues are covered here
4. Check [RAG User Guide](RAG_USER_GUIDE.md) troubleshooting section

**Still stuck?**

- Include output of health check
- Include relevant log snippets
- Describe what you expected vs what happened
- Mention your configuration (.env settings)

## Tips for Best Results

### Content Tips

1. **Process quality videos**: Better transcripts = better notes = better links
2. **Use consistent subjects**: Helps RAG find connections within domains
3. **Process related videos**: More content = more connections
4. **Review generated links**: Adjust threshold if too many/few links

### Configuration Tips

1. **Start with defaults**: Don't tweak settings until you see results
2. **Adjust threshold gradually**: Change by 0.1 increments
3. **Monitor memory usage**: Increase if you see crashes
4. **Use faster model for testing**: Switch to better model later

### Workflow Tips

1. **Process videos in batches**: RAG works better with more indexed content
2. **Migrate old notes early**: Get semantic search on existing content
3. **Use query tool to explore**: Discover connections manually
4. **Backup your data**: Use `./scripts/manage_rag_volumes.sh backup`

## Success Metrics

After processing 10-20 videos, you should see:

- **5-8 cross-references per note** (average)
- **80%+ relevance** (most links make sense)
- **New conceptual connections** you didn't notice before
- **Query time < 100ms** (fast semantic search)
- **No impact on note generation time** (RAG runs in background)

If you're not seeing these results, review the troubleshooting section or check the [User Guide](RAG_USER_GUIDE.md).

---

## Congratulations!

You now have RAG-powered semantic cross-referencing working!

Your study notes will automatically discover connections between concepts, helping you build a comprehensive knowledge graph.

**Happy learning!**

---

**Quick Links:**
- [Main README](../README.md) - Docker setup and general info
- [RAG User Guide](RAG_USER_GUIDE.md) - Full user documentation
- [RAG Developer Guide](RAG_DEVELOPER_GUIDE.md) - Technical details
- [RAG API Reference](RAG_API.md) - API documentation

**Last Updated**: October 17, 2025
**Version**: 1.0.0 (Initial RAG Implementation)
