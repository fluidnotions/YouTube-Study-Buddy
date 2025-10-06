 @~/.claude/claude.md
# CLAUDE.md - YouTubeStudyBuddy Project Instructions

## Primary Reference: Home Directory CLAUDE.md

**ALWAYS refer to `/home/justin/Documents/dev/python/PycharmProjects/CLAUDE.md` for:**
- Repository-wide architecture and project structure
- Common development commands across all projects
- UV-based workflow and dependency management
- Testing approaches and environment requirements
- Docker support and configuration patterns

This project is part of the larger PyCharm Projects directory and should follow all conventions defined in the home directory CLAUDE.md.

## Project-Specific Context

This is the **ytstudybuddy** project:
- **Purpose**: YouTube study notes generator with AI integration
- **Core Flow**: YouTube URL � transcript extraction � AI-powered study notes + assessments
- **Key Components**: Claude API integration, sentence transformers for ML, auto-categorization
- **Output**: Markdown files with wiki-style links for Obsidian compatibility
- **Testing**: Uses pytest with custom test discovery in `run_tests.py`
- **Python**: 3.13
- **Package Manager**: UV (as per home directory standards)

## CLI Usage

```bash
uv run yt-study-buddy --help           # Main CLI
uv run streamlit run streamlit_app.py  # Web interface
uv run pytest                          # Run tests
```