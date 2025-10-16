"""Link quality metrics for RAG cross-referencing.

This module tracks and reports metrics on link generation quality,
comparing RAG vs fuzzy matching approaches, and measuring performance.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LinkingMetrics:
    """Metrics for a single link generation operation.

    Attributes:
        method: Linking method used ('rag' or 'fuzzy')
        links_generated: Number of links created
        query_time_ms: Time taken for query/search (milliseconds)
        total_time_ms: Total time including processing (milliseconds)
        similarity_scores: List of similarity scores for generated links
        fallback_used: Whether fallback method was used
        error_occurred: Whether an error occurred
        error_message: Error message if error occurred
        timestamp: When metrics were recorded
    """

    method: str
    links_generated: int = 0
    query_time_ms: float = 0.0
    total_time_ms: float = 0.0
    similarity_scores: List[float] = field(default_factory=list)
    fallback_used: bool = False
    error_occurred: bool = False
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for logging."""
        return {
            'method': self.method,
            'links_generated': self.links_generated,
            'query_time_ms': self.query_time_ms,
            'total_time_ms': self.total_time_ms,
            'avg_similarity': self._avg_similarity(),
            'min_similarity': min(self.similarity_scores) if self.similarity_scores else 0.0,
            'max_similarity': max(self.similarity_scores) if self.similarity_scores else 0.0,
            'fallback_used': self.fallback_used,
            'error_occurred': self.error_occurred,
            'error_message': self.error_message,
            'timestamp': self.timestamp,
        }

    def _avg_similarity(self) -> float:
        """Calculate average similarity score."""
        if not self.similarity_scores:
            return 0.0
        return sum(self.similarity_scores) / len(self.similarity_scores)


@dataclass
class AggregatedMetrics:
    """Aggregated metrics across multiple linking operations.

    Attributes:
        total_operations: Total number of linking operations
        rag_operations: Number of RAG linking operations
        fuzzy_operations: Number of fuzzy matching operations
        total_links_generated: Total links across all operations
        total_rag_links: Total links from RAG
        total_fuzzy_links: Total links from fuzzy matching
        fallback_count: Number of times fallback was used
        error_count: Number of errors encountered
        avg_query_time_ms: Average query time
        p95_query_time_ms: 95th percentile query time
        p99_query_time_ms: 99th percentile query time
    """

    total_operations: int = 0
    rag_operations: int = 0
    fuzzy_operations: int = 0
    total_links_generated: int = 0
    total_rag_links: int = 0
    total_fuzzy_links: int = 0
    fallback_count: int = 0
    error_count: int = 0
    avg_query_time_ms: float = 0.0
    p95_query_time_ms: float = 0.0
    p99_query_time_ms: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'total_operations': self.total_operations,
            'rag_operations': self.rag_operations,
            'fuzzy_operations': self.fuzzy_operations,
            'total_links_generated': self.total_links_generated,
            'total_rag_links': self.total_rag_links,
            'total_fuzzy_links': self.total_fuzzy_links,
            'fallback_rate': self.fallback_count / self.total_operations if self.total_operations > 0 else 0.0,
            'error_rate': self.error_count / self.total_operations if self.total_operations > 0 else 0.0,
            'avg_links_per_operation': self.total_links_generated / self.total_operations if self.total_operations > 0 else 0.0,
            'avg_query_time_ms': self.avg_query_time_ms,
            'p95_query_time_ms': self.p95_query_time_ms,
            'p99_query_time_ms': self.p99_query_time_ms,
        }


