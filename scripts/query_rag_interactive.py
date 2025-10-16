#!/usr/bin/env python3
"""
Interactive RAG query tool.

This script provides a REPL (Read-Eval-Print Loop) interface for testing RAG
queries with pretty-printed results, filtering capabilities, and export options.

Usage:
    # Start interactive session
    python scripts/query_rag_interactive.py

    # With custom notes directory
    python scripts/query_rag_interactive.py --notes-dir /path/to/notes

Commands:
    - Enter a query to search
    - "subject:AI <query>" - Filter by subject
    - "video:<id> <query>" - Filter by video ID
    - "global <query>" - Search globally (all subjects)
    - "export <filename>" - Export last results to JSON
    - "stats" - Show vector store statistics
    - "help" - Show help
    - "quit" or "exit" - Exit the tool
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yt_study_buddy.rag.config import load_config_from_env, RAGConfig
from yt_study_buddy.rag.vector_store import VectorStore
from yt_study_buddy.rag.embedding_service import EmbeddingService
from yt_study_buddy.rag.cross_referencer import RAGCrossReferencer, CrossReference

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InteractiveRAGQuery:
    """Interactive REPL for RAG queries."""

    def __init__(self, config: RAGConfig):
        """
        Initialize the interactive query tool.

        Args:
            config: RAG configuration
        """
        self.config = config
        self.last_results: List[CrossReference] = []

        # Initialize RAG components
        try:
            self.vector_store = VectorStore(
                persist_dir=str(config.vector_store_dir),
                collection_name=config.collection_name
            )
            self.embedding_service = EmbeddingService(
                model_name=config.model_name,
                cache_dir=str(config.model_cache_dir)
            )
            self.cross_referencer = RAGCrossReferencer(
                embedding_service=self.embedding_service,
                vector_store=self.vector_store,
                config=config
            )

            # Verify vector store has data
            stats = self.vector_store.collection_stats()
            self.total_chunks = stats.get('count', 0)

            if self.total_chunks == 0:
                print("\nWARNING: Vector store is empty!")
                print("Run migration script first: python scripts/migrate_notes_to_rag.py\n")
            else:
                print(f"\nConnected to vector store with {self.total_chunks} chunks")

        except Exception as e:
            logger.error(f"Failed to initialize RAG components: {e}")
            raise

    def parse_query(self, user_input: str) -> Dict[str, Any]:
        """
        Parse user query for filters and options.

        Args:
            user_input: Raw user input

        Returns:
            Parsed query dictionary
        """
        # Check for subject filter: "subject:AI query text"
        subject_match = re.match(r'subject:(\w+)\s+(.+)', user_input, re.IGNORECASE)
        if subject_match:
            return {
                'query': subject_match.group(2).strip(),
                'subject': subject_match.group(1),
                'global_context': False
            }

        # Check for video filter: "video:xyz query text"
        video_match = re.match(r'video:(\S+)\s+(.+)', user_input, re.IGNORECASE)
        if video_match:
            return {
                'query': video_match.group(2).strip(),
                'video_id': video_match.group(1),
                'global_context': False
            }

        # Check for global search: "global query text"
        global_match = re.match(r'global\s+(.+)', user_input, re.IGNORECASE)
        if global_match:
            return {
                'query': global_match.group(1).strip(),
                'global_context': True
            }

        # Regular query
        return {
            'query': user_input.strip(),
            'global_context': False
        }

    def execute_query(self, parsed_query: Dict[str, Any]) -> List[CrossReference]:
        """
        Execute a RAG query.

        Args:
            parsed_query: Parsed query dictionary

        Returns:
            List of cross-references
        """
        query = parsed_query['query']
        subject = parsed_query.get('subject')
        video_id = parsed_query.get('video_id', 'dummy')
        global_context = parsed_query.get('global_context', False)

        try:
            results = self.cross_referencer.find_references(
                section_text=query,
                current_video_id=video_id,
                subject=subject,
                global_context=global_context
            )
            return results
        except Exception as e:
            logger.error(f"Query failed: {e}")
            print(f"\nError executing query: {e}")
            return []

    def format_results(self, results: List[CrossReference], max_results: int = 10) -> str:
        """
        Format results for display.

        Args:
            results: List of cross-references
            max_results: Maximum number of results to display

        Returns:
            Formatted string
        """
        if not results:
            return "\nNo results found."

        output = [f"\nFound {len(results)} results:\n"]
        output.append("=" * 80)

        for i, ref in enumerate(results[:max_results], 1):
            # Header
            score_bar = "█" * int(ref.similarity_score * 20)
            output.append(f"\n{i}. {ref.target_section_title} (score: {ref.similarity_score:.3f} {score_bar})")

            # Metadata
            output.append(f"   Video: {ref.target_video_title}")
            if hasattr(ref, 'metadata') and ref.metadata:
                output.append(f"   Subject: {ref.metadata.get('subject', 'N/A')}")
                output.append(f"   Video ID: {ref.metadata.get('video_id', 'N/A')}")

            # Preview (first 200 chars)
            preview = ref.preview_text[:200] + "..." if len(ref.preview_text) > 200 else ref.preview_text
            output.append(f"   Preview: {preview}")

            # Obsidian link
            link = self.cross_referencer.format_as_obsidian_link(ref)
            output.append(f"   Link: {link}")

            output.append("")

        if len(results) > max_results:
            output.append(f"... and {len(results) - max_results} more results")

        output.append("=" * 80)

        return "\n".join(output)

    def export_results(self, filename: str):
        """
        Export last results to JSON file.

        Args:
            filename: Output filename
        """
        if not self.last_results:
            print("No results to export.")
            return

        try:
            export_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'total_results': len(self.last_results),
                'results': []
            }

            for ref in self.last_results:
                export_data['results'].append({
                    'section_title': ref.target_section_title,
                    'video_title': ref.target_video_title,
                    'video_id': ref.metadata.get('video_id') if hasattr(ref, 'metadata') else None,
                    'subject': ref.metadata.get('subject') if hasattr(ref, 'metadata') else None,
                    'similarity_score': ref.similarity_score,
                    'preview': ref.preview_text[:500],
                    'obsidian_link': self.cross_referencer.format_as_obsidian_link(ref)
                })

            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)

            print(f"\nExported {len(self.last_results)} results to {filename}")

        except Exception as e:
            print(f"\nError exporting results: {e}")

    def show_stats(self):
        """Show vector store statistics."""
        try:
            stats = self.vector_store.collection_stats()
            print("\nVector Store Statistics:")
            print("-" * 40)
            print(f"Total chunks:     {stats.get('count', 0)}")
            print(f"Collection name:  {stats.get('name', 'N/A')}")
            print(f"Model:            {self.config.model_name}")
            print(f"Similarity threshold: {self.config.similarity_threshold}")
            print(f"Max results:      {self.config.max_results}")
            print("-" * 40)
        except Exception as e:
            print(f"\nError getting statistics: {e}")

    def show_help(self):
        """Show help message."""
        help_text = """
