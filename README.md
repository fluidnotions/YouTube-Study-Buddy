# RAG Cross-Reference Enhancement - Worktree

This worktree is dedicated to researching and implementing RAG (Retrieval-Augmented Generation) for improved cross-referencing in YouTube Study Buddy.

## Quick Start

```bash
cd /home/justin/Documents/dev/python/PycharmProjects/rag-worktree

# Read the detailed task
cat AGENT_TASK.md

# Install dependencies
uv sync

# Start working on the research phase
```

## What's Here

- **AGENT_TASK.md**: Comprehensive task document with objectives, deliverables, and success criteria
- **Branch**: `feature/rag-cross-reference`
- **Timeline**: 8-11 hours of focused work

## Why RAG?

The current cross-reference system uses simple keyword matching, which:
- Misses semantic relationships
- Can't rank relevance
- Doesn't scale well
- Has limited recall

RAG will enable:
- Semantic understanding of concepts
- Relevance-ranked connections
- Fast similarity search
- Better discovery of related content

## Deliverables

1. **docs/rag-research.md** - Vector DB comparison and recommendations
2. **docs/rag-design.md** - Architecture and data flow design
3. **scripts/rag_poc.py** - Working proof of concept
4. **docs/rag-integration.md** - Implementation roadmap

## Workflow

This is a feature branch workflow:
1. Work is done in this worktree
2. Commits go to `feature/rag-cross-reference`
3. When complete, merge to `main` via PR
4. Worktree can be removed after merge

## Cleanup

When done:
```bash
cd /home/justin/Documents/dev/python/PycharmProjects/ytstudybuddy
git worktree remove ../rag-worktree
git branch -d feature/rag-cross-reference
```
