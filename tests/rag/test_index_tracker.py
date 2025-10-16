"""
Unit tests for IndexTracker module.

Tests index tracking, modification detection, and persistence.
"""

import json
import tempfile
import time
from pathlib import Path
import pytest

from src.yt_study_buddy.rag.index_tracker import IndexTracker


@pytest.fixture
def temp_tracker_file():
    """Create a temporary tracker file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_note_file():
    """Create a temporary note file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Note\n\nSome content here.")
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


class TestIndexTrackerInit:
    """Test IndexTracker initialization."""

    def test_init_creates_new_tracker(self, temp_tracker_file):
        """Test creating a new tracker."""
        tracker = IndexTracker(temp_tracker_file)
        assert tracker.tracker_file == temp_tracker_file
        assert len(tracker.get_indexed_videos()) == 0

    def test_init_loads_existing_tracker(self, temp_tracker_file):
        """Test loading an existing tracker file."""
        # Create existing tracker data
        initial_data = {
            'test_video_1': {
                'video_id': 'test_video_1',
                'note_path': '/path/to/note.md',
                'indexed_at': '2025-01-01T00:00:00',
                'file_mtime': 1234567890.0,
                'chunks_created': 5,
            }
        }
        temp_tracker_file.write_text(json.dumps(initial_data))

        # Load tracker
        tracker = IndexTracker(temp_tracker_file)
        assert 'test_video_1' in tracker.get_indexed_videos()
        entry = tracker.get_entry('test_video_1')
        assert entry['chunks_created'] == 5


class TestIndexTrackerMarking:
    """Test marking notes as indexed."""

    def test_mark_indexed(self, temp_tracker_file, temp_note_file):
        """Test marking a note as indexed."""
        tracker = IndexTracker(temp_tracker_file)

        tracker.mark_indexed(
            video_id='test_video',
            note_path=temp_note_file,
            chunks_created=3,
        )

        assert tracker.is_indexed('test_video')
        entry = tracker.get_entry('test_video')
        assert entry['chunks_created'] == 3
        assert entry['file_mtime'] is not None

    def test_mark_indexed_with_metadata(self, temp_tracker_file, temp_note_file):
        """Test marking with additional metadata."""
        tracker = IndexTracker(temp_tracker_file)

        metadata = {'video_title': 'Test Video', 'subject': 'AI'}
        tracker.mark_indexed(
            video_id='test_video',
            note_path=temp_note_file,
            chunks_created=5,
            metadata=metadata,
        )

        entry = tracker.get_entry('test_video')
        assert entry['metadata']['video_title'] == 'Test Video'
        assert entry['metadata']['subject'] == 'AI'

    def test_mark_indexed_updates_existing(self, temp_tracker_file, temp_note_file):
        """Test that marking updates existing entries."""
        tracker = IndexTracker(temp_tracker_file)

        # First indexing
        tracker.mark_indexed('test_video', temp_note_file, chunks_created=3)
        entry1 = tracker.get_entry('test_video')

        time.sleep(0.1)

        # Re-index
        tracker.mark_indexed('test_video', temp_note_file, chunks_created=5)
        entry2 = tracker.get_entry('test_video')

        assert entry2['chunks_created'] == 5
        assert entry2['indexed_at'] > entry1['indexed_at']


class TestIndexTrackerQuerying:
    """Test querying index status."""

    def test_is_indexed_simple(self, temp_tracker_file, temp_note_file):
        """Test simple indexed check."""
        tracker = IndexTracker(temp_tracker_file)

        assert not tracker.is_indexed('test_video')
        tracker.mark_indexed('test_video', temp_note_file)
        assert tracker.is_indexed('test_video')

    def test_is_indexed_with_path(self, temp_tracker_file, temp_note_file):
        """Test indexed check with path verification."""
        tracker = IndexTracker(temp_tracker_file)

        tracker.mark_indexed('test_video', temp_note_file)
        assert tracker.is_indexed('test_video', temp_note_file)

    def test_needs_reindex_not_indexed(self, temp_tracker_file, temp_note_file):
        """Test needs_reindex for unindexed note."""
        tracker = IndexTracker(temp_tracker_file)
        assert tracker.needs_reindex('test_video', temp_note_file)

    def test_needs_reindex_modified_file(self, temp_tracker_file, temp_note_file):
        """Test needs_reindex detects file modification."""
        tracker = IndexTracker(temp_tracker_file)

        # Index the note
        tracker.mark_indexed('test_video', temp_note_file)
        assert not tracker.needs_reindex('test_video', temp_note_file)

        # Modify the file
        time.sleep(0.1)  # Ensure mtime changes
        temp_note_file.write_text("# Modified Content\n\nNew content.")

        # Should need reindexing
        assert tracker.needs_reindex('test_video', temp_note_file)

    def test_needs_reindex_no_mtime(self, temp_tracker_file, temp_note_file):
        """Test needs_reindex when stored mtime is None."""
        tracker = IndexTracker(temp_tracker_file)

        # Manually create entry without mtime
        tracker._index['test_video'] = {
            'video_id': 'test_video',
            'note_path': str(temp_note_file),
            'file_mtime': None,
        }

        # Should need reindexing
        assert tracker.needs_reindex('test_video', temp_note_file)


