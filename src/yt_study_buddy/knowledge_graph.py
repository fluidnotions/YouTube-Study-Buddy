"""
Knowledge graph for managing concept indexing and cross-references between study notes.
"""
import os
import re


class KnowledgeGraph:
    """Manages concept extraction and relationship finding between study notes."""

    def __init__(self, base_dir="notes", subject=None, global_context=True):
        self.base_dir = base_dir
        self.subject = subject
        self.global_context = global_context
        self.subject_dir = os.path.join(base_dir, subject) if subject else base_dir
        self._concepts_cache = None
        self._global_cache = None

    def extract_concepts_from_notes(self, force_refresh=False, global_scope=None):
        """Extract key concepts and topics from existing markdown files."""
        # Determine scope - use parameter if provided, otherwise use instance setting
        use_global = global_scope if global_scope is not None else self.global_context

        # Use appropriate cache
        cache_key = '_global_cache' if use_global else '_concepts_cache'
        if getattr(self, cache_key) is not None and not force_refresh:
            return getattr(self, cache_key)

        concepts_index = {}

        # Determine directories to scan
        dirs_to_scan = []
        if use_global and os.path.exists(self.base_dir):
            # Scan all subjects for global context
            for item in os.listdir(self.base_dir):
                item_path = os.path.join(self.base_dir, item)
                if os.path.isdir(item_path):
                    dirs_to_scan.append((item_path, item))  # (path, subject)
            # Also scan base directory for any loose files
            dirs_to_scan.append((self.base_dir, None))
        else:
            # Subject-specific context
            if os.path.exists(self.subject_dir):
                dirs_to_scan.append((self.subject_dir, self.subject))

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
                    if not title_match:
                        continue

                    title = title_match.group(1).strip()
                    concepts = self._extract_concepts_from_content(content)

                    if concepts:
                        concepts_index[title] = {
                            'filename': filename,
                            'subject': subject_name,
                            'path': filepath,
                            'concepts': list(concepts)[:10]  # Limit to top 10 concepts
                        }

                except Exception as e:
                    print(f"Warning: Could not process {filename}: {e}")
                    continue

        # Cache the results
        setattr(self, cache_key, concepts_index)
        return concepts_index

    def _extract_concepts_from_content(self, content):
        """Extract concepts from markdown content."""
        concepts = set()

        # Look for Core Concepts section
        core_concepts_match = re.search(r'## Core Concepts\n(.*?)(?=\n##|\n---|\Z)', content, re.DOTALL)
        if core_concepts_match:
            concepts.update(self._extract_from_section(core_concepts_match.group(1)))

        # Look for Definitions & Terminology
        defs_match = re.search(r'## Definitions & Terminology\n(.*?)(?=\n##|\n---|\Z)', content, re.DOTALL)
        if defs_match:
            concepts.update(self._extract_definitions(defs_match.group(1)))

        # Look for Key Points section for additional concepts
        key_points_match = re.search(r'## Key Points\n(.*?)(?=\n##|\n---|\Z)', content, re.DOTALL)
        if key_points_match:
            concepts.update(self._extract_key_phrases(key_points_match.group(1)))

        return concepts

    def _extract_from_section(self, section_text):
        """Extract concepts from a general section (bullet points, numbered items)."""
        concepts = set()
        # Extract bullet points and numbered items
        concept_lines = re.findall(r'[-*•]\s*(.+?)(?=\n|$)', section_text)
        concept_lines.extend(re.findall(r'\d+\.\s*(.+?)(?=\n|$)', section_text))

        for line in concept_lines:
            # Take first few words as concept
            concept = ' '.join(line.split()[:4]).rstrip(':.-,')
            if len(concept) > 5:
                concepts.add(concept.lower())

        return concepts

    def _extract_definitions(self, defs_text):
        """Extract defined terms from definitions section."""
        concepts = set()
        # Extract defined terms (usually in bold or as list items)
        terms = re.findall(r'\*\*([^*]+)\*\*', defs_text)
        terms.extend(re.findall(r'[-*•]\s*([^:]+):', defs_text))

        for term in terms:
            clean_term = term.strip().lower()
            if len(clean_term) > 2:
                concepts.add(clean_term)

        return concepts

    def _extract_key_phrases(self, key_text):
        """Extract important phrases from key points section."""
        concepts = set()
        # Extract important phrases (capitalized words, technical terms)
        important_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', key_text)

        for phrase in important_phrases:
            if len(phrase) > 3 and phrase.lower() not in ['The', 'This', 'That', 'With', 'From']:
                concepts.add(phrase.lower())

        return concepts

    def find_related_notes(self, current_transcript, global_scope=None):
        """Find notes related to the current transcript."""
        use_global = global_scope if global_scope is not None else self.global_context
        concepts_index = self.extract_concepts_from_notes(global_scope=use_global)

        if not concepts_index:
            return []

        # Extract key terms from current transcript
        transcript_lower = current_transcript.lower()
        related_notes = []

        for title, note_data in concepts_index.items():
            relevance_score = 0
            matching_concepts = []

            # Check how many concepts from existing notes appear in current transcript
            for concept in note_data['concepts']:
                if concept in transcript_lower:
                    relevance_score += 1
                    matching_concepts.append(concept)

            # If we found matches, this note is related
            if relevance_score > 0:
                related_notes.append({
                    'title': title,
                    'filename': note_data['filename'],
                    'subject': note_data.get('subject'),
                    'relevance_score': relevance_score,
                    'matching_concepts': matching_concepts[:3]  # Top 3 matches
                })

        # Sort by relevance and return top 5
        related_notes.sort(key=lambda x: x['relevance_score'], reverse=True)
        return related_notes[:5]

    def refresh_cache(self):
        """Force refresh both concept caches."""
        self._concepts_cache = None
        self._global_cache = None
        return self.extract_concepts_from_notes(force_refresh=True)

    def get_stats(self, global_scope=None):
        """Get statistics about the knowledge graph."""
        use_global = global_scope if global_scope is not None else self.global_context
        concepts_index = self.extract_concepts_from_notes(global_scope=use_global)

        total_notes = len(concepts_index)
        total_concepts = sum(len(data['concepts']) for data in concepts_index.values())

        # Count subjects if in global mode
        subjects = set()
        for data in concepts_index.values():
            if data.get('subject'):
                subjects.add(data['subject'])

        stats = {
            'total_notes': total_notes,
            'total_concepts': total_concepts,
            'avg_concepts_per_note': round(total_concepts / total_notes, 2) if total_notes > 0 else 0,
            'scope': 'global' if use_global else f'subject: {self.subject}'
        }

        if use_global and subjects:
            stats['subjects'] = list(subjects)
            stats['subject_count'] = len(subjects)

        return stats