class MetricsCollector:
    """Collects and aggregates link generation metrics.

    This class tracks metrics for both RAG and fuzzy matching approaches,
    allowing comparison of quality and performance.

    Attributes:
        metrics_history: List of all recorded metrics
        enabled: Whether metrics collection is enabled
    """

    def __init__(self, enabled: bool = True):
        """Initialize metrics collector.

        Args:
            enabled: Whether to collect metrics (default: True)
        """
        self.enabled = enabled
        self.metrics_history: List[LinkingMetrics] = []
        logger.info(f"MetricsCollector initialized (enabled={enabled})")

    def record_linking(
        self,
        method: str,
        links_generated: int,
        query_time_ms: float,
        total_time_ms: float,
        similarity_scores: Optional[List[float]] = None,
        fallback_used: bool = False,
        error: Optional[Exception] = None,
    ) -> LinkingMetrics:
        """Record metrics for a linking operation.

        Args:
            method: Linking method ('rag' or 'fuzzy')
            links_generated: Number of links created
            query_time_ms: Query/search time in milliseconds
            total_time_ms: Total processing time in milliseconds
            similarity_scores: List of similarity scores for links
            fallback_used: Whether fallback method was used
            error: Exception if error occurred

        Returns:
            LinkingMetrics object with recorded metrics
        """
        if not self.enabled:
            return LinkingMetrics(method=method)

        metrics = LinkingMetrics(
            method=method,
            links_generated=links_generated,
            query_time_ms=query_time_ms,
            total_time_ms=total_time_ms,
            similarity_scores=similarity_scores or [],
            fallback_used=fallback_used,
            error_occurred=error is not None,
            error_message=str(error) if error else None,
        )

        self.metrics_history.append(metrics)

        logger.debug(
            f"Recorded {method} linking: {links_generated} links in {total_time_ms:.2f}ms"
        )

        return metrics

    def get_aggregated_metrics(self) -> AggregatedMetrics:
        """Calculate aggregated metrics across all operations.

        Returns:
            AggregatedMetrics object with aggregated statistics
        """
        if not self.metrics_history:
            return AggregatedMetrics()

        # Count operations by method
        rag_ops = [m for m in self.metrics_history if m.method == 'rag']
        fuzzy_ops = [m for m in self.metrics_history if m.method == 'fuzzy']

        # Calculate link counts
        total_rag_links = sum(m.links_generated for m in rag_ops)
        total_fuzzy_links = sum(m.links_generated for m in fuzzy_ops)

        # Calculate fallback and error counts
        fallback_count = sum(1 for m in self.metrics_history if m.fallback_used)
        error_count = sum(1 for m in self.metrics_history if m.error_occurred)

        # Calculate query time percentiles
        query_times = [m.query_time_ms for m in self.metrics_history if m.query_time_ms > 0]
        query_times.sort()

        if query_times:
            avg_query_time = sum(query_times) / len(query_times)
            p95_index = int(len(query_times) * 0.95)
            p99_index = int(len(query_times) * 0.99)
            p95_query_time = query_times[p95_index] if p95_index < len(query_times) else query_times[-1]
            p99_query_time = query_times[p99_index] if p99_index < len(query_times) else query_times[-1]
        else:
            avg_query_time = 0.0
            p95_query_time = 0.0
            p99_query_time = 0.0

        return AggregatedMetrics(
            total_operations=len(self.metrics_history),
            rag_operations=len(rag_ops),
            fuzzy_operations=len(fuzzy_ops),
            total_links_generated=total_rag_links + total_fuzzy_links,
            total_rag_links=total_rag_links,
            total_fuzzy_links=total_fuzzy_links,
            fallback_count=fallback_count,
            error_count=error_count,
            avg_query_time_ms=avg_query_time,
            p95_query_time_ms=p95_query_time,
            p99_query_time_ms=p99_query_time,
        )

    def get_comparison_report(self) -> Dict:
        """Generate comparison report between RAG and fuzzy matching.

        Returns:
            Dictionary with comparison statistics
        """
        if not self.metrics_history:
            return {'error': 'No metrics recorded'}

        rag_metrics = [m for m in self.metrics_history if m.method == 'rag' and not m.error_occurred]
        fuzzy_metrics = [m for m in self.metrics_history if m.method == 'fuzzy' and not m.error_occurred]

        def avg_links(metrics_list):
            if not metrics_list:
                return 0.0
            return sum(m.links_generated for m in metrics_list) / len(metrics_list)

        def avg_time(metrics_list):
            if not metrics_list:
                return 0.0
            return sum(m.query_time_ms for m in metrics_list) / len(metrics_list)

        def avg_similarity(metrics_list):
            all_scores = []
            for m in metrics_list:
                all_scores.extend(m.similarity_scores)
            if not all_scores:
                return 0.0
            return sum(all_scores) / len(all_scores)

        return {
            'rag': {
                'operations': len(rag_metrics),
                'avg_links_per_operation': avg_links(rag_metrics),
                'avg_query_time_ms': avg_time(rag_metrics),
                'avg_similarity_score': avg_similarity(rag_metrics),
            },
            'fuzzy': {
                'operations': len(fuzzy_metrics),
                'avg_links_per_operation': avg_links(fuzzy_metrics),
                'avg_query_time_ms': avg_time(fuzzy_metrics),
                'avg_similarity_score': avg_similarity(fuzzy_metrics),
            },
            'improvement': {
                'links_improvement': (
                    (avg_links(rag_metrics) - avg_links(fuzzy_metrics)) / avg_links(fuzzy_metrics) * 100
                    if avg_links(fuzzy_metrics) > 0 else 0.0
                ),
                'quality_improvement': (
                    (avg_similarity(rag_metrics) - avg_similarity(fuzzy_metrics)) / avg_similarity(fuzzy_metrics) * 100
                    if avg_similarity(fuzzy_metrics) > 0 else 0.0
                ),
            },
        }

    def print_summary(self):
        """Print a human-readable summary of metrics."""
        aggregated = self.get_aggregated_metrics()
        comparison = self.get_comparison_report()

        print("\n" + "="*80)
        print("LINK GENERATION METRICS SUMMARY")
        print("="*80)

        print(f"\nTotal Operations: {aggregated.total_operations}")
        print(f"  - RAG: {aggregated.rag_operations}")
        print(f"  - Fuzzy: {aggregated.fuzzy_operations}")

        print(f"\nTotal Links Generated: {aggregated.total_links_generated}")
        print(f"  - RAG: {aggregated.total_rag_links}")
        print(f"  - Fuzzy: {aggregated.total_fuzzy_links}")

        print(f"\nPerformance:")
        print(f"  - Avg query time: {aggregated.avg_query_time_ms:.2f}ms")
        print(f"  - P95 query time: {aggregated.p95_query_time_ms:.2f}ms")
        print(f"  - P99 query time: {aggregated.p99_query_time_ms:.2f}ms")

        print(f"\nReliability:")
        fallback_rate = aggregated.fallback_count / aggregated.total_operations * 100 if aggregated.total_operations > 0 else 0
        error_rate = aggregated.error_count / aggregated.total_operations * 100 if aggregated.total_operations > 0 else 0
        print(f"  - Fallback rate: {fallback_rate:.1f}%")
        print(f"  - Error rate: {error_rate:.1f}%")

        if 'error' not in comparison:
            print(f"\nRAG vs Fuzzy Comparison:")
            rag_info = comparison['rag']
            fuzzy_info = comparison['fuzzy']
            improvement = comparison['improvement']

            print(f"  RAG avg links: {rag_info['avg_links_per_operation']:.2f}")
            print(f"  Fuzzy avg links: {fuzzy_info['avg_links_per_operation']:.2f}")
            print(f"  -> Improvement: {improvement['links_improvement']:.1f}%")

            print(f"\n  RAG avg similarity: {rag_info['avg_similarity_score']:.3f}")
            print(f"  Fuzzy avg similarity: {fuzzy_info['avg_similarity_score']:.3f}")
            print(f"  -> Quality improvement: {improvement['quality_improvement']:.1f}%")

        print("="*80)

    def reset(self):
        """Reset all collected metrics."""
        self.metrics_history.clear()
        logger.info("Metrics history reset")


# Global metrics collector instance
_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector(enabled: bool = True) -> MetricsCollector:
    """Get the global metrics collector instance.

    Args:
        enabled: Whether metrics collection is enabled

    Returns:
        Global MetricsCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector(enabled=enabled)
    return _global_collector
