"""
Obsidian linker for automatically creating Obsidian-style [[links]] between study notes.
Handles both RAG-based semantic linking and fuzzy matching fallback.
"""
import logging
import os
import re
from typing import Optional

try:
    from fuzzywuzzy import fuzz, process
except ImportError:
    fuzz = None
    process = None

logger = logging.getLogger(__name__)


class ObsidianLinker:
    """Creates Obsidian-style [[links]] between related study notes.

    This linker supports two modes:
    1. RAG-based semantic linking (primary, if enabled)
    2. Fuzzy matching fallback (if RAG unavailable or disabled)
    """

    def __init__(self, base_dir="Study notes", subject=None, global_context=True, min_similarity=85, use_rag=True):
        self.base_dir = base_dir
        self.subject = subject
        self.global_context = global_context
        self.min_similarity = min_similarity
        self.note_titles = {}  # Cache of {title: (file_path, subject)}

        # RAG components (lazy initialization)
        self.use_rag = use_rag
        self.rag_referencer = None
        self.rag_config = None
        self._rag_initialized = False

        # Try to initialize RAG if requested
        if self.use_rag:
            self._initialize_rag()

    def _initialize_rag(self):
        """Initialize RAG components if available."""
        if self._rag_initialized:
            return

        try:
            from .rag.config import load_config_from_env
            from .rag.embedding_service import EmbeddingService
            from .rag.vector_store import VectorStore
            from .rag.cross_referencer import RAGCrossReferencer

            # Load configuration
            self.rag_config = load_config_from_env()

            if not self.rag_config.enabled:
                logger.info("RAG is disabled in configuration")
                self.use_rag = False
                return

            # Initialize components
            embedding_service = EmbeddingService(
                model_name=self.rag_config.model_name,
                cache_dir=str(self.rag_config.model_cache_dir),
            )

            vector_store = VectorStore(
                persist_dir=str(self.rag_config.vector_store_dir),
                collection_name=self.rag_config.collection_name,
            )

            self.rag_referencer = RAGCrossReferencer(
                embedding_service=embedding_service,
                vector_store=vector_store,
                config=self.rag_config,
            )

            self._rag_initialized = True
            logger.info("RAG initialized successfully for ObsidianLinker")

        except Exception as e:
            logger.warning(f"Failed to initialize RAG: {e}. Falling back to fuzzy matching.")
            self.use_rag = False
            self.rag_referencer = None

    def build_note_index(self):
        """Build an index of all available note titles for linking."""
        self.note_titles = {}

        # Determine directories to scan based on context
        dirs_to_scan = []
        if self.global_context and os.path.exists(self.base_dir):
            # Scan all subjects for global context
            for item in os.listdir(self.base_dir):
                item_path = os.path.join(self.base_dir, item)
                if os.path.isdir(item_path):
                    dirs_to_scan.append((item_path, item))  # (path, subject)
            # Also scan base directory for any loose files
            dirs_to_scan.append((self.base_dir, None))
        else:
            # Subject-specific context
            subject_dir = os.path.join(self.base_dir, self.subject) if self.subject else self.base_dir
            if os.path.exists(subject_dir):
                dirs_to_scan.append((subject_dir, self.subject))

        # Build the index
        for dir_path, subject_name in dirs_to_scan:
            if not os.path.exists(dir_path):
                continue

            for filename in os.listdir(dir_path):
                if not filename.endswith('.md'):
                    continue

                filepath = os.path.join(dir_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Extract title (first line after #)
                    title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
                    if title_match:
                        title = title_match.group(1).strip()
                        self.note_titles[title] = {
                            'file_path': filepath,
                            'subject': subject_name,
                            'filename': filename
                        }

                except Exception as e:
                    print(f"Warning: Could not process {filename} for linking: {e}")
                    continue

    def extract_existing_links(self, content):
        """Extract existing Obsidian links to avoid double-linking."""
        # Find all existing [[links]]
        existing_links = re.findall(r'\[\[([^\]]+)\]\]', content)
        return set(existing_links)

    def find_potential_links(self, content, exclude_current_title=None):
        """Find potential phrases in content that could be linked to existing notes."""
        if not fuzz or not process:
            print("Warning: fuzzywuzzy not available for fuzzy matching. Install with: pip install fuzzywuzzy")
            return []

        # Get existing links to avoid double-linking
        existing_links = self.extract_existing_links(content)

        # Get all available note titles (excluding current note)
        available_titles = {title: data for title, data in self.note_titles.items()
                          if title != exclude_current_title}

        if not available_titles:
            return []

        potential_links = []

        # Split content into sentences and phrases for analysis
        sentences = re.split(r'[.!?]+', content)

        for sentence in sentences:
            # Skip if sentence is too short or is already a header/link
            if len(sentence.strip()) < 10 or sentence.strip().startswith('#') or '[[' in sentence:
                continue

            # Extract potential phrases (noun phrases, technical terms, etc.)
            # Look for capitalized phrases, technical terms, and multi-word concepts
            phrases = self._extract_phrases(sentence)

            for phrase in phrases:
                # Skip if this phrase is already linked
                if phrase in existing_links:
                    continue

                # Find best matches using fuzzy matching
                matches = process.extractBests(
                    phrase, available_titles.keys(),
                    scorer=fuzz.token_sort_ratio,
                    score_cutoff=self.min_similarity,
                    limit=3
                )

                for match_title, score in matches:
                    # Additional checks to avoid false positives
                    if self._is_valid_link(phrase, match_title, sentence):
                        potential_links.append({
                            'phrase': phrase,
                            'title': match_title,
                            'score': score,
                            'subject': available_titles[match_title]['subject'],
                            'sentence': sentence.strip()
                        })

        # Sort by score and remove duplicates
        potential_links.sort(key=lambda x: x['score'], reverse=True)
        seen_phrases = set()
        unique_links = []

        for link in potential_links:
            if link['phrase'] not in seen_phrases:
                unique_links.append(link)
                seen_phrases.add(link['phrase'])

        return unique_links[:10]  # Limit to top 10 links to avoid over-linking

    def _extract_phrases(self, sentence):
        """Extract potential linkable phrases from a sentence."""
        phrases = []

        # Look for multi-word capitalized phrases (proper nouns, technical terms)
        capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', sentence)
        phrases.extend([p for p in capitalized_phrases if len(p) > 3])

        # Look for technical terms and concepts (words with specific patterns)
        technical_terms = re.findall(r'\b[a-z]+(?:[A-Z][a-z]*)+\b', sentence)  # camelCase terms
        phrases.extend(technical_terms)

        # Look for quoted terms
        quoted_terms = re.findall(r'"([^"]+)"', sentence)
        phrases.extend([q for q in quoted_terms if len(q) > 3])

        # Look for terms in parentheses
        parenthetical = re.findall(r'\(([^)]+)\)', sentence)
        phrases.extend([p for p in parenthetical if len(p) > 3 and not p.isdigit()])

        return list(set(phrases))  # Remove duplicates

    def _is_valid_link(self, phrase, title, context):
        """Validate if a phrase should be linked to a title."""
        # Avoid linking very short phrases
        if len(phrase) < 4:
            return False

        # Avoid linking common words
        common_words = {'this', 'that', 'with', 'from', 'they', 'will', 'have', 'been',
                       'were', 'your', 'what', 'when', 'where', 'how', 'why', 'the', 'and', 'or'}
        if phrase.lower() in common_words:
            return False

        # Avoid linking URLs or file extensions
        if any(ext in phrase.lower() for ext in ['.com', '.org', 'http', 'www', '.py', '.js']):
            return False

        # Check if the phrase makes sense in context (basic semantic check)
        # Avoid linking if the phrase is part of a URL, code, or formatting
        if any(marker in context for marker in ['```', '`', 'http', 'www', '##']):
            return False

        return True

    def apply_links(self, content, file_path, current_title=None, current_video_id=None):
        """Apply Obsidian links to the content using RAG or fuzzy matching.

        Args:
            content: Markdown content to add links to
            file_path: Path to the file being processed
            current_title: Title of current note (to exclude self-references)
            current_video_id: Video ID of current note (for RAG filtering)

        Returns:
            Modified content with links added
        """
        # Try RAG-based linking first
        if self.use_rag and self.rag_referencer:
            try:
                return self._apply_links_rag(content, file_path, current_title, current_video_id)
            except Exception as e:
                logger.warning(f"RAG linking failed: {e}. Falling back to fuzzy matching.")

        # Fallback to fuzzy matching
        return self._apply_links_fuzzy(content, file_path, current_title)

    def _apply_links_rag(self, content, file_path, current_title=None, current_video_id=None):
        """Apply links using RAG-based semantic search."""
        if not current_video_id:
            # Try to extract video ID from filename
            current_video_id = self._extract_video_id_from_path(file_path)

        if not current_video_id:
            logger.warning("No video ID available for RAG linking, using fuzzy fallback")
            return self._apply_links_fuzzy(content, file_path, current_title)

        # Split content into sections (## headings)
        sections = self._split_content_into_sections(content)

        if not sections:
            logger.debug("No sections found in content")
            return content

        modified_content = content
        total_links_added = 0

        # Find references for each section
        for section_title, section_text in sections:
            # Skip very short sections
            if len(section_text.strip()) < 50:
                continue

            # Find cross-references using RAG
            cross_refs = self.rag_referencer.find_references(
                section_text=section_text,
                current_video_id=current_video_id,
                subject=self.subject if not self.global_context else None,
                global_context=self.global_context,
            )

            # Add links to content (limit to avoid over-linking)
            for ref in cross_refs[:3]:  # Max 3 links per section
                link = ref.obsidian_link
                # Check if link already exists in content
                if link not in modified_content:
                    # Add link at end of section with "See also:" prefix
                    section_end_pattern = r'(## ' + re.escape(section_title) + r'.*?)(\n## |\Z)'
                    match = re.search(section_end_pattern, modified_content, re.DOTALL)
                    if match:
                        section_content = match.group(1)
                        # Add "See also" if not already there
                        if "See also:" not in section_content:
                            replacement = section_content + f"\n\n**See also:** {link}"
                        else:
                            replacement = section_content.rstrip() + f", {link}"

                        modified_content = modified_content.replace(match.group(1), replacement, 1)
                        total_links_added += 1
                        print(f"    RAG linked: {ref.target_video_title} (score: {ref.similarity_score:.3f})")

        if total_links_added > 0:
            print(f"  Added {total_links_added} RAG-based links")

        return modified_content

    def _apply_links_fuzzy(self, content, file_path, current_title=None):
        """Apply links using fuzzy matching (original behavior)."""
        if not self.note_titles:
            self.build_note_index()

        # Find potential links
        potential_links = self.find_potential_links(content, exclude_current_title=current_title)

        if not potential_links:
            return content

        print(f"  Found {len(potential_links)} potential fuzzy links to add")

        # Apply links in order of decreasing score to prioritize best matches
        modified_content = content

        for link_info in potential_links:
            phrase = link_info['phrase']
            title = link_info['title']
            subject_info = f" ({link_info['subject']})" if link_info['subject'] else ""

            # Create the Obsidian link
            obsidian_link = f"[[{title}]]"

            # Only replace if the phrase isn't already inside a link
            pattern = r'\b' + re.escape(phrase) + r'\b(?![^\[]*\]\])'

            # Replace the first occurrence only to avoid over-linking
            if re.search(pattern, modified_content):
                modified_content = re.sub(pattern, obsidian_link, modified_content, count=1)
                print(f"    Linked: '{phrase}' -> [[{title}]]{subject_info}")

        return modified_content

    def _extract_video_id_from_path(self, file_path):
        """Extract video ID from file path."""
        try:
            filename = os.path.basename(file_path)
            # Try to find a pattern that looks like a YouTube video ID (11 chars)
            match = re.search(r'([a-zA-Z0-9_-]{11})\.md$', filename)
            if match:
                return match.group(1)
        except Exception as e:
            logger.debug(f"Could not extract video ID from path: {e}")
        return None

    def _split_content_into_sections(self, content):
        """Split markdown content into sections based on ## headings."""
        sections = []

        # Pattern to match ## headings
        heading_pattern = re.compile(r'^## (.+)$', re.MULTILINE)
        matches = list(heading_pattern.finditer(content))

        if not matches:
            # No sections, return entire content as one section
            return [("Main Content", content)]

        # Process each section
        for i, match in enumerate(matches):
            section_title = match.group(1).strip()
            start_pos = match.end()

            # Find end of section (next ## heading or end of content)
            if i < len(matches) - 1:
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)

            section_text = content[start_pos:end_pos].strip()

            if section_text:
                sections.append((section_title, section_text))

        return sections

    def process_file(self, file_path):
        """Process a single file to add Obsidian links."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract current note title
            title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
            current_title = title_match.group(1).strip() if title_match else None

            # Apply links
            modified_content = self.apply_links(content, file_path, current_title)

            # Only write back if content was modified
            if modified_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                return True

        except Exception as e:
            print(f"Error processing {file_path} for Obsidian links: {e}")

        return False

    def get_stats(self):
        """Get statistics about available notes for linking."""
        if not self.note_titles:
            self.build_note_index()

        subjects = set()
        for data in self.note_titles.values():
            if data['subject']:
                subjects.add(data['subject'])

        return {
            'total_notes': len(self.note_titles),
            'subjects': list(subjects),
            'subject_count': len(subjects),
            'context': 'global' if self.global_context else f'subject: {self.subject}'
        }