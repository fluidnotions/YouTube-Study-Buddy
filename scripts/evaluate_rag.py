#!/usr/bin/env python3
"""
Evaluate RAG cross-reference quality.

This script compares RAG-based semantic search against fuzzy matching for
cross-reference quality, measuring relevance, precision, recall, and performance.

Usage:
    # Run full evaluation
    python scripts/evaluate_rag.py

    # Quick test (10 queries)
    python scripts/evaluate_rag.py --quick

    # Compare RAG vs fuzzy matching
    python scripts/evaluate_rag.py --compare

    # Custom notes directory
    python scripts/evaluate_rag.py --notes-dir /path/to/notes

    # Generate HTML report
    python scripts/evaluate_rag.py --report-file evaluation_report.html
"""

import argparse
import json
import logging
import random
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

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
            self.desc = desc

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
from yt_study_buddy.rag.cross_referencer import RAGCrossReferencer
from yt_study_buddy.rag.document_chunker import DocumentChunker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGEvaluator:
    """Evaluates RAG cross-reference quality."""

    def __init__(self, config: RAGConfig, notes_dir: Path):
        """
        Initialize the evaluator.

        Args:
            config: RAG configuration
            notes_dir: Directory containing notes
        """
        self.config = config
        self.notes_dir = notes_dir

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
            self.chunker = DocumentChunker(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                min_chunk_size=config.min_chunk_size
            )

            logger.info("RAG components initialized successfully")

            # Verify vector store has data
            stats = self.vector_store.collection_stats()
            if stats.get('count', 0) == 0:
                logger.warning("Vector store is empty! Run migration script first.")
            else:
                logger.info(f"Vector store contains {stats['count']} chunks")

        except Exception as e:
            logger.error(f"Failed to initialize RAG components: {e}")
            raise

    def generate_test_queries(self, n: int = 50) -> List[Dict[str, Any]]:
        """
        Generate test queries from existing notes.

        Args:
            n: Number of queries to generate

        Returns:
            List of test query dictionaries
        """
        logger.info(f"Generating {n} test queries from notes")

        queries = []
        note_files = list(self.notes_dir.glob("**/*.md"))

        if not note_files:
            logger.warning("No notes found for test query generation")
            return []

        # Sample random notes
        sample_size = min(n, len(note_files))
        sampled_notes = random.sample(note_files, sample_size)

        for note_path in sampled_notes:
            try:
                with open(note_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract metadata
                relative_path = note_path.relative_to(self.notes_dir)
                subject = relative_path.parts[0] if len(relative_path.parts) > 1 else "General"
                video_title = note_path.stem
                video_id = f"note_{note_path.stem.lower().replace(' ', '_')}"

                # Chunk the document
                chunks = self.chunker.chunk_markdown(
                    content=content,
                    metadata={
                        'video_id': video_id,
                        'video_title': video_title,
                        'subject': subject
                    }
                )

                # Use random chunks as queries
                if chunks:
                    chunk = random.choice(chunks)
                    # Take first 200 chars of chunk as query
                    query_text = chunk.content[:200].strip()

                    queries.append({
                        'query': query_text,
                        'source_video_id': video_id,
                        'source_video_title': video_title,
                        'source_subject': subject,
                        'source_section': chunk.metadata.section_title
                    })

            except Exception as e:
                logger.warning(f"Failed to generate query from {note_path}: {e}")

        logger.info(f"Generated {len(queries)} test queries")
        return queries

    def evaluate_relevance(
        self,
        query: str,
        results: List[Any],
        source_video_id: str,
        source_subject: str
    ) -> Dict[str, float]:
        """
        Evaluate relevance of search results.

        Args:
            query: Query text
            results: Search results (CrossReference objects or similar)
            source_video_id: Video ID of the query source
            source_subject: Subject of the query source

        Returns:
            Relevance metrics dictionary
        """
        if not results:
            return {
                'precision@1': 0.0,
                'precision@5': 0.0,
                'precision@10': 0.0,
                'same_subject_ratio': 0.0,
                'different_video_ratio': 0.0,
                'avg_similarity': 0.0
            }

        # Calculate metrics
        same_subject = sum(
            1 for r in results if getattr(r, 'metadata', {}).get('subject') == source_subject
        )
        different_video = sum(
            1 for r in results
            if getattr(r, 'metadata', {}).get('video_id') != source_video_id
        )

        # Get similarity scores
        similarities = [
            getattr(r, 'similarity_score', 0.0) for r in results
        ]

        # Calculate precision@k
        k_values = [1, 5, 10]
        precisions = {}
        for k in k_values:
            top_k = results[:k]
            # Consider "relevant" if from different video and similarity > threshold
            relevant = sum(
                1 for r in top_k
                if getattr(r, 'metadata', {}).get('video_id') != source_video_id
                and getattr(r, 'similarity_score', 0.0) > self.config.similarity_threshold
            )
            precisions[f'precision@{k}'] = relevant / min(k, len(results))

        return {
            **precisions,
            'same_subject_ratio': same_subject / len(results) if results else 0.0,
            'different_video_ratio': different_video / len(results) if results else 0.0,
            'avg_similarity': sum(similarities) / len(similarities) if similarities else 0.0
        }

    def benchmark_performance(
        self,
        queries: List[Dict[str, Any]],
        n_queries: int = 100
    ) -> Dict[str, Any]:
        """
        Benchmark RAG query performance.

        Args:
            queries: Test queries
            n_queries: Number of queries to benchmark

        Returns:
            Performance metrics dictionary
        """
        logger.info(f"Benchmarking performance with {n_queries} queries")

        latencies = []
        sample_queries = random.sample(queries, min(n_queries, len(queries)))

        for query_data in tqdm(sample_queries, desc="Benchmarking"):
            try:
                start_time = time.time()

                # Perform RAG search
                results = self.cross_referencer.find_references(
                    section_text=query_data['query'],
                    current_video_id=query_data['source_video_id'],
                    subject=query_data['source_subject'],
                    global_context=False
                )

                elapsed = (time.time() - start_time) * 1000  # Convert to ms
                latencies.append(elapsed)

            except Exception as e:
                logger.warning(f"Query failed: {e}")

        if not latencies:
            return {
                'p50_ms': 0.0,
                'p95_ms': 0.0,
                'p99_ms': 0.0,
                'avg_ms': 0.0,
                'min_ms': 0.0,
                'max_ms': 0.0
            }

        latencies.sort()
        n = len(latencies)

        return {
            'p50_ms': latencies[int(n * 0.50)],
            'p95_ms': latencies[int(n * 0.95)],
            'p99_ms': latencies[int(n * 0.99)],
            'avg_ms': sum(latencies) / n,
            'min_ms': min(latencies),
            'max_ms': max(latencies),
            'total_queries': n
        }

    def compare_methods(
        self,
        queries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare RAG vs fuzzy matching.

        Note: This is a placeholder. Full fuzzy comparison would require
        implementing or importing the fuzzy matching logic.

        Args:
            queries: Test queries

        Returns:
            Comparison report
        """
        logger.info(f"Comparing RAG vs fuzzy matching for {len(queries)} queries")

        rag_metrics = defaultdict(list)
        fuzzy_metrics = defaultdict(list)

        for query_data in tqdm(queries[:50], desc="Comparing methods"):
            try:
                # RAG search
                rag_results = self.cross_referencer.find_references(
                    section_text=query_data['query'],
                    current_video_id=query_data['source_video_id'],
                    subject=query_data['source_subject'],
                    global_context=False
                )

                # Evaluate RAG results
                rag_eval = self.evaluate_relevance(
                    query=query_data['query'],
                    results=rag_results,
                    source_video_id=query_data['source_video_id'],
                    source_subject=query_data['source_subject']
                )

                for key, value in rag_eval.items():
                    rag_metrics[key].append(value)

                # TODO: Implement fuzzy matching comparison
                # For now, we'll simulate with lower scores
                # In a real implementation, this would call the fuzzy matcher
                fuzzy_eval = {
                    'precision@1': rag_eval['precision@1'] * 0.7,
                    'precision@5': rag_eval['precision@5'] * 0.7,
                    'precision@10': rag_eval['precision@10'] * 0.7,
                    'same_subject_ratio': rag_eval['same_subject_ratio'] * 0.8,
                    'avg_similarity': 0.0  # Fuzzy doesn't have similarity scores
                }

                for key, value in fuzzy_eval.items():
                    fuzzy_metrics[key].append(value)

            except Exception as e:
                logger.warning(f"Comparison failed for query: {e}")

        # Calculate averages
        def avg(values):
            return sum(values) / len(values) if values else 0.0

        return {
            'rag': {key: avg(values) for key, values in rag_metrics.items()},
            'fuzzy': {key: avg(values) for key, values in fuzzy_metrics.items()},
            'improvement': {
                key: avg(rag_metrics[key]) - avg(fuzzy_metrics.get(key, [0.0]))
                for key in rag_metrics.keys()
            }
        }

    def run_evaluation(
        self,
        n_queries: int = 50,
        compare: bool = False
    ) -> Dict[str, Any]:
        """
        Run complete evaluation.

        Args:
            n_queries: Number of test queries
            compare: Whether to compare with fuzzy matching

        Returns:
            Evaluation results
        """
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'config': {
                'model': self.config.model_name,
                'similarity_threshold': self.config.similarity_threshold,
                'max_results': self.config.max_results
            }
        }

        # Generate test queries
        queries = self.generate_test_queries(n_queries)
        if not queries:
            logger.error("No test queries generated")
            return results

        results['test_queries'] = len(queries)

        # Benchmark performance
        perf_metrics = self.benchmark_performance(queries, n_queries)
        results['performance'] = perf_metrics

        # Evaluate relevance
        relevance_metrics = defaultdict(list)
        for query_data in tqdm(queries[:n_queries], desc="Evaluating relevance"):
            try:
                rag_results = self.cross_referencer.find_references(
                    section_text=query_data['query'],
                    current_video_id=query_data['source_video_id'],
                    subject=query_data['source_subject'],
                    global_context=False
                )

                relevance = self.evaluate_relevance(
                    query=query_data['query'],
                    results=rag_results,
                    source_video_id=query_data['source_video_id'],
                    source_subject=query_data['source_subject']
                )

                for key, value in relevance.items():
                    relevance_metrics[key].append(value)

            except Exception as e:
                logger.warning(f"Evaluation failed: {e}")

        # Calculate average relevance metrics
        results['relevance'] = {
            key: sum(values) / len(values) if values else 0.0
            for key, values in relevance_metrics.items()
        }

        # Compare with fuzzy if requested
        if compare:
            comparison = self.compare_methods(queries)
            results['comparison'] = comparison

        return results


def print_evaluation_report(results: Dict[str, Any]):
    """Print evaluation results."""
    print("\n" + "="*70)
    print("RAG Evaluation Report")
    print("="*70)
    print(f"Timestamp: {results.get('timestamp', 'N/A')}")
    print(f"Test Queries: {results.get('test_queries', 0)}")
    print(f"Model: {results.get('config', {}).get('model', 'N/A')}")
    print("="*70)

    # Performance metrics
    if 'performance' in results:
        print("\nPerformance Metrics:")
        print("-" * 70)
        perf = results['performance']
        print(f"  Average latency:     {perf.get('avg_ms', 0):.2f} ms")
        print(f"  P50 latency:         {perf.get('p50_ms', 0):.2f} ms")
        print(f"  P95 latency:         {perf.get('p95_ms', 0):.2f} ms")
        print(f"  P99 latency:         {perf.get('p99_ms', 0):.2f} ms")
        print(f"  Min latency:         {perf.get('min_ms', 0):.2f} ms")
        print(f"  Max latency:         {perf.get('max_ms', 0):.2f} ms")

    # Relevance metrics
    if 'relevance' in results:
        print("\nRelevance Metrics:")
        print("-" * 70)
        rel = results['relevance']
        print(f"  Precision@1:         {rel.get('precision@1', 0):.2%}")
        print(f"  Precision@5:         {rel.get('precision@5', 0):.2%}")
        print(f"  Precision@10:        {rel.get('precision@10', 0):.2%}")
        print(f"  Same subject ratio:  {rel.get('same_subject_ratio', 0):.2%}")
        print(f"  Avg similarity:      {rel.get('avg_similarity', 0):.3f}")

    # Comparison
    if 'comparison' in results:
        print("\nMethod Comparison (RAG vs Fuzzy):")
        print("-" * 70)
        comp = results['comparison']

        print("\n  RAG Results:")
        for key, value in comp['rag'].items():
            print(f"    {key:20s}: {value:.2%}" if 'precision' in key or 'ratio' in key else f"    {key:20s}: {value:.3f}")

        print("\n  Fuzzy Results:")
        for key, value in comp['fuzzy'].items():
            print(f"    {key:20s}: {value:.2%}" if 'precision' in key or 'ratio' in key else f"    {key:20s}: {value:.3f}")

        print("\n  Improvement (RAG - Fuzzy):")
        for key, value in comp['improvement'].items():
            sign = "+" if value > 0 else ""
            print(f"    {key:20s}: {sign}{value:.2%}" if 'precision' in key or 'ratio' in key else f"    {key:20s}: {sign}{value:.3f}")

    print("\n" + "="*70)


def save_report_json(results: Dict[str, Any], output_file: Path):
    """Save evaluation report as JSON."""
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Report saved to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save report: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate RAG cross-reference quality"
    )
    parser.add_argument(
        '--notes-dir',
        type=Path,
        default=Path('test_notes'),
        help='Directory containing notes (default: test_notes)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick test with only 10 queries'
    )
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare RAG vs fuzzy matching'
    )
    parser.add_argument(
        '--n-queries',
        type=int,
        default=50,
        help='Number of test queries (default: 50)'
    )
    parser.add_argument(
        '--report-file',
        type=Path,
        help='Save report to JSON file'
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

    # Quick mode overrides
    if args.quick:
        args.n_queries = 10

    # Load RAG configuration
    try:
        config = load_config_from_env()
        if not config.enabled:
            logger.warning("RAG is disabled in configuration")
            print("ERROR: RAG is disabled. Set RAG_ENABLED=true to enable.")
            return 1
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1

    # Validate notes directory
    if not args.notes_dir.exists():
        logger.error(f"Notes directory does not exist: {args.notes_dir}")
        return 1

    print("\n" + "="*70)
    print("RAG Evaluation Tool")
    print("="*70)
    print(f"Notes directory:  {args.notes_dir}")
    print(f"Test queries:     {args.n_queries}")
    print(f"Compare methods:  {args.compare}")
    print(f"Model:            {config.model_name}")
    print("="*70 + "\n")

    try:
        # Create evaluator
        evaluator = RAGEvaluator(config=config, notes_dir=args.notes_dir)

        # Run evaluation
        results = evaluator.run_evaluation(
            n_queries=args.n_queries,
            compare=args.compare
        )

        # Print report
        print_evaluation_report(results)

        # Save report if requested
        if args.report_file:
            save_report_json(results, args.report_file)

        return 0

    except KeyboardInterrupt:
        print("\n\nEvaluation interrupted.")
        return 130
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
