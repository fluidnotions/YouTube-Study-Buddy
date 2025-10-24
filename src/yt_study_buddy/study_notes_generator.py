"""
Study notes generation using Claude API with cross-referencing capabilities.
"""
import os

from dotenv import load_dotenv
from loguru import logger

try:
    import anthropic
except ImportError:
    anthropic = None

# Load environment variables from .env file
load_dotenv()


class StudyNotesGenerator:
    """Generates study notes using Claude API with cross-reference support."""

    def __init__(self):
        self.client = None
        self._setup_api()

    def _setup_api(self):
        """Setup Claude API client."""
        api_key = self.get_api_key()
        if api_key and anthropic:
            self.client = anthropic.Anthropic(api_key=api_key)

    @staticmethod
    def get_api_key():
        """Get Claude API key from environment or .env file."""
        api_key = os.getenv('CLAUDE_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.error("\\nERROR: Claude API key not found!")
            logger.info("Please set your API key in one of these ways:")
            logger.info("1. Create a .env file with: CLAUDE_API_KEY=your_key_here")
            logger.info("2. Set environment variable: CLAUDE_API_KEY=your_key_here")
            logger.info("3. Set environment variable: ANTHROPIC_API_KEY=your_key_here")
            logger.info("\\nGet your API key from: https://console.anthropic.com/")
            return None
        return api_key

    def is_ready(self):
        """Check if the generator is ready to use."""
        if not anthropic:
            logger.error("ERROR: anthropic library not installed. Run: pip install anthropic")
            return False
        if not self.client:
            logger.error("ERROR: No valid API key found")
            return False
        return True

    def suggest_title(self, transcript: str, max_length: int = 60) -> str:
        """
        Generate a concise title from transcript content using Claude.

        Args:
            transcript: Video transcript text
            max_length: Maximum title length (default: 60)

        Returns:
            Suggested title or None if generation fails
        """
        if not self.is_ready():
            return None

        try:
            # Use faster model for quick title generation
            model = os.getenv('TITLE_GENERATION_MODEL', 'claude-3-5-haiku-20241022')

            # Truncate transcript if too long (first ~2000 chars usually enough)
            sample_transcript = transcript[:2000] if len(transcript) > 2000 else transcript

            prompt = f"""Analyze this video transcript excerpt and suggest a clear, descriptive title.

Requirements:
- Maximum {max_length} characters
- Describe the main topic/subject
- Be specific and informative
- Use title case
- No quotes or special characters that would break filenames
- Focus on what the video teaches/discusses

Transcript excerpt:
{sample_transcript}

Respond with ONLY the title, nothing else."""

            message = self.client.messages.create(
                model=model,
                max_tokens=100,  # Short response
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            title = message.content[0].text.strip()

            # Clean title for filename
            import re
            title = re.sub(r'[<>:"/\\|?*]', '_', title)
            title = re.sub(r'\s+', ' ', title).strip()

            # Ensure it's not too long
            if len(title) > max_length:
                title = title[:max_length].rsplit(' ', 1)[0]  # Cut at last space

            return title

        except Exception as e:
            logger.error(f"⚠️  AI title generation failed: {e}")
            return None

    def generate_notes(self, transcript, related_notes=None, suggest_title=False):
        """Generate study notes from transcript with optional cross-references.

        Args:
            transcript: Video transcript text
            related_notes: Optional list of related notes for cross-referencing
            suggest_title: If True, asks Claude to suggest a descriptive title

        Returns:
            Generated notes text (may include title if suggest_title=True)
        """
        if not self.is_ready():
            return None

        try:
            prompt = self._build_prompt(transcript, related_notes, suggest_title)
            model = os.getenv('GENERATE_NOTES_MODEL', 'claude-sonnet-4-5-20250929')
            message = self.client.messages.create(
                model=model,
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            return message.content[0].text

        except Exception as e:
            logger.error(f"ERROR calling Claude API: {e}")
            return None

    def _build_prompt(self, transcript, related_notes=None, suggest_title=False):
        """Build the prompt for Claude API.

        Args:
            transcript: Video transcript text
            related_notes: Optional list of related notes for cross-referencing
            suggest_title: If True, asks Claude to suggest a descriptive title
        """
        # Build related notes context if available
        related_context = ""
        if related_notes:
            related_context = "\\n\\nRELATED STUDY NOTES (for cross-referencing):\\n"
            for i, note in enumerate(related_notes, 1):
                concepts_str = ", ".join(note['matching_concepts'])
                subject_info = f" (Subject: {note['subject']})" if note.get('subject') else ""
                related_context += f"{i}. '{note['title']}'{subject_info} - shared concepts: {concepts_str}\\n"
            related_context += "\\n"

        connections_instruction = ""
        if related_notes:
            connections_instruction = " Also note connections to related study notes listed below - mention which notes cover similar topics and how they might connect."

        # Title suggestion instruction
        title_instruction = ""
        if suggest_title:
            title_instruction = """
IMPORTANT: Start your response with a descriptive title for this video on the first line as:
# Title: <your suggested title here>

The title should:
- Be 5-10 words maximum
- Describe the main topic/subject clearly
- Be specific and informative
- Use title case
- No quotes or special characters

Then continue with the study notes below.

"""

        prompt = f"""Create comprehensive educational notes from this YouTube video transcript. Format this for learning and mind mapping.
{title_instruction}

# Video Study Notes

## Core Concepts
List the main ideas with clear, brief explanations. Focus on the fundamental principles being taught.

## Key Points
Number the most important details and insights from the video. Include specific facts, statistics, or claims made.

## Examples & Applications (Only if applicable, if not, leave out)
List concrete examples, case studies, or real-world applications mentioned in the video.

## Definitions & Terminology (Only if applicable, if not, leave out)
Extract and define key terms, jargon, or technical vocabulary used.

## Connections & Relationships (Only if applicable, if not, leave out)
How do the concepts relate to each other? What are the cause-effect relationships?{connections_instruction}

## Questions for Further Study (Only if applicable, if not, leave out)
What questions does this raise? What should I explore deeper? What wasn't fully explained?

## Action Items & Practice (Only if applicable, if not, leave out)
What concrete steps can I take to apply this knowledge? What should I practice or try?

## Critical Analysis (Only if applicable, if not, leave out)
What are the strengths and potential limitations of the ideas presented?
{related_context}
Transcript to analyze:
{transcript}

Please create comprehensive study notes that I can use for learning. Make them detailed but well-organized.
I'm going to be using them to annotate and highlight sections and connect them together on Miro, an Infinite Canvas, so I need the layout of the information provided to be fairly spacious so that I can write stuff in using a stylus and also connect sections to other places on the Infinite Canvas."""

        return prompt

    @staticmethod
    def extract_title_from_notes(study_notes):
        """
        Extract the video title from Claude's generated notes.

        Looks for patterns:
        - '# Title: <title>' (when suggest_title=True)
        - '# Video Study Notes: <title>'
        - '# VIDEO STUDY NOTES: <title>'

        Returns:
            Tuple of (extracted_title, notes_without_title) or (None, study_notes)
        """
        import re

        # Try to match "# Title: ..." pattern first (suggest_title format)
        match = re.search(r'^#\s+Title:\s*(.+)$', study_notes, re.MULTILINE | re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            # Remove the title line from notes
            notes_without_title = re.sub(r'^#\s+Title:\s*.+\n*', '', study_notes, count=1, flags=re.MULTILINE | re.IGNORECASE)
            return title, notes_without_title.strip()

        # Try old pattern for backward compatibility
        match = re.search(r'^#\s+(?:VIDEO\s+)?[Vv]ideo\s+[Ss]tudy\s+[Nn]otes:\s*(.+)$', study_notes, re.MULTILINE)
        if match:
            return match.group(1).strip(), study_notes

        return None, study_notes

    def create_markdown_file(self, title, video_url, study_notes, output_dir="Study notes", video_id=None):
        """Create a markdown file with the study notes."""
        from .video_processor import VideoProcessor  # Import here to avoid circular imports

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Try to extract a better title from the generated notes
        extracted_title = self.extract_title_from_notes(study_notes)
        if extracted_title:
            # Use the extracted title for both the filename and header
            final_title = extracted_title
        elif title and not title.startswith("Video_"):
            # Use the provided title if it's not a fallback
            final_title = title
        else:
            # Fallback to video_id based title
            final_title = f"Video_{video_id}" if video_id else title

        # Create markdown content with title and link header
        markdown_content = f"# {final_title}\n\n[YouTube Video]({video_url})\n\n---\n\n{study_notes}"

        # Generate safe filename
        safe_title = VideoProcessor.sanitize_filename(final_title)
        filename = os.path.join(output_dir, f"{safe_title}.md")

        # Handle duplicate filenames
        counter = 1
        original_filename = filename
        while os.path.exists(filename):
            name_part = os.path.splitext(original_filename)[0]
            filename = f"{name_part}_{counter}.md"
            counter += 1

        # Write the file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        return filename