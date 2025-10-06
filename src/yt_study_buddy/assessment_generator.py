"""
Assessment generation module for creating learning assessments from video content.
Generates questions that test understanding beyond just the notes.
"""

import logging
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime


class AssessmentGenerator:
    """Generates learning assessments and questions from video content."""

    def __init__(self, claude_client):
        """
        Initialize the assessment generator.

        Args:
            claude_client: Anthropic Claude client for generating questions
        """
        self.claude_client = claude_client

    def generate_assessment(self, transcript: str, notes_content: str,
                          video_title: str, video_url: str) -> str:
        """
        Generate a comprehensive assessment file.

        Args:
            transcript: Full video transcript
            notes_content: Generated study notes
            video_title: Title of the video
            video_url: YouTube URL

        Returns:
            Formatted assessment markdown content
        """
        try:
            # Generate different types of questions
            questions_data = self._generate_questions(transcript, notes_content, video_title)

            # Format as markdown assessment file
            assessment_content = self._format_assessment_file(
                questions_data, video_title, video_url
            )

            return assessment_content

        except Exception as e:
            logging.error(f"Error generating assessment: {e}")
            return self._create_fallback_assessment(video_title, video_url)

    def _generate_questions(self, transcript: str, notes_content: str,
                          video_title: str) -> Dict:
        """Generate different types of questions using Claude."""

        prompt = f"""Based on this YouTube video, create a learning assessment with 5-7 questions that test deep understanding.

VIDEO TITLE: {video_title}

FULL TRANSCRIPT: {transcript[:3000]}...

GENERATED NOTES: {notes_content}

Create questions in these categories:

1. GAP ANALYSIS (1-2 questions): What important details were in the video but NOT captured in the notes?

2. APPLICATION (2-3 questions): How would you apply these concepts in real scenarios?

3. ONE-UP CHALLENGES (1-2 questions): How could you improve/extend the implementations or ideas discussed?

4. SYNTHESIS (1-2 questions): How do these concepts connect to broader topics in the field?

For each question, provide:
- Clear question text
- Model answer (2-3 sentences)
- Key concepts being tested

IMPORTANT: Return ONLY valid JSON with no additional text, explanation, or markdown formatting.

Return this exact JSON structure:
{{
    "gap_analysis": [
        {{"question": "...", "model_answer": "...", "concepts": ["..."]}}
    ],
    "application": [
        {{"question": "...", "model_answer": "...", "concepts": ["..."]}}
    ],
    "one_up": [
        {{"question": "...", "model_answer": "...", "concepts": ["..."]}}
    ],
    "synthesis": [
        {{"question": "...", "model_answer": "...", "concepts": ["..."]}}
    ]
}}"""

        try:
            response = self.claude_client.messages.create(
                model="claude-sonnet-4-5-20250929",  # Claude Sonnet 4.5 (latest)
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract and parse JSON from response
            response_text = response.content[0].text
            questions_data = self._extract_json_from_response(response_text)

            if questions_data:
                return questions_data
            else:
                logging.warning("Could not parse JSON from Claude response, using fallback questions")
                return self._create_fallback_questions(video_title)

        except Exception as e:
            logging.error(f"Error calling Claude API for questions: {e}")
            return self._create_fallback_questions(video_title)

    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """
        Extract and parse JSON from Claude's response, handling various formats.

        Handles:
        - Plain JSON
        - JSON wrapped in markdown code blocks (```json ... ```)
        - JSON with explanatory text before/after

        Args:
            response_text: Raw text response from Claude

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        import json

        # Try 1: Parse as-is (plain JSON)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try 2: Extract from markdown code block
        # Match ```json ... ``` or ``` ... ```
        code_block_patterns = [
            r'```json\s*\n(.*?)\n```',  # ```json ... ```
            r'```\s*\n(.*?)\n```',       # ``` ... ```
        ]

        for pattern in code_block_patterns:
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1).strip()
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue

        # Try 3: Find JSON object by looking for { ... } pattern
        # Find the largest valid JSON object in the text
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.finditer(json_pattern, response_text, re.DOTALL)

        # Try each match, starting with the longest
        potential_jsons = sorted([m.group(0) for m in matches], key=len, reverse=True)
        for json_str in potential_jsons:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue

        # Try 4: Look for JSON array pattern
        array_pattern = r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
        matches = re.finditer(array_pattern, response_text, re.DOTALL)
        potential_arrays = sorted([m.group(0) for m in matches], key=len, reverse=True)
        for json_str in potential_arrays:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue

        logging.error(f"Could not extract valid JSON from response. First 200 chars: {response_text[:200]}")
        return None

    def _create_fallback_questions(self, video_title: str) -> Dict:
        """Create basic questions when API fails."""
        return {
            "gap_analysis": [
                {
                    "question": f"What important technical details about {video_title} might have been mentioned in the video but weren't captured in the summary notes?",
                    "model_answer": "Consider implementation specifics, edge cases, performance considerations, or practical tips that are often mentioned verbally but may not make it into condensed notes.",
                    "concepts": ["technical details", "implementation"]
                }
            ],
            "application": [
                {
                    "question": f"How would you apply the main concepts from this video about {video_title} to solve a real-world problem in your current projects?",
                    "model_answer": "Think about your specific use cases and how the demonstrated techniques could be adapted or integrated into your existing workflow.",
                    "concepts": ["practical application", "problem solving"]
                }
            ],
            "one_up": [
                {
                    "question": f"How could you improve or extend the approach shown in the {video_title} video using modern tools or techniques?",
                    "model_answer": "Consider newer technologies, optimization techniques, or combining with other approaches to create a more robust or efficient solution.",
                    "concepts": ["optimization", "innovation"]
                }
            ],
            "synthesis": [
                {
                    "question": f"How do the concepts from this {video_title} video connect to other topics you've been learning about?",
                    "model_answer": "Look for patterns, shared principles, or complementary techniques that appear across different domains or technologies.",
                    "concepts": ["connections", "synthesis"]
                }
            ]
        }

    def _format_assessment_file(self, questions_data: Dict, video_title: str,
                              video_url: str) -> str:
        """Format questions into a markdown assessment file."""

        assessment_content = f"""# {video_title} - Learning Assessment

[Original Video]({video_url})

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Instructions

Answer each question in the space provided. Focus on demonstrating understanding beyond just recalling the notes. After completing all questions, you can reveal the model answers at the bottom for comparison.

---

"""

        question_num = 1

        # Add each category of questions
        for category, questions in questions_data.items():
            if not questions:
                continue

            category_title = self._get_category_title(category)
            assessment_content += f"## {category_title}\n\n"

            for q in questions:
                assessment_content += f"### Question {question_num}\n"
                assessment_content += f"{q['question']}\n\n"
                assessment_content += f"**Your Answer:**\n"
                assessment_content += f"[Write your response here]\n\n"
                assessment_content += f"---\n\n"
                question_num += 1

        # Add model answers section (hidden)
        assessment_content += "## Model Answers\n\n"
        assessment_content += "<!-- SPOILER ALERT: Model answers below. Complete your answers first! -->\n\n"

        question_num = 1
        for category, questions in questions_data.items():
            if not questions:
                continue

            category_title = self._get_category_title(category)
            assessment_content += f"### {category_title} - Model Answers\n\n"

            for q in questions:
                assessment_content += f"**Question {question_num}:** {q['question']}\n\n"
                assessment_content += f"**Model Answer:** {q['model_answer']}\n\n"
                assessment_content += f"**Key Concepts:** {', '.join(q['concepts'])}\n\n"
                assessment_content += f"---\n\n"
                question_num += 1

        return assessment_content

    def _get_category_title(self, category: str) -> str:
        """Convert category key to display title."""
        titles = {
            'gap_analysis': 'Gap Analysis - Beyond the Notes',
            'application': 'Practical Application',
            'one_up': 'Innovation Challenges',
            'synthesis': 'Connections & Synthesis'
        }
        return titles.get(category, category.title())

    def _create_fallback_assessment(self, video_title: str, video_url: str) -> str:
        """Create a basic assessment when generation fails."""
        return f"""# {video_title} - Learning Assessment

[Original Video]({video_url})

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Assessment Generation Error

Unable to generate custom assessment questions. Please consider these general reflection questions:

### Question 1: Key Insights
What were the 3 most important insights from this video that weren't captured in your notes?

**Your Answer:**
[Write your response here]

### Question 2: Practical Application
How would you apply the main concepts from this video to a current project or problem you're working on?

**Your Answer:**
[Write your response here]

### Question 3: Improvement Opportunities
What aspects of the approach shown in the video could be improved or modernized?

**Your Answer:**
[Write your response here]

### Question 4: Broader Connections
How do the concepts in this video relate to other topics you've been studying?

**Your Answer:**
[Write your response here]

---

*Note: This is a fallback assessment. For better question generation, ensure Claude API is properly configured.*
"""

    def create_assessment_filename(self, video_title: str) -> str:
        """Create a safe filename for the assessment."""
        # Clean title for filename
        safe_title = re.sub(r'[^\w\s-]', '', video_title)
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        return f"{safe_title}_Assessment.md"