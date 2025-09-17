# YouTube to Study Notes

Convert YouTube videos into comprehensive study notes with automatic cross-referencing between related topics.

## Features

- **Automatic Transcript Extraction** from YouTube videos
- **AI-Generated Study Notes** using Claude API with structured sections
- **Cross-Reference System** that connects related concepts across your note collection
- **Obsidian Auto-Linking** - Automatically creates `[[links]]` between related notes using fuzzy matching
- **Batch Processing** for multiple videos at once
- **Markdown Output** with proper titles and YouTube links
- **Knowledge Graph** that grows smarter with each video processed

## Setup

1. **Install Dependencies**
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

### Advanced Options
```bash
# Custom URL file
python main.py --subject "Data Science" --batch --file my_videos.txt

# Interactive mode
python main.py

# Help
python main.py --help
```

## File Formats

### URLs File (`urls.txt`)
```
https://www.youtube.com/watch?v=abc123
https://youtu.be/def456
# Comments start with # and are ignored

https://www.youtube.com/watch?v=ghi789
```

### Generated Notes Example
Files are saved as `Study notes/Subject Name/Video_Title.md`. Here's an example of generated output:

```markdown
# How to Build a Startup in 2024

[YouTube Video](https://www.youtube.com/watch?v=abc123)

---

# Video Study Notes

## Core Concepts
- Lean startup methodology focuses on rapid iteration
- Product-market fit is the primary goal before scaling

## Key Points
1. Start with a minimum viable product (MVP)
2. Validate assumptions through customer interviews
3. Pivot based on data, not opinions

## Connections & Relationships
This connects to your 'Product Management Basics' notes - both cover MVP development and customer validation strategies.

## Questions for Further Study
What metrics best indicate product-market fit has been achieved?

## Action Items & Practice
1. Interview 5 potential customers about their current solutions
2. Build an MVP with core features only
```

*Note: This is just an example - the actual content will vary based on your video's topic and existing notes.*

## Cross-Referencing

The tool automatically:
- Analyzes existing notes for key concepts
- Identifies related topics in new videos
- Adds connection notes in the "Connections & Relationships" section
- Builds a growing knowledge web across all your study materials

Perfect for stylus-based mind mapping and visual learning!

## Output Structure

All notes are saved in `study_notes_output/` with:
- **Filename**: Based on actual video title
- **Header**: Video title + YouTube link
- **Sections**: Core Concepts, Key Points, Examples, Definitions, Connections, Questions, Action Items, Critical Analysis
- **Cross-references**: Automatic mentions of related notes when applicable

## Requirements

- Python 3.10+
- Claude API key
- Internet connection for YouTube and Claude API access