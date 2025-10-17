# PDF Export Guide

Export your study notes to beautiful PDFs with Obsidian-style formatting!

## Installation

PDF export requires additional dependencies:

```bash
# Install PDF export dependencies
uv pip install weasyprint markdown2

# Or install with the pdf extra
uv sync --extra pdf
```

## Quick Start

### Command Line Usage

Export notes to PDF when processing videos:

```bash
# Single video with PDF export
yt-study-buddy --export-pdf https://youtube.com/watch?v=xyz

# Batch processing with PDF export
yt-study-buddy --export-pdf --file urls.txt

# Parallel processing with PDF export
yt-study-buddy --parallel --export-pdf --file playlist.txt
```

### Choose a Theme

Four built-in themes are available:

```bash
# Obsidian theme (default) - Purple accents, clean formatting
yt-study-buddy --export-pdf --pdf-theme obsidian <url>

# Academic theme - Formal, Times New Roman
yt-study-buddy --export-pdf --pdf-theme academic <url>

# Minimal theme - Clean, simple design
yt-study-buddy --export-pdf --pdf-theme minimal <url>

# Default theme - Basic styling
yt-study-buddy --export-pdf --pdf-theme default <url>
```

## Themes Preview

### Obsidian Theme (Default)
- **Font**: System fonts (San Francisco, Segoe UI, etc.)
- **Style**: Purple accents, bordered headings
- **Features**: Page numbers, chapter headers, styled code blocks
- **Use case**: Modern, professional study notes

### Academic Theme
- **Font**: Times New Roman
- **Style**: Formal, centered titles
- **Features**: Traditional academic formatting
- **Use case**: Formal papers, academic submissions

### Minimal Theme
- **Font**: Helvetica Neue
- **Style**: Clean, lightweight
- **Features**: Simple, distraction-free
- **Use case**: Quick reference, printing

### Default Theme
- **Font**: Arial
- **Style**: Basic HTML styling
- **Features**: Standard formatting
- **Use case**: Simple exports

## Features

### Obsidian Syntax Support

The PDF exporter handles Obsidian-specific markdown:

**Wiki Links**: `[[Note Name]]` → Styled cross-references
**YouTube Links**: Special button styling for video links
**Code Blocks**: Syntax highlighting with monospace fonts
**Tables**: Properly formatted with borders
**Blockquotes**: Highlighted with left border
**Headings**: Styled with borders and hierarchy

### What Gets Exported

When you use `--export-pdf`:
1. **Study Notes**: Main markdown file → PDF
2. **Assessments**: Assessment file → PDF (if enabled)
3. **Formatting**: All Obsidian links, code, tables preserved

### Output Location

PDFs are saved alongside markdown files:
```
notes/
├── Python_Programming.md
├── Python_Programming.pdf        ← Study notes PDF
├── Assessment_Python.md
└── Assessment_Python.pdf          ← Assessment PDF
```

## Programmatic Usage

Use the PDF exporter in your own scripts:

```python
from pathlib import Path
from yt_study_buddy.pdf_exporter import PDFExporter

# Create exporter with theme
exporter = PDFExporter(theme='obsidian')

# Export single file
pdf_path = exporter.markdown_to_pdf(
    Path('notes/my_note.md'),
    output_file=Path('notes/my_note.pdf')
)

# Batch export directory
pdf_files = exporter.batch_export(
    directory=Path('notes/Python'),
    pattern='*.md',
    recursive=True
)

print(f"Generated {len(pdf_files)} PDFs")
```

## Advanced Usage

### Custom Output Directory

```python
exporter.batch_export(
    directory=Path('notes'),
    output_dir=Path('pdfs'),
    recursive=True
)
```

### Open PDF After Generation

```python
exporter.markdown_to_pdf(
    Path('note.md'),
    open_after=True  # Opens PDF in default viewer
)
```

### Standalone CLI

The PDF exporter can be used independently:

```bash
# Export single file
uv run python -m yt_study_buddy.pdf_exporter note.md

# Export with theme
uv run python -m yt_study_buddy.pdf_exporter note.md -t academic

# Export directory recursively
uv run python -m yt_study_buddy.pdf_exporter notes/ -r -o pdfs/

# Open after export
uv run python -m yt_study_buddy.pdf_exporter note.md --open
```

## Customization

### Custom CSS Themes

