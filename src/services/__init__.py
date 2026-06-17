"""
CodeCortex Services Package — provides runtime services for the CodeCortex ecosystem.

Exports:
  UnifiedSearchEngine, SearchRequest, SearchResponse from unified_search
  IndexStatus, check_index_status, run_full_index from auto_indexer
  UnifiedIndexingEngine, IndexingRequest, IndexingResult, IndexProvider from unified_indexing
  SecurityFilter, parse_ignore_file, IgnoreRule from security_filter
"""

from src.services.unified_search import UnifiedSearchEngine, SearchRequest, SearchResponse, get_search_engine, SEARCH_PROVIDERS
from src.services.auto_indexer import IndexStatus, check_index_status, run_full_index
from src.services.unified_indexing import UnifiedIndexingEngine, IndexingRequest, IndexingResult, IndexProvider, INDEX_PROVIDERS as INDEXING_PROVIDERS, get_indexing_engine
from src.services.security_filter import SecurityFilter, parse_ignore_file, IgnoreRule

__all__ = [
    "UnifiedSearchEngine", "SearchRequest", "SearchResponse",
    "get_search_engine", "SEARCH_PROVIDERS",
    "IndexStatus", "check_index_status", "run_full_index",
    "UnifiedIndexingEngine", "IndexingRequest", "IndexingResult",
    "IndexProvider", "INDEXING_PROVIDERS", "get_indexing_engine",
    "SecurityFilter", "parse_ignore_file", "IgnoreRule",
]