RAG Query Tool - Commands
========================

Query Syntax:
  <query>                    - Search with current filters
  subject:AI <query>         - Filter by subject
  video:<id> <query>         - Filter by video ID
  global <query>             - Search globally (all subjects)

Commands:
  stats                      - Show vector store statistics
  export <filename>          - Export last results to JSON
  help                       - Show this help message
  quit / exit                - Exit the tool

Examples:
  > How do neural networks learn?
  > subject:AI backpropagation algorithm
  > global gradient descent
  > export results.json

Tips:
  - Use specific queries for better results
  - Try different subjects to explore connections
  - Export results to save interesting findings
"""
        print(help_text)

    def run(self):
        """Run the interactive REPL."""
        print("\n" + "="*80)
        print("RAG Interactive Query Tool")
        print("="*80)
        print(f"Model: {self.config.model_name}")
        print(f"Chunks in store: {self.total_chunks}")
        print("\nType 'help' for commands, 'quit' to exit")
        print("="*80)

        while True:
            try:
                # Get user input
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                # Check for commands
                if user_input.lower() in ('quit', 'exit'):
                    print("\nGoodbye!")
                    break

                elif user_input.lower() == 'help':
                    self.show_help()
                    continue

                elif user_input.lower() == 'stats':
                    self.show_stats()
                    continue

                elif user_input.lower().startswith('export '):
                    filename = user_input[7:].strip()
                    if filename:
                        self.export_results(filename)
                    else:
                        print("Usage: export <filename>")
                    continue

                # Parse and execute query
                parsed = self.parse_query(user_input)
                print(f"\nSearching for: {parsed['query']}")
                if parsed.get('subject'):
                    print(f"Subject filter: {parsed['subject']}")
                if parsed.get('global_context'):
                    print("Mode: Global search")

                # Execute query
                results = self.execute_query(parsed)
                self.last_results = results

                # Display results
                output = self.format_results(results)
                print(output)

            except KeyboardInterrupt:
                print("\n\nUse 'quit' or 'exit' to exit.")
            except EOFError:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error in REPL: {e}", exc_info=True)
                print(f"\nError: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive RAG query tool"
    )
    parser.add_argument(
        '--notes-dir',
        type=Path,
        default=Path('test_notes'),
        help='Directory containing notes (default: test_notes)'
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
            print("ERROR: RAG is disabled. Set RAG_ENABLED=true to enable.")
            return 1
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        print(f"ERROR: Failed to load configuration: {e}")
        return 1

    try:
        # Create interactive query tool
        tool = InteractiveRAGQuery(config=config)

        # Run REPL
        tool.run()

        return 0

    except Exception as e:
        logger.error(f"Failed to start interactive tool: {e}", exc_info=True)
        print(f"ERROR: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
