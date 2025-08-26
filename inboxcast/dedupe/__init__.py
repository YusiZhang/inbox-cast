"""Deduplication modules."""
from .simple import SimpleDeduplicator
from .semantic import SemanticDeduplicator

__all__ = ['SimpleDeduplicator', 'SemanticDeduplicator']