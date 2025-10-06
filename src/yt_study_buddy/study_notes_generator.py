"""
Study notes generation using Claude API with cross-referencing capabilities.
"""
import os
from dotenv import load_dotenv

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
            print("\\nERROR: Claude API key not found!")
            print("Please set your API key in one of these ways:")
            print("1. Create a .env file with: CLAUDE_API_KEY=your_key_here")
            print("2. Set environment variable: CLAUDE_API_KEY=your_key_here")
            print("3. Set environment variable: ANTHROPIC_API_KEY=your_key_here")
            print("\\nGet your API key from: https://console.anthropic.com/")
            return None
        return api_key

    def is_ready(self):
        """Check if the generator is ready to use."""
        if not anthropic:
            print("ERROR: anthropic library not installed. Run: pip install anthropic")
            return False
        if not self.client:
            print("ERROR: No valid API key found")
            return False
        return True

    def generate_notes(self, transcript, related_notes=None):
        """Generate study notes from transcript with optional cross-references."""
        if not self.is_ready():
            return None

        try:
            prompt = self._build_prompt(transcript, related_notes)

            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",  # Claude Sonnet 4.5 (latest)
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            return message.content[0].text

        except Exception as e:
            print(f"ERROR calling Claude API: {e}")
            return None

    def _build_prompt(self, transcript, related_notes=None):
        """Build the prompt for Claude API."""
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

        prompt = f"""Create comprehensive educational notes from this YouTube video transcript. Format this for learning and mind mapping.

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

    def create_markdown_file(self, title, video_url, study_notes, output_dir="Study notes", video_id=None):
        """Create a markdown file with the study notes."""
        from .video_processor import VideoProcessor  # Import here to avoid circular imports

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Create markdown content with title and link header
        markdown_content = f"# {title}\\n\\n[YouTube Video]({video_url})\\n\\n---\\n\\n{study_notes}"

        # Generate safe filename
        safe_title = VideoProcessor.sanitize_filename(title)
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