Create custom themes by adding CSS files to `src/yt_study_buddy/themes/`:

```css
/* themes/custom.css */
@page {
    size: A4;
    margin: 2cm;
}

body {
    font-family: 'Georgia', serif;
    font-size: 12pt;
    color: #1a1a1a;
}

h1 {
    color: #2c5282;
    border-bottom: 3px solid #2c5282;
}
```

Then use it:
```bash
yt-study-buddy --export-pdf --pdf-theme custom <url>
```

### Page Settings

Modify the `@page` CSS rules to customize:
- **Page size**: A4, Letter, A5
- **Margins**: Top, bottom, left, right
- **Headers/Footers**: Page numbers, chapter names
- **Orientation**: Portrait or landscape

## Troubleshooting

### Installation Issues

**WeasyPrint won't install:**
```bash
# On Ubuntu/Debian
sudo apt-get install python3-dev libpango1.0-dev libcairo2-dev

# On macOS
brew install cairo pango gdk-pixbuf libffi

# Then retry
uv pip install weasyprint
```

**Permission errors:**
```bash
# Ensure output directory is writable
chmod +w notes/
```

### PDF Issues

**Fonts not rendering:**
- WeasyPrint uses system fonts
- Install missing fonts: `sudo apt-get install fonts-liberation`

**Code blocks look wrong:**
- Ensure monospace font is available: Courier New, Monaco, Consolas

**Images not appearing:**
- Images must be accessible from markdown file location
- Use relative paths: `![](./images/diagram.png)`

### Performance

**Slow PDF generation:**
- PDF generation adds ~2-3 seconds per file
- Use `--export-pdf` only when needed
- For batch exports, generate PDFs after all markdown is created

## Examples

### Full Workflow

```bash
# 1. Process videos with all features
yt-study-buddy \
  --parallel \
  --workers 3 \
  --subject "Machine Learning" \
  --export-pdf \
  --pdf-theme obsidian \
  --file ml_playlist.txt

# Result:
# notes/Machine Learning/
# ├── Neural_Networks.md
# ├── Neural_Networks.pdf
# ├── Assessment_Neural_Networks.md
# ├── Assessment_Neural_Networks.pdf
# ├── Deep_Learning.md
# ├── Deep_Learning.pdf
# ...
```

### Convert Existing Notes

```bash
# Export existing markdown notes to PDF
cd notes
find . -name "*.md" -type f | while read file; do
  uv run python -m yt_study_buddy.pdf_exporter "$file" -t obsidian
done
```

### Batch Export Script

```python
#!/usr/bin/env python3
"""Batch export all notes to PDF."""
from pathlib import Path
from yt_study_buddy.pdf_exporter import PDFExporter

exporter = PDFExporter(theme='obsidian')

# Export all subjects
for subject_dir in Path('../notes').iterdir():
    if subject_dir.is_dir():
        print(f"\nExporting {subject_dir.name}...")
        pdfs = exporter.batch_export(
            subject_dir,
            pattern='*.md',
            recursive=False
        )
        print(f"  Generated {len(pdfs)} PDFs")
```

## Tips

1. **Use Obsidian theme** for best results - it's optimized for study notes
2. **Generate PDFs at the end** of batch processing to save time
3. **Academic theme** works well for printing
4. **Minimal theme** reduces file size (good for sharing)
5. **Test themes** on one note before batch processing

## Technical Details

### Under the Hood

- **Markdown Parser**: markdown2 (faster than python-markdown)
- **PDF Generator**: WeasyPrint (Chromium-quality rendering)
- **CSS Engine**: Paged Media CSS for print-specific styling
- **Font Support**: System fonts + fallback chains

### Supported Markdown

✅ Headers (H1-H6)
✅ Bold, italic, strikethrough
✅ Code blocks with language
✅ Inline code
✅ Tables
✅ Lists (ordered, unordered, nested)
✅ Blockquotes
✅ Links
✅ Horizontal rules
✅ Task lists
✅ Obsidian wiki links [[Note]]

❌ Images (limited support)
❌ Mermaid diagrams
❌ LaTeX equations

## Resources

- WeasyPrint Docs: https://doc.courtbouillon.org/weasyprint/
- CSS Paged Media: https://www.w3.org/TR/css-page-3/
- Markdown2: https://github.com/trentm/python-markdown2

---

**Enjoy your beautiful PDFs!** 📄✨
