#!/usr/bin/env python3
"""
Migrate existing notes to RAG vector store.

This script scans the notes directory for existing markdown files and indexes
them into the RAG vector store. It supports resume capability, batch processing,
and dry-run mode.

Usage:
    # Dry run (show what would be indexed)
    python scripts/migrate_notes_to_rag.py --dry-run

    # Index all notes
    python scripts/migrate_notes_to_rag.py

    # Index specific subject
    python scripts/migrate_notes_to_rag.py --subject AI

    # Resume from checkpoint
    python scripts/migrate_notes_to_rag.py --resume

    # Specify custom notes directory
    python scripts/migrate_notes_to_rag.py --notes-dir /path/to/notes
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm is not installed
    class tqdm:
        def __init__(self, iterable=None, total=None, desc=None, **kwargs):
            self.iterable = iterable
            self.total = total or (len(iterable) if iterable else 0)
            self.desc = desc
            self.n = 0

        def __iter__(self):
            for item in self.iterable:
                yield item
                self.update(1)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def update(self, n=1):
            self.n += n
            if self.desc:
                print(f"\r{self.desc}: {self.n}/{self.total}", end='', flush=True)

from yt_study_buddy.rag.config import load_config_from_env, RAGConfig
from yt_study_buddy.rag.vector_store import VectorStore
from yt_study_buddy.rag.embedding_service import EmbeddingService
from yt_study_buddy.rag.document_chunker import DocumentChunker
from yt_study_buddy.rag.pipeline_stage import RAGPipelineStage
from yt_study_buddy.rag.index_tracker import IndexTracker
from yt_study_buddy.rag.types import ProcessResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NoteMigrator:
    """Migrates existing notes to RAG vector store."""

    def __init__(
        self,
        config: RAGConfig,
        notes_dir: Path,
        checkpoint_file: Path,
        dry_run: bool = False
    ):
        """
        Initialize the migrator.

        Args:
            config: RAG configuration
            notes_dir: Directory containing notes
            checkpoint_file: File to store migration progress
            dry_run: If True, only show what would be done
        """
        self.config = config
        self.notes_dir = notes_dir
        self.checkpoint_file = checkpoint_file
        self.dry_run = dry_run

        # Initialize RAG components (unless dry run)
        self.pipeline_stage: Optional[RAGPipelineStage] = None
        if not dry_run:
            try:
                vector_store = VectorStore(
                    persist_dir=str(config.vector_store_dir),
                    collection_name=config.collection_name
                )
                embedding_service = EmbeddingService(
                    model_name=config.model_name,
                    cache_dir=str(config.model_cache_dir)
                )
                chunker = DocumentChunker(
                    chunk_size=config.chunk_size,
                    chunk_overlap=config.chunk_overlap,
                    min_chunk_size=config.min_chunk_size
                )
                index_tracker = IndexTracker(config.index_tracker_file)

                self.pipeline_stage = RAGPipelineStage(
                    config=config,
                    embedding_service=embedding_service,
                    vector_store=vector_store,
                    chunker=chunker,
                    index_tracker=index_tracker
                )

                logger.info("RAG components initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize RAG components: {e}")
                raise

    def scan_notes(self, subject_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scan notes directory for markdown files.

        Args:
            subject_filter: Optional subject to filter by (directory name)

        Returns:
            List of note information dictionaries
        """
        logger.info(f"Scanning notes directory: {self.notes_dir}")

        if not self.notes_dir.exists():
            logger.error(f"Notes directory does not exist: {self.notes_dir}")
            return []

        notes = []
        pattern = "**/*.md" if not subject_filter else f"{subject_filter}/**/*.md"

        for note_path in self.notes_dir.glob(pattern):
            if note_path.is_file():
                # Extract metadata from path
                relative_path = note_path.relative_to(self.notes_dir)
                parts = relative_path.parts

                # Subject is the top-level directory
                subject = parts[0] if len(parts) > 1 else "General"

                # Extract video title from filename (remove .md extension)
                video_title = note_path.stem

                # Generate a pseudo video ID from the file path
                video_id = f"note_{note_path.stem.lower().replace(' ', '_')}"

                notes.append({
                    'path': note_path,
                    'subject': subject,
                    'video_title': video_title,
                    'video_id': video_id,
                    'size': note_path.stat().st_size,
                    'modified': datetime.fromtimestamp(note_path.stat().st_mtime)
                })

        logger.info(f"Found {len(notes)} notes")
        return notes

    def filter_unindexed(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out already-indexed notes.

        Args:
            notes: List of note information dictionaries

        Returns:
            List of unindexed notes
        """
        if self.dry_run or not self.pipeline_stage:
            return notes

        unindexed = []
        for note in notes:
            if not self.pipeline_stage.is_note_indexed(note['video_id']):
                unindexed.append(note)
            elif self.pipeline_stage.index_tracker.needs_reindex(
                note['video_id'],
                note['path']
            ):
                logger.info(f"Note needs re-indexing: {note['path']}")
                unindexed.append(note)

        logger.info(f"{len(unindexed)} notes need indexing (out of {len(notes)} total)")
        return unindexed

    def load_checkpoint(self) -> Dict[str, Any]:
        """
        Load migration checkpoint if it exists.

        Returns:
            Checkpoint data or empty dict
        """
        if not self.checkpoint_file.exists():
            return {}

        try:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                logger.info(f"Loaded checkpoint: {checkpoint.get('processed', 0)} notes processed")
                return checkpoint
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return {}

    def save_checkpoint(self, processed: List[str], failed: List[str]):
        """
        Save migration progress checkpoint.

        Args:
            processed: List of successfully processed note paths
            failed: List of failed note paths
        """
        checkpoint = {
            'timestamp': datetime.utcnow().isoformat(),
            'processed': len(processed),
            'failed': len(failed),
            'processed_paths': processed,
            'failed_paths': failed
        }

        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            logger.debug(f"Saved checkpoint: {len(processed)} processed")
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")

    def migrate_batch(
        self,
        notes: List[Dict[str, Any]],
        batch_size: int,
        resume: bool = False
    ) -> Dict[str, Any]:
        """
        Migrate notes in batches.

        Args:
            notes: List of notes to migrate
            batch_size: Number of notes to process in each batch
            resume: If True, skip already processed notes

        Returns:
            Migration statistics
        """
        start_time = time.time()
        processed = []
        failed = []
        skipped = []

        # Load checkpoint if resuming
        checkpoint = self.load_checkpoint() if resume else {}
        processed_paths = set(checkpoint.get('processed_paths', []))

        # Filter out already processed if resuming
        if resume and processed_paths:
            notes = [n for n in notes if str(n['path']) not in processed_paths]
            skipped = list(processed_paths)
            logger.info(f"Resuming: skipping {len(skipped)} already processed notes")

        if not notes:
            logger.info("No notes to process")
            return {
                'total': len(skipped),
                'processed': len(skipped),
                'failed': 0,
                'skipped': len(skipped),
                'time_seconds': 0.0
            }

        # Process notes with progress bar
        with tqdm(total=len(notes), desc="Migrating notes") as pbar:
            for i in range(0, len(notes), batch_size):
                batch = notes[i:i + batch_size]

                for note in batch:
                    note_path = note['path']
                    pbar.set_description(f"Processing {note['video_title'][:40]}...")

                    if self.dry_run:
                        logger.info(f"[DRY RUN] Would index: {note_path}")
                        processed.append(str(note_path))
                        pbar.update(1)
                        continue

                    try:
                        # Process note through pipeline
                        result = self.pipeline_stage.process_note(
                            note_path=note_path,
                            video_metadata={
                                'video_id': note['video_id'],
                                'title': note['video_title'],
                                'subject': note['subject']
                            }
                        )

                        if result.success:
                            processed.append(str(note_path))
                            logger.debug(
                                f"Indexed {note['video_title']}: "
                                f"{result.chunks_created} chunks, "
                                f"{result.embeddings_generated} embeddings"
                            )
                        else:
                            failed.append(str(note_path))
                            logger.warning(
                                f"Failed to index {note['video_title']}: "
                                f"{result.error_message}"
                            )
                    except Exception as e:
                        failed.append(str(note_path))
                        logger.error(f"Error processing {note_path}: {e}")

                    pbar.update(1)

                # Save checkpoint after each batch
                if not self.dry_run:
                    self.save_checkpoint(processed + list(skipped), failed)

        elapsed = time.time() - start_time

        return {
            'total': len(notes) + len(skipped),
            'processed': len(processed),
            'failed': len(failed),
            'skipped': len(skipped),
            'time_seconds': elapsed
        }


def print_statistics(stats: Dict[str, Any]):
    """Print migration statistics."""
    print("\n" + "="*60)
    print("Migration Statistics")
    print("="*60)
    print(f"Total notes:      {stats['total']}")
    print(f"Processed:        {stats['processed']}")
    print(f"Failed:           {stats['failed']}")
    print(f"Skipped:          {stats['skipped']}")
    print(f"Time elapsed:     {stats['time_seconds']:.2f} seconds")
    if stats['processed'] > 0:
        print(f"Average time:     {stats['time_seconds'] / stats['processed']:.2f} sec/note")
    print("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate existing notes to RAG vector store"
    )
    parser.add_argument(
        '--notes-dir',
        type=Path,
        default=Path('test_notes'),
        help='Directory containing notes (default: test_notes)'
    )
    parser.add_argument(
        '--subject',
        type=str,
        help='Filter by subject (directory name)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of notes to process in each batch (default: 10)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually indexing'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint'
    )
    parser.add_argument(
        '--checkpoint-file',
        type=Path,
        default=Path('.migration_checkpoint.json'),
        help='Checkpoint file location (default: .migration_checkpoint.json)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load RAG configuration
    try:
        config = load_config_from_env()
        if not config.enabled:
            logger.warning("RAG is disabled in configuration")
            if not args.dry_run:
                print("ERROR: RAG is disabled. Set RAG_ENABLED=true to enable.")
                return 1
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1

    # Validate notes directory
    if not args.notes_dir.exists():
        logger.error(f"Notes directory does not exist: {args.notes_dir}")
        return 1

    # Print configuration
    print("\n" + "="*60)
    print("RAG Migration Tool")
    print("="*60)
    print(f"Notes directory:  {args.notes_dir}")
    print(f"Subject filter:   {args.subject or 'None (all subjects)'}")
    print(f"Batch size:       {args.batch_size}")
    print(f"Dry run:          {args.dry_run}")
    print(f"Resume:           {args.resume}")
    print(f"Vector store:     {config.vector_store_dir}")
    print(f"Model:            {config.model_name}")
    print("="*60 + "\n")

    try:
        # Create migrator
        migrator = NoteMigrator(
            config=config,
            notes_dir=args.notes_dir,
            checkpoint_file=args.checkpoint_file,
            dry_run=args.dry_run
        )

        # Scan for notes
        notes = migrator.scan_notes(subject_filter=args.subject)
        if not notes:
            print("No notes found to migrate.")
            return 0

        # Filter unindexed
        unindexed = migrator.filter_unindexed(notes)
        if not unindexed:
            print("All notes are already indexed!")
            return 0

        # Confirm migration
        if not args.dry_run:
            print(f"\nReady to index {len(unindexed)} notes.")
            response = input("Continue? [y/N]: ")
            if response.lower() not in ('y', 'yes'):
                print("Aborted.")
                return 0

        # Migrate notes
        stats = migrator.migrate_batch(
            notes=unindexed,
            batch_size=args.batch_size,
            resume=args.resume
        )

        # Print results
        print_statistics(stats)

        if stats['failed'] > 0:
            logger.warning(f"{stats['failed']} notes failed to index")
            return 1

        if args.dry_run:
            print("\nDry run complete. Use without --dry-run to actually index notes.")
        else:
            print("\nMigration complete!")

        return 0

    except KeyboardInterrupt:
        print("\n\nMigration interrupted. Progress saved to checkpoint.")
        return 130
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
