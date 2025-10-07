"""
Auto-categorization module using semantic similarity.
Automatically categorizes videos into subjects when no subject is provided.
"""

import logging
import os
import re
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logging.warning("sentence-transformers not available. Auto-categorization will use fallback method.")


class AutoCategorizer:
    """Automatically categorizes video content into appropriate subjects."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the auto-categorizer.

        Args:
            model_name: Name of the sentence transformer model to use (defaults to env var or 'all-MiniLM-L6-v2')
        """
        # Get model name from environment or use default
        self.model_name = model_name or os.getenv('SENTENCE_TRANSFORMER_MODEL', 'all-MiniLM-L6-v2')
        self.model = None
        self._similarity_threshold = 0.6

    def _load_model(self):
        """Lazy load the sentence transformer model."""
        if not SEMANTIC_AVAILABLE:
            return False

        if self.model is None:
            try:
                logging.info(f"Loading sentence transformer model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                return True
            except Exception as e:
                logging.error(f"Failed to load model {self.model_name}: {e}")
                return False
        return True

    def categorize_video(self, transcript: str, video_title: str, output_dir: str,
                        subject: Optional[str] = None) -> str:
        """
        Categorize a video into an appropriate subject.

        Args:
            transcript: Full video transcript
            video_title: Title of the video
            output_dir: Output directory containing existing subject folders
            subject: Optional user-provided subject (takes precedence)

        Returns:
            Subject category for the video
        """
        # User-provided subject always takes precedence
        if subject:
            return subject

        # Get existing subject folders
        existing_subjects = self._get_existing_subjects(output_dir)

        # If no existing subjects, extract from content
        if not existing_subjects:
            return self._extract_subject_from_content(transcript, video_title)

        # Try semantic matching if available
        if self._load_model():
            best_match = self._find_semantic_match(transcript, video_title, existing_subjects)
            if best_match:
                return best_match

        # Fallback to keyword matching
        keyword_match = self._find_keyword_match(transcript, video_title, existing_subjects)
        if keyword_match:
            return keyword_match

        # Create new subject from content
        return self._extract_subject_from_content(transcript, video_title)

    def _get_existing_subjects(self, output_dir: str) -> List[str]:
        """Get list of existing subject folders."""
        if not os.path.exists(output_dir):
            return []

        subjects = []
        try:
            for item in os.listdir(output_dir):
                item_path = os.path.join(output_dir, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    subjects.append(item)
        except OSError as e:
            logging.error(f"Error reading output directory {output_dir}: {e}")

        return subjects

    def _find_semantic_match(self, transcript: str, video_title: str,
                           existing_subjects: List[str]) -> Optional[str]:
        """Find best semantic match using sentence transformers."""
        try:
            # Combine title and first part of transcript for matching
            content_sample = f"{video_title}. {transcript[:1000]}"

            # Encode content and existing subjects
            content_embedding = self.model.encode([content_sample])
            subject_embeddings = self.model.encode(existing_subjects)

            # Calculate similarities
            similarities = cosine_similarity(content_embedding, subject_embeddings)[0]

            # Find best match above threshold
            best_idx = np.argmax(similarities)
            best_score = similarities[best_idx]

            if best_score > self._similarity_threshold:
                logging.info(f"Semantic match found: {existing_subjects[best_idx]} (score: {best_score:.3f})")
                return existing_subjects[best_idx]

        except Exception as e:
            logging.error(f"Error in semantic matching: {e}")

        return None

    def _find_keyword_match(self, transcript: str, video_title: str,
                          existing_subjects: List[str]) -> Optional[str]:
        """Find match using keyword overlap (fallback method)."""
        content = f"{video_title} {transcript}".lower()

        best_match = None
        best_score = 0

        for subject in existing_subjects:
            # Split subject into keywords
            subject_words = re.findall(r'\w+', subject.lower())

            # Count keyword matches
            matches = sum(1 for word in subject_words if word in content)
            score = matches / len(subject_words) if subject_words else 0

            if score > best_score and score > 0.3:  # At least 30% keyword overlap
                best_score = score
                best_match = subject

        if best_match:
            logging.info(f"Keyword match found: {best_match} (score: {best_score:.3f})")

        return best_match

    def _extract_subject_from_content(self, transcript: str, video_title: str) -> str:
        """Extract subject from video content when no matches found."""
        # Common technical/educational keywords and their subjects
        subject_keywords = {
            'Machine Learning': ['machine learning', 'neural network', 'deep learning', 'ai', 'artificial intelligence',
                               'tensorflow', 'pytorch', 'sklearn', 'algorithm', 'model training'],
            'Programming': ['python', 'javascript', 'programming', 'coding', 'software', 'development',
                          'function', 'variable', 'class', 'object'],
            'Data Science': ['data science', 'data analysis', 'pandas', 'numpy', 'visualization', 'statistics',
                           'dataset', 'csv', 'database'],
            'Web Development': ['html', 'css', 'react', 'vue', 'angular', 'frontend', 'backend', 'web development',
                              'api', 'http', 'server'],
            'Mathematics': ['mathematics', 'calculus', 'algebra', 'geometry', 'statistics', 'probability',
                          'equation', 'theorem', 'proof'],
            'Physics': ['physics', 'quantum', 'mechanics', 'thermodynamics', 'electricity', 'magnetism',
                       'wave', 'particle', 'energy'],
            'Business': ['business', 'entrepreneurship', 'startup', 'marketing', 'finance', 'economics',
                        'strategy', 'management', 'leadership'],
            'Technology': ['technology', 'tech', 'innovation', 'digital', 'computer', 'internet', 'software',
                          'hardware', 'cybersecurity']
        }

        content = f"{video_title} {transcript[:2000]}".lower()

        # Score each subject based on keyword matches
        subject_scores = {}
        for subject, keywords in subject_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content)
            if score > 0:
                subject_scores[subject] = score

        # Return highest scoring subject or default
        if subject_scores:
            best_subject = max(subject_scores.keys(), key=lambda k: subject_scores[k])
            logging.info(f"Extracted subject from content: {best_subject}")
            return best_subject
        else:
            # Extract first significant word from title as fallback
            title_words = re.findall(r'\b[A-Z][a-z]+\b', video_title)
            if title_words:
                return title_words[0]
            return "General"

    def get_categorization_info(self) -> dict:
        """Get information about the categorization system."""
        return {
            'semantic_available': SEMANTIC_AVAILABLE,
            'model_name': self.model_name if SEMANTIC_AVAILABLE else None,
            'similarity_threshold': self._similarity_threshold,
            'model_loaded': self.model is not None
        }