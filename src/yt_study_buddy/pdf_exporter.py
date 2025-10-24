"""
PDF exporter for markdown study notes with Obsidian-style themes.

Converts markdown notes to beautiful PDFs using markdown2 and WeasyPrint.
"""
import os
import re
from pathlib import Path
from typing import Optional, List

from loguru import logger

try:
    import markdown2
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


class PDFExporter:
    """Export markdown files to PDF with custom themes."""

    # Built-in themes
    THEMES = {
        'default': 'default',
        'obsidian': 'obsidian',
        'academic': 'academic',
        'minimal': 'minimal'
    }

    def __init__(self, theme: str = 'obsidian'):
        """
        Initialize PDF exporter.

        Args:
            theme: Theme name ('default', 'obsidian', 'academic', 'minimal')
        """
        if not WEASYPRINT_AVAILABLE:
            raise ImportError(
                "PDF export requires additional dependencies. Install with:\n"
                "  uv pip install weasyprint markdown2"
            )

        self.theme = theme if theme in self.THEMES else 'obsidian'
        self.theme_dir = Path(__file__).parent / 'themes'

    def _get_theme_css(self) -> str:
        """Get CSS for the selected theme."""
        # Check for custom theme file
        theme_file = self.theme_dir / f"{self.theme}.css"

        if theme_file.exists():
            with open(theme_file, 'r', encoding='utf-8') as f:
                return f.read()

        # Return built-in theme CSS
        return self._get_builtin_theme_css()

    def _get_builtin_theme_css(self) -> str:
        """Get built-in theme CSS (fallback if no theme file exists)."""
        if self.theme == 'obsidian':
            return """
                @page {
                    size: A4;
                    margin: 2cm;
                    @top-center {
                        content: string(chapter);
                        font-size: 9pt;
                        color: #666;
                    }
                    @bottom-center {
                        content: counter(page);
                        font-size: 9pt;
                        color: #666;
                    }
                }

                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.6;
                    color: #2e3338;
                    max-width: 100%;
                }

                h1 {
                    color: #1a1a1a;
                    font-size: 24pt;
                    font-weight: 700;
                    margin-top: 0;
                    margin-bottom: 0.5em;
                    border-bottom: 2px solid #7c3aed;
                    padding-bottom: 0.3em;
                    string-set: chapter content();
                }

                h2 {
                    color: #2d2d2d;
                    font-size: 18pt;
                    font-weight: 600;
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                    border-bottom: 1px solid #e0e0e0;
                    padding-bottom: 0.2em;
                }

                h3 {
                    color: #404040;
                    font-size: 14pt;
                    font-weight: 600;
                    margin-top: 1.2em;
                    margin-bottom: 0.4em;
                }

                h4, h5, h6 {
                    color: #505050;
                    font-weight: 600;
                    margin-top: 1em;
                    margin-bottom: 0.3em;
                }

                p {
                    margin: 0.5em 0;
                    text-align: justify;
                }

                a {
                    color: #7c3aed;
                    text-decoration: none;
                }

                a:hover {
                    text-decoration: underline;
                }

                code {
                    background-color: #f5f5f5;
                    padding: 0.2em 0.4em;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                    font-size: 0.9em;
                    color: #d63384;
                }

                pre {
                    background-color: #f8f8f8;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                    padding: 1em;
                    overflow-x: auto;
                    margin: 1em 0;
                }

                pre code {
                    background-color: transparent;
                    padding: 0;
                    color: #1a1a1a;
                }

                blockquote {
                    border-left: 4px solid #7c3aed;
                    margin: 1em 0;
                    padding: 0.5em 1em;
                    background-color: #f9f9f9;
                    color: #555;
                }

                ul, ol {
                    margin: 0.5em 0;
                    padding-left: 2em;
                }

                li {
                    margin: 0.3em 0;
                }

                table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 1em 0;
                }

                th, td {
                    border: 1px solid #ddd;
                    padding: 0.5em;
                    text-align: left;
                }

                th {
                    background-color: #f0f0f0;
                    font-weight: 600;
                }

                hr {
                    border: none;
                    border-top: 2px solid #e0e0e0;
                    margin: 2em 0;
                }

                .youtube-link {
                    display: inline-block;
                    background-color: #ff0000;
                    color: white;
                    padding: 0.3em 0.8em;
                    border-radius: 4px;
                    text-decoration: none;
                    margin: 0.5em 0;
                }

                /* Obsidian-style wiki links */
                .wiki-link {
                    color: #7c3aed;
                    font-weight: 500;
                }
            """
        elif self.theme == 'academic':
            return """
                @page {
                    size: A4;
                    margin: 2.5cm;
                    @bottom-right {
                        content: counter(page);
                    }
                }

                body {
                    font-family: 'Times New Roman', Times, serif;
                    font-size: 12pt;
                    line-height: 1.8;
                    color: #000;
                }

                h1 {
                    font-size: 20pt;
                    font-weight: bold;
                    text-align: center;
                    margin-bottom: 1em;
                }

                h2 {
                    font-size: 16pt;
                    font-weight: bold;
                    margin-top: 1.5em;
                }

                h3 {
                    font-size: 14pt;
                    font-weight: bold;
                    margin-top: 1em;
                }
            """
        elif self.theme == 'minimal':
            return """
                @page {
                    size: A4;
                    margin: 2cm;
                }

                body {
                    font-family: 'Helvetica Neue', Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.5;
                    color: #333;
                }

                h1, h2, h3 {
                    font-weight: 300;
                    color: #000;
                }
            """
        else:  # default
            return """
                @page {
                    size: A4;
                    margin: 2cm;
                }

                body {
                    font-family: Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.6;
                }
            """

    def _preprocess_markdown(self, markdown_content: str) -> str:
        """
        Preprocess markdown to handle Obsidian-specific syntax.

        Args:
            markdown_content: Raw markdown content

        Returns:
            Processed markdown content
        """
        # Convert Obsidian wiki links [[Note]] to regular markdown links
        # Keep the link text but remove the [[ ]]
        def replace_wiki_link(match):
            link_text = match.group(1)
            # If it has | separator, use the alias
            if '|' in link_text:
                path, alias = link_text.split('|', 1)
                return f'<span class="wiki-link">{alias.strip()}</span>'
            return f'<span class="wiki-link">{link_text}</span>'

        markdown_content = re.sub(r'\[\[([^\]]+)\]\]', replace_wiki_link, markdown_content)

        # Handle YouTube links specially
        markdown_content = re.sub(
            r'\[YouTube Video\]\((https://[^\)]+)\)',
            r'<a href="\1" class="youtube-link">🎥 Watch on YouTube</a>',
            markdown_content
        )

        return markdown_content

    def markdown_to_pdf(
        self,
        markdown_file: Path,
        output_file: Optional[Path] = None,
        open_after: bool = False
    ) -> Path:
        """
        Convert a markdown file to PDF.

        Args:
            markdown_file: Path to markdown file
            output_file: Output PDF path (default: same name with .pdf extension)
            open_after: Open PDF after generation (default: False)

        Returns:
            Path to generated PDF file
        """
        markdown_file = Path(markdown_file)

        if not markdown_file.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_file}")

        # Read markdown content
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # Preprocess markdown
        markdown_content = self._preprocess_markdown(markdown_content)

        # Convert to HTML
        html_content = markdown2.markdown(
            markdown_content,
            extras=['fenced-code-blocks', 'tables', 'strike', 'task_list']
        )

        # Wrap in HTML document
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{markdown_file.stem}</title>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        # Determine output path
        if output_file is None:
            output_file = markdown_file.with_suffix('.pdf')
        else:
            output_file = Path(output_file)

        # Generate PDF
        html = HTML(string=full_html, base_url=str(markdown_file.parent))
        css = CSS(string=self._get_theme_css())

        html.write_pdf(output_file, stylesheets=[css])

        logger.success(f"✓ PDF generated: {output_file}")

        # Open PDF if requested
        if open_after:
            import subprocess
            import platform
            system = platform.system()
            if system == 'Darwin':  # macOS
                subprocess.run(['open', str(output_file)])
            elif system == 'Linux':
                subprocess.run(['xdg-open', str(output_file)])
            elif system == 'Windows':
                os.startfile(str(output_file))

        return output_file

    def batch_export(
        self,
        directory: Path,
        pattern: str = '*.md',
        output_dir: Optional[Path] = None,
        recursive: bool = False
    ) -> List[Path]:
        """
        Export multiple markdown files to PDF.

        Args:
            directory: Directory containing markdown files
            pattern: File pattern to match (default: '*.md')
            output_dir: Output directory (default: same as input)
            recursive: Search subdirectories (default: False)

        Returns:
            List of generated PDF paths
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        # Find markdown files
        if recursive:
            markdown_files = list(directory.rglob(pattern))
        else:
            markdown_files = list(directory.glob(pattern))

        if not markdown_files:
            logger.info(f"No markdown files found matching '{pattern}'")
            return []

        # Determine output directory
        if output_dir is None:
            output_dir = directory
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Exporting {len(markdown_files)} file(s) to PDF...")

        generated_pdfs = []
        for md_file in markdown_files:
            try:
                # Preserve directory structure if recursive
                if recursive and output_dir != directory:
                    relative_path = md_file.relative_to(directory)
                    pdf_output = output_dir / relative_path.with_suffix('.pdf')
                    pdf_output.parent.mkdir(parents=True, exist_ok=True)
                else:
                    pdf_output = output_dir / md_file.with_suffix('.pdf').name

                pdf_path = self.markdown_to_pdf(md_file, pdf_output)
                generated_pdfs.append(pdf_path)

            except Exception as e:
                logger.error(f"  ✗ Failed to export {md_file.name}: {e}")

        logger.success(f"✓ Successfully exported {len(generated_pdfs)}/{len(markdown_files)} file(s)")
        return generated_pdfs


# CLI function for standalone usage
def main():
    """Standalone CLI for PDF export."""
    import argparse

    parser = argparse.ArgumentParser(description='Export markdown notes to PDF')
    parser.add_argument('input', help='Markdown file or directory')
    parser.add_argument('-o', '--output', help='Output file or directory')
    parser.add_argument('-t', '--theme', default='obsidian',
                       choices=['default', 'obsidian', 'academic', 'minimal'],
                       help='PDF theme (default: obsidian)')
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='Process subdirectories recursively')
    parser.add_argument('--open', action='store_true',
                       help='Open PDF after generation')

    args = parser.parse_args()

    exporter = PDFExporter(theme=args.theme)
    input_path = Path(args.input)

    if input_path.is_file():
        # Single file
        output = Path(args.output) if args.output else None
        exporter.markdown_to_pdf(input_path, output, open_after=args.open)
    elif input_path.is_dir():
        # Directory
        output_dir = Path(args.output) if args.output else None
        exporter.batch_export(input_path, output_dir=output_dir, recursive=args.recursive)
    else:
        logger.error(f"Error: {input_path} is not a file or directory")
        exit(1)


if __name__ == '__main__':
    main()
