"""
Index tracking module for RAG pipeline.

Tracks which notes have been indexed and their modification times to support
incremental indexing and avoid redundant work.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class IndexTracker:
    """
    Tracks indexed notes and their modification times.

    Stores metadata in a JSON file to persist across sessions.
    Supports incremental indexing by detecting modified files.
    """

    def __init__(self, tracker_file: Path):
        """
        Initialize index tracker.

        Args:
            tracker_file: Path to JSON file for storing tracking data
        """
        self.tracker_file = Path(tracker_file)
        self._index: Dict[str, Dict] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load index from JSON file."""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, 'r', encoding='utf-8') as f:
                    self._index = json.load(f)
                logger.debug(f"Loaded index tracker: {len(self._index)} entries")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load index tracker: {e}. Starting fresh.")
                self._index = {}
        else:
            logger.debug("Index tracker file does not exist. Starting fresh.")
            self._index = {}

    def _save_index(self) -> None:
        """Save index to JSON file."""
        try:
            # Ensure parent directory exists
            self.tracker_file.parent.mkdir(parents=True, exist_ok=True)

            # Write atomically (write to temp file, then rename)
            temp_file = self.tracker_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._index, f, indent=2)

            # Atomic rename
            temp_file.replace(self.tracker_file)
            logger.debug(f"Saved index tracker: {len(self._index)} entries")
        except IOError as e:
            logger.error(f"Failed to save index tracker: {e}")

    def mark_indexed(
        self,
        video_id: str,
        note_path: Path,
        chunks_created: int = 0,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Mark a note as indexed.

        Args:
            video_id: Video identifier
            note_path: Path to the note file
            chunks_created: Number of chunks created from this note
            metadata: Optional additional metadata to store
        """
        note_path = Path(note_path)

        # Get file modification time
        if note_path.exists():
            mtime = note_path.stat().st_mtime
        else:
            logger.warning(f"Note file does not exist: {note_path}")
            mtime = None

        # Create index entry
        entry = {
            'video_id': video_id,
            'note_path': str(note_path),
            'indexed_at': datetime.utcnow().isoformat(),
            'file_mtime': mtime,
            'chunks_created': chunks_created,
        }

        # Add optional metadata
        if metadata:
            entry['metadata'] = metadata

        # Store and save
        self._index[video_id] = entry
        self._save_index()

        logger.info(f"Marked {video_id} as indexed ({chunks_created} chunks)")

    def is_indexed(self, video_id: str, note_path: Optional[Path] = None) -> bool:
        """
        Check if a note has been indexed.

        Args:
            video_id: Video identifier
            note_path: Optional path to check (if provided, checks mtime)

        Returns:
            True if indexed and up-to-date
        """
        if video_id not in self._index:
            return False

        # If no path provided, just check existence
        if note_path is None:
            return True

        # Check if file has been modified since indexing
        return not self.needs_reindex(video_id, note_path)

    def needs_reindex(self, video_id: str, note_path: Path) -> bool:
        """
        Check if a note needs re-indexing.

        A note needs re-indexing if:
        - It's not in the index
        - The file has been modified since last indexing
        - The file doesn't exist but is in index (stale entry)

        Args:
            video_id: Video identifier
            note_path: Path to the note file

        Returns:
            True if note needs (re)indexing
        """
        note_path = Path(note_path)

        # Not indexed yet
        if video_id not in self._index:
            return True

        entry = self._index[video_id]
        stored_mtime = entry.get('file_mtime')

        # No mtime stored (old index format)
        if stored_mtime is None:
            return True

        # File doesn't exist anymore (stale entry)
        if not note_path.exists():
            logger.warning(f"Note file missing: {note_path}")
            return False  # Don't reindex missing files

        # Check if file has been modified
        current_mtime = note_path.stat().st_mtime
        if current_mtime > stored_mtime:
            logger.debug(f"Note modified since indexing: {video_id}")
            return True

        return False

    def get_unindexed_notes(self, notes_dir: Path) -> List[Path]:
        """
        Find all unindexed markdown files in a directory.

        Args:
            notes_dir: Directory containing markdown notes

        Returns:
            List of paths to unindexed notes
        """
        notes_dir = Path(notes_dir)
        if not notes_dir.exists():
            logger.warning(f"Notes directory does not exist: {notes_dir}")
            return []

        # Get all markdown files
        all_notes = list(notes_dir.glob("**/*.md"))

        # Filter out assessments (Assessment_*.md)
        note_files = [
            p for p in all_notes
            if not p.name.startswith("Assessment_")
        ]

        # Find unindexed notes
        unindexed = []
        for note_path in note_files:
            # Try to extract video_id from filename or content
            # For now, just check if any indexed entry points to this path
            is_indexed = any(
                Path(entry['note_path']) == note_path
                and not self.needs_reindex(vid, note_path)
                for vid, entry in self._index.items()
            )

            if not is_indexed:
                unindexed.append(note_path)

        logger.info(f"Found {len(unindexed)} unindexed notes out of {len(note_files)} total")
        return unindexed

    def get_indexed_videos(self) -> Set[str]:
        """
        Get set of all indexed video IDs.

        Returns:
            Set of video IDs
        """
        return set(self._index.keys())

    def remove_entry(self, video_id: str) -> bool:
        """
        Remove an index entry.

        Args:
            video_id: Video identifier

        Returns:
            True if entry was removed
        """
        if video_id in self._index:
            del self._index[video_id]
            self._save_index()
            logger.info(f"Removed index entry: {video_id}")
            return True
        return False

    def get_entry(self, video_id: str) -> Optional[Dict]:
        """
        Get index entry for a video.

        Args:
            video_id: Video identifier

        Returns:
            Index entry dict or None if not found
        """
        return self._index.get(video_id)

    def get_stats(self) -> Dict:
        """
        Get statistics about the index.

        Returns:
            Dictionary with statistics
        """
        total_entries = len(self._index)
        total_chunks = sum(
            entry.get('chunks_created', 0)
            for entry in self._index.values()
        )

        return {
            'total_videos_indexed': total_entries,
            'total_chunks_created': total_chunks,
            'tracker_file': str(self.tracker_file),
            'tracker_exists': self.tracker_file.exists(),
        }

    def clear(self) -> None:
        """Clear all index entries."""
        self._index = {}
        self._save_index()
        logger.info("Cleared all index entries")
