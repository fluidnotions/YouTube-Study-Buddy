#!/usr/bin/env python3
"""
Vector store maintenance script.

This script provides maintenance operations for the RAG vector store including
rebuild, cleanup, backup/restore, and health diagnostics.

Usage:
    # Rebuild from scratch
    python scripts/maintain_vector_store.py --rebuild

    # Clean stale entries (deleted notes)
    python scripts/maintain_vector_store.py --clean

    # Export for backup
    python scripts/maintain_vector_store.py --export backup.json

    # Import from backup
    python scripts/maintain_vector_store.py --import backup.json

    # Health diagnostics
    python scripts/maintain_vector_store.py --diagnose

    # Show collection statistics
    python scripts/maintain_vector_store.py --stats
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm is not installed
    class tqdm:
        def __init__(self, iterable=None, total=None, desc=None, **kwargs):
            self.iterable = iterable or []
            self.total = total or len(self.iterable)

        def __iter__(self):
            for item in self.iterable:
                yield item

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def update(self, n=1):
            pass

from yt_study_buddy.rag.config import load_config_from_env, RAGConfig
from yt_study_buddy.rag.vector_store import VectorStore
from yt_study_buddy.rag.embedding_service import EmbeddingService
from yt_study_buddy.rag.document_chunker import DocumentChunker
from yt_study_buddy.rag.index_tracker import IndexTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VectorStoreMaintenance:
    """Handles vector store maintenance operations."""

    def __init__(self, config: RAGConfig, notes_dir: Path):
        """
        Initialize maintenance handler.

        Args:
            config: RAG configuration
            notes_dir: Directory containing notes
        """
        self.config = config
        self.notes_dir = notes_dir

        # Initialize components
        try:
            self.vector_store = VectorStore(
                persist_dir=str(config.vector_store_dir),
                collection_name=config.collection_name
            )
            self.embedding_service = EmbeddingService(
                model_name=config.model_name,
                cache_dir=str(config.model_cache_dir)
            )
            self.chunker = DocumentChunker(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                min_chunk_size=config.min_chunk_size
            )
            self.index_tracker = IndexTracker(config.index_tracker_file)

            logger.info("Vector store components initialized")

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get vector store statistics.

        Returns:
            Statistics dictionary
        """
        try:
            stats = self.vector_store.collection_stats()

            # Additional stats from index tracker
            tracker_stats = self.index_tracker.get_stats()

            return {
                'collection': stats,
                'index_tracker': tracker_stats,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}

    def diagnose(self) -> Dict[str, Any]:
        """
        Run health diagnostics.

        Returns:
            Diagnostic results
        """
        logger.info("Running health diagnostics...")

        diagnostics = {
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }

        # Check 1: Vector store health
        try:
            health = self.vector_store.health_check()
            diagnostics['checks']['vector_store_health'] = {
                'status': 'pass' if health else 'fail',
                'healthy': health
            }
        except Exception as e:
            diagnostics['checks']['vector_store_health'] = {
                'status': 'error',
                'error': str(e)
            }

        # Check 2: Collection exists and has data
        try:
            stats = self.vector_store.collection_stats()
            count = stats.get('count', 0)
            diagnostics['checks']['collection_data'] = {
                'status': 'pass' if count > 0 else 'warn',
                'count': count,
                'message': 'OK' if count > 0 else 'Collection is empty'
            }
        except Exception as e:
            diagnostics['checks']['collection_data'] = {
                'status': 'error',
                'error': str(e)
            }

        # Check 3: Embedding service
        try:
            test_embedding = self.embedding_service.embed_text("test")
            dim = len(test_embedding)
            expected_dim = self.embedding_service.get_embedding_dim()
            diagnostics['checks']['embedding_service'] = {
                'status': 'pass' if dim == expected_dim else 'warn',
                'dimension': dim,
                'expected_dimension': expected_dim
            }
        except Exception as e:
            diagnostics['checks']['embedding_service'] = {
                'status': 'error',
                'error': str(e)
            }

        # Check 4: Index tracker
        try:
            tracker_stats = self.index_tracker.get_stats()
            diagnostics['checks']['index_tracker'] = {
                'status': 'pass',
                'indexed_count': tracker_stats.get('indexed_count', 0)
            }
        except Exception as e:
            diagnostics['checks']['index_tracker'] = {
                'status': 'error',
                'error': str(e)
            }

        # Check 5: Persist directory
        persist_dir = Path(self.config.vector_store_dir)
        diagnostics['checks']['persist_directory'] = {
            'status': 'pass' if persist_dir.exists() else 'fail',
            'path': str(persist_dir),
            'exists': persist_dir.exists(),
            'writable': persist_dir.exists() and persist_dir.stat().st_mode & 0o200
        }

        # Check 6: Model cache
        cache_dir = Path(self.config.model_cache_dir)
        diagnostics['checks']['model_cache'] = {
            'status': 'pass' if cache_dir.exists() else 'warn',
            'path': str(cache_dir),
            'exists': cache_dir.exists()
        }

        # Overall status
        statuses = [check['status'] for check in diagnostics['checks'].values()]
        if 'error' in statuses or 'fail' in statuses:
            diagnostics['overall_status'] = 'unhealthy'
        elif 'warn' in statuses:
            diagnostics['overall_status'] = 'degraded'
        else:
            diagnostics['overall_status'] = 'healthy'

        return diagnostics

    def clean_stale_entries(self, notes_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Remove entries for deleted notes.

        Args:
            notes_dir: Directory to check for existing notes

        Returns:
            Cleanup statistics
        """
        logger.info("Cleaning stale entries...")

        notes_dir = notes_dir or self.notes_dir
        if not notes_dir.exists():
            logger.warning(f"Notes directory does not exist: {notes_dir}")
            return {'removed': 0, 'error': 'Notes directory not found'}

        # Get all video IDs from vector store
        try:
            stats = self.vector_store.collection_stats()
            logger.info(f"Vector store contains {stats.get('count', 0)} chunks")
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {'removed': 0, 'error': str(e)}

        # Get all existing note files
        existing_notes = set()
        for note_path in notes_dir.glob("**/*.md"):
            video_id = f"note_{note_path.stem.lower().replace(' ', '_')}"
            existing_notes.add(video_id)

        logger.info(f"Found {len(existing_notes)} existing notes")

        # Get all indexed video IDs
        indexed_ids = set(self.index_tracker.get_all_video_ids())
        logger.info(f"Index tracker has {len(indexed_ids)} entries")

        # Find stale entries
        stale_ids = indexed_ids - existing_notes
        logger.info(f"Found {len(stale_ids)} stale entries")

        # Remove stale entries
        removed = 0
        failed = 0

        for video_id in tqdm(stale_ids, desc="Removing stale entries"):
            try:
                # Remove from vector store
                success = self.vector_store.delete_by_video_id(video_id)
                if success:
                    # Remove from index tracker
                    self.index_tracker.remove_entry(video_id)
                    removed += 1
                else:
                    failed += 1
                    logger.warning(f"Failed to remove {video_id}")
            except Exception as e:
                failed += 1
                logger.error(f"Error removing {video_id}: {e}")

        return {
            'total_indexed': len(indexed_ids),
            'existing_notes': len(existing_notes),
            'stale_found': len(stale_ids),
            'removed': removed,
            'failed': failed
        }

    def rebuild(self, notes_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Rebuild entire vector store from scratch.

        Args:
            notes_dir: Directory containing notes

        Returns:
            Rebuild statistics
        """
        logger.warning("Rebuilding vector store from scratch...")

        notes_dir = notes_dir or self.notes_dir

        # Confirm rebuild
        print("\nWARNING: This will delete all existing embeddings and rebuild from scratch.")
        response = input("Are you sure? Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("Aborted.")
            return {'status': 'aborted'}

        start_time = time.time()

        # Clear vector store
        try:
            logger.info("Clearing vector store...")
            # Delete and recreate collection
            self.vector_store.clear_collection()
            logger.info("Vector store cleared")
        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            return {'status': 'error', 'error': str(e)}

        # Clear index tracker
        try:
            logger.info("Clearing index tracker...")
            self.index_tracker.clear()
            logger.info("Index tracker cleared")
        except Exception as e:
            logger.error(f"Failed to clear index tracker: {e}")

        # Re-run migration
        logger.info("Starting re-indexing...")
        print("\nPlease run the migration script to re-index notes:")
        print(f"  python scripts/migrate_notes_to_rag.py --notes-dir {notes_dir}")

        elapsed = time.time() - start_time

        return {
            'status': 'cleared',
            'message': 'Vector store cleared. Run migration script to re-index.',
            'time_seconds': elapsed
        }

    def export_data(self, output_file: Path) -> Dict[str, Any]:
        """
        Export vector store data to JSON file.

        Args:
            output_file: Output file path

        Returns:
            Export statistics
        """
        logger.info(f"Exporting data to {output_file}...")

        try:
            # Get all data from vector store
            data = self.vector_store.export_collection()

            # Get index tracker data
            tracker_data = self.index_tracker.export_data()

            # Combine into export package
            export_package = {
                'timestamp': datetime.utcnow().isoformat(),
                'config': {
                    'model_name': self.config.model_name,
                    'collection_name': self.config.collection_name,
                    'similarity_threshold': self.config.similarity_threshold
                },
                'vector_store': data,
                'index_tracker': tracker_data
            }

            # Write to file
            with open(output_file, 'w') as f:
                json.dump(export_package, f, indent=2)

            file_size = output_file.stat().st_size
            logger.info(f"Export complete: {file_size / 1024 / 1024:.2f} MB")

            return {
                'status': 'success',
                'output_file': str(output_file),
                'file_size_mb': file_size / 1024 / 1024,
                'chunks_exported': len(data.get('chunks', []))
            }

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {'status': 'error', 'error': str(e)}

    def import_data(self, input_file: Path) -> Dict[str, Any]:
        """
        Import vector store data from JSON file.

        Args:
            input_file: Input file path

        Returns:
            Import statistics
        """
        logger.info(f"Importing data from {input_file}...")

        if not input_file.exists():
            logger.error(f"Input file does not exist: {input_file}")
            return {'status': 'error', 'error': 'File not found'}

        # Confirm import
        print("\nWARNING: This will overwrite existing vector store data.")
        response = input("Are you sure? Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("Aborted.")
            return {'status': 'aborted'}

        try:
            # Load import package
            with open(input_file, 'r') as f:
                import_package = json.load(f)

            # Import vector store data
            vector_data = import_package.get('vector_store', {})
            result = self.vector_store.import_collection(vector_data)

            # Import index tracker data
            tracker_data = import_package.get('index_tracker', {})
            self.index_tracker.import_data(tracker_data)

            logger.info("Import complete")

            return {
                'status': 'success',
                'chunks_imported': result.get('chunks_imported', 0),
                'source_timestamp': import_package.get('timestamp')
            }

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return {'status': 'error', 'error': str(e)}


def print_statistics(stats: Dict[str, Any]):
    """Print vector store statistics."""
    print("\n" + "="*60)
    print("Vector Store Statistics")
    print("="*60)

    collection = stats.get('collection', {})
    print(f"Total chunks:     {collection.get('count', 0)}")
    print(f"Collection name:  {collection.get('name', 'N/A')}")

    tracker = stats.get('index_tracker', {})
    print(f"Indexed notes:    {tracker.get('indexed_count', 0)}")

    print(f"Timestamp:        {stats.get('timestamp', 'N/A')}")
    print("="*60)


def print_diagnostics(diagnostics: Dict[str, Any]):
    """Print health diagnostics."""
    print("\n" + "="*60)
    print("Health Diagnostics")
    print("="*60)
    print(f"Overall Status: {diagnostics.get('overall_status', 'unknown').upper()}")
    print("="*60)

    for check_name, check_result in diagnostics.get('checks', {}).items():
        status = check_result.get('status', 'unknown')
        symbol = "✓" if status == 'pass' else "⚠" if status == 'warn' else "✗"
        print(f"\n{symbol} {check_name.replace('_', ' ').title()}: {status.upper()}")

        for key, value in check_result.items():
            if key != 'status':
                print(f"  {key}: {value}")

    print("\n" + "="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Vector store maintenance operations"
    )
    parser.add_argument(
        '--notes-dir',
        type=Path,
        default=Path('test_notes'),
        help='Directory containing notes (default: test_notes)'
    )

    # Operations (mutually exclusive)
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument('--stats', action='store_true', help='Show statistics')
    operations.add_argument('--diagnose', action='store_true', help='Run diagnostics')
    operations.add_argument('--clean', action='store_true', help='Clean stale entries')
    operations.add_argument('--rebuild', action='store_true', help='Rebuild from scratch')
    operations.add_argument('--export', type=Path, help='Export to file')
    operations.add_argument('--import', type=Path, dest='import_file', help='Import from file')

    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load RAG configuration
    try:
        config = load_config_from_env()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1

    print("\n" + "="*60)
    print("Vector Store Maintenance")
    print("="*60)
    print(f"Vector store dir: {config.vector_store_dir}")
    print(f"Collection name:  {config.collection_name}")
    print(f"Notes directory:  {args.notes_dir}")
    print("="*60 + "\n")

    try:
        # Create maintenance handler
        maintenance = VectorStoreMaintenance(config=config, notes_dir=args.notes_dir)

        # Execute operation
        if args.stats:
            stats = maintenance.get_statistics()
            print_statistics(stats)

        elif args.diagnose:
            diagnostics = maintenance.diagnose()
            print_diagnostics(diagnostics)

        elif args.clean:
            result = maintenance.clean_stale_entries()
            print("\nCleanup Results:")
            print("-" * 60)
            for key, value in result.items():
                print(f"{key:20s}: {value}")

        elif args.rebuild:
            result = maintenance.rebuild()
            print("\nRebuild Results:")
            print("-" * 60)
            for key, value in result.items():
                print(f"{key:20s}: {value}")

        elif args.export:
            result = maintenance.export_data(args.export)
            print("\nExport Results:")
            print("-" * 60)
            for key, value in result.items():
                print(f"{key:20s}: {value}")

        elif args.import_file:
            result = maintenance.import_data(args.import_file)
            print("\nImport Results:")
            print("-" * 60)
            for key, value in result.items():
                print(f"{key:20s}: {value}")

        return 0

    except KeyboardInterrupt:
        print("\n\nOperation interrupted.")
        return 130
    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