class TestIndexTrackerMaintenance:
    """Test maintenance operations."""

    def test_remove_entry(self, temp_tracker_file, temp_note_file):
        """Test removing an entry."""
        tracker = IndexTracker(temp_tracker_file)

        tracker.mark_indexed('test_video', temp_note_file)
        assert tracker.is_indexed('test_video')

        result = tracker.remove_entry('test_video')
        assert result is True
        assert not tracker.is_indexed('test_video')

    def test_remove_nonexistent_entry(self, temp_tracker_file):
        """Test removing a non-existent entry."""
        tracker = IndexTracker(temp_tracker_file)
        result = tracker.remove_entry('nonexistent')
        assert result is False

    def test_clear(self, temp_tracker_file, temp_note_file):
        """Test clearing all entries."""
        tracker = IndexTracker(temp_tracker_file)

        tracker.mark_indexed('video1', temp_note_file)
        tracker.mark_indexed('video2', temp_note_file)
        assert len(tracker.get_indexed_videos()) == 2

        tracker.clear()
        assert len(tracker.get_indexed_videos()) == 0

    def test_get_stats(self, temp_tracker_file, temp_note_file):
        """Test getting statistics."""
        tracker = IndexTracker(temp_tracker_file)

        tracker.mark_indexed('video1', temp_note_file, chunks_created=3)
        tracker.mark_indexed('video2', temp_note_file, chunks_created=5)

        stats = tracker.get_stats()
        assert stats['total_videos_indexed'] == 2
        assert stats['total_chunks_created'] == 8
        assert stats['tracker_file'] == str(temp_tracker_file)


class TestIndexTrackerPersistence:
    """Test persistence and file operations."""

    def test_persistence(self, temp_tracker_file, temp_note_file):
        """Test that changes are persisted across instances."""
        # Create and populate tracker
        tracker1 = IndexTracker(temp_tracker_file)
        tracker1.mark_indexed('test_video', temp_note_file, chunks_created=5)

        # Create new instance (should load from file)
        tracker2 = IndexTracker(temp_tracker_file)
        assert tracker2.is_indexed('test_video')
        entry = tracker2.get_entry('test_video')
        assert entry['chunks_created'] == 5

    def test_atomic_save(self, temp_tracker_file, temp_note_file):
        """Test that saves are atomic (no corruption)."""
        tracker = IndexTracker(temp_tracker_file)
        tracker.mark_indexed('test_video', temp_note_file)

        # File should exist and be valid JSON
        assert temp_tracker_file.exists()
        data = json.loads(temp_tracker_file.read_text())
        assert 'test_video' in data


class TestIndexTrackerUnindexedNotes:
    """Test finding unindexed notes."""

    def test_get_unindexed_notes_empty_dir(self, temp_tracker_file):
        """Test with non-existent directory."""
        tracker = IndexTracker(temp_tracker_file)
        notes = tracker.get_unindexed_notes(Path('/nonexistent'))
        assert notes == []

    def test_get_unindexed_notes(self, temp_tracker_file):
        """Test finding unindexed notes in a directory."""
        tracker = IndexTracker(temp_tracker_file)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create some notes
            note1 = tmpdir / "note1.md"
            note2 = tmpdir / "note2.md"
            note3 = tmpdir / "Assessment_note3.md"  # Should be filtered

            note1.write_text("# Note 1")
            note2.write_text("# Note 2")
            note3.write_text("# Assessment")

            # Index note1
            tracker.mark_indexed('video1', note1)

            # Get unindexed notes
            unindexed = tracker.get_unindexed_notes(tmpdir)

            # Should only find note2 (note3 is filtered, note1 is indexed)
            assert len(unindexed) == 1
            assert note2 in unindexed
