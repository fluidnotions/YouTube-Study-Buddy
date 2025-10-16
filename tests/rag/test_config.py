"""Unit tests for RAG configuration module."""

import os
from pathlib import Path
import pytest

from yt_study_buddy.rag.config import RAGConfig, load_config_from_env


class TestRAGConfig:
    """Tests for RAGConfig dataclass."""
    
    def test_default_values(self):
        """Test that default configuration values are set correctly."""
        config = RAGConfig()
        
        assert config.enabled is True
        assert config.model_name == "all-mpnet-base-v2"
        assert config.collection_name == "study_notes"
        assert config.similarity_threshold == 0.3
        assert config.max_results == 5
        assert config.batch_size == 32
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 50
        assert config.min_chunk_size == 50
    
    def test_custom_values(self):
        """Test creating config with custom values."""
        config = RAGConfig(
            enabled=False,
            model_name="test-model",
            similarity_threshold=0.5,
            max_results=10,
        )
        
        assert config.enabled is False
        assert config.model_name == "test-model"
        assert config.similarity_threshold == 0.5
        assert config.max_results == 10
    
    def test_path_post_init(self):
        """Test that paths are properly converted in __post_init__."""
        config = RAGConfig(
            model_cache_dir="/tmp/cache",
            vector_store_dir="/tmp/store",
        )
        
        assert isinstance(config.model_cache_dir, Path)
        assert isinstance(config.vector_store_dir, Path)
        assert str(config.model_cache_dir) == "/tmp/cache"
        assert str(config.vector_store_dir) == "/tmp/store"


class TestLoadConfigFromEnv:
    """Tests for load_config_from_env function."""
    
    def test_load_with_no_env_vars(self, monkeypatch):
        """Test loading config with no environment variables set."""
        # Clear all RAG-related env vars
        for key in list(os.environ.keys()):
            if key.startswith('RAG_') or key in ('CHROMA_PERSIST_DIR', 'MODEL_CACHE_DIR'):
                monkeypatch.delenv(key, raising=False)
        
        config = load_config_from_env()
        
        # Should use defaults
        assert config.enabled is True
        assert config.model_name == "all-mpnet-base-v2"
        assert config.collection_name == "study_notes"
    
    def test_load_rag_enabled(self, monkeypatch):
        """Test loading RAG_ENABLED from various formats."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('on', True),
            ('enabled', True),
            ('false', False),
            ('False', False),
            ('0', False),
            ('no', False),
            ('off', False),
        ]
        
        for env_value, expected in test_cases:
            monkeypatch.setenv('RAG_ENABLED', env_value)
            config = load_config_from_env()
            assert config.enabled == expected, f"Failed for RAG_ENABLED={env_value}"
    
    def test_load_model_name(self, monkeypatch):
        """Test loading custom model name."""
        monkeypatch.setenv('RAG_MODEL', 'custom-model-v1')
        config = load_config_from_env()
        
        assert config.model_name == 'custom-model-v1'
    
    def test_load_similarity_threshold(self, monkeypatch):
        """Test loading similarity threshold."""
        monkeypatch.setenv('RAG_SIMILARITY_THRESHOLD', '0.7')
        config = load_config_from_env()
        
        assert config.similarity_threshold == 0.7
    
    def test_load_invalid_float(self, monkeypatch):
        """Test handling invalid float values."""
        monkeypatch.setenv('RAG_SIMILARITY_THRESHOLD', 'invalid')
        config = load_config_from_env()
        
        # Should use default when invalid
        assert config.similarity_threshold == 0.3
    
    def test_load_max_results(self, monkeypatch):
        """Test loading max results."""
        monkeypatch.setenv('RAG_MAX_RESULTS', '10')
        config = load_config_from_env()
        
        assert config.max_results == 10
    
    def test_load_invalid_int(self, monkeypatch):
        """Test handling invalid integer values."""
        monkeypatch.setenv('RAG_MAX_RESULTS', 'invalid')
        config = load_config_from_env()
        
        # Should use default when invalid
        assert config.max_results == 5
    
    def test_load_batch_size(self, monkeypatch):
        """Test loading batch size."""
        monkeypatch.setenv('RAG_BATCH_SIZE', '64')
        config = load_config_from_env()
        
        assert config.batch_size == 64
    
    def test_load_chunk_settings(self, monkeypatch):
        """Test loading chunk size, overlap, and min size."""
        monkeypatch.setenv('RAG_CHUNK_SIZE', '2000')
        monkeypatch.setenv('RAG_CHUNK_OVERLAP', '100')
        monkeypatch.setenv('RAG_MIN_CHUNK_SIZE', '100')
        config = load_config_from_env()
        
        assert config.chunk_size == 2000
        assert config.chunk_overlap == 100
        assert config.min_chunk_size == 100
    
    def test_load_model_cache_dir(self, monkeypatch):
        """Test loading model cache directory."""
        monkeypatch.setenv('RAG_MODEL_CACHE_DIR', '/custom/cache')
        config = load_config_from_env()
        
        assert config.model_cache_dir == Path('/custom/cache')
    
    def test_load_legacy_model_cache_dir(self, monkeypatch):
        """Test loading legacy MODEL_CACHE_DIR environment variable."""
        monkeypatch.setenv('MODEL_CACHE_DIR', '/legacy/cache')
        config = load_config_from_env()
        
        assert config.model_cache_dir == Path('/legacy/cache')
    
    def test_rag_model_cache_dir_takes_precedence(self, monkeypatch):
        """Test that RAG_MODEL_CACHE_DIR takes precedence over legacy."""
        monkeypatch.setenv('RAG_MODEL_CACHE_DIR', '/new/cache')
        monkeypatch.setenv('MODEL_CACHE_DIR', '/old/cache')
        config = load_config_from_env()
        
        assert config.model_cache_dir == Path('/new/cache')
    
    def test_load_vector_store_dir(self, monkeypatch):
        """Test loading vector store directory."""
        monkeypatch.setenv('RAG_VECTOR_STORE_DIR', '/custom/store')
        config = load_config_from_env()
        
        assert config.vector_store_dir == Path('/custom/store')
    
    def test_load_legacy_chroma_persist_dir(self, monkeypatch):
        """Test loading legacy CHROMA_PERSIST_DIR environment variable."""
        monkeypatch.setenv('CHROMA_PERSIST_DIR', '/legacy/chroma')
        config = load_config_from_env()
        
        assert config.vector_store_dir == Path('/legacy/chroma')
    
    def test_rag_vector_store_dir_takes_precedence(self, monkeypatch):
        """Test that RAG_VECTOR_STORE_DIR takes precedence over legacy."""
        monkeypatch.setenv('RAG_VECTOR_STORE_DIR', '/new/store')
        monkeypatch.setenv('CHROMA_PERSIST_DIR', '/old/chroma')
        config = load_config_from_env()
        
        assert config.vector_store_dir == Path('/new/store')
    
    def test_load_collection_name(self, monkeypatch):
        """Test loading collection name."""
        monkeypatch.setenv('RAG_COLLECTION_NAME', 'custom_collection')
        config = load_config_from_env()
        
        assert config.collection_name == 'custom_collection'
    
    def test_load_all_env_vars(self, monkeypatch):
        """Test loading all environment variables together."""
        monkeypatch.setenv('RAG_ENABLED', 'false')
        monkeypatch.setenv('RAG_MODEL', 'test-model')
        monkeypatch.setenv('RAG_MODEL_CACHE_DIR', '/test/cache')
        monkeypatch.setenv('RAG_VECTOR_STORE_DIR', '/test/store')
        monkeypatch.setenv('RAG_COLLECTION_NAME', 'test_collection')
        monkeypatch.setenv('RAG_SIMILARITY_THRESHOLD', '0.6')
        monkeypatch.setenv('RAG_MAX_RESULTS', '8')
        monkeypatch.setenv('RAG_BATCH_SIZE', '16')
        monkeypatch.setenv('RAG_CHUNK_SIZE', '1500')
        monkeypatch.setenv('RAG_CHUNK_OVERLAP', '75')
        monkeypatch.setenv('RAG_MIN_CHUNK_SIZE', '75')
        
        config = load_config_from_env()
        
        assert config.enabled is False
        assert config.model_name == 'test-model'
        assert config.model_cache_dir == Path('/test/cache')
        assert config.vector_store_dir == Path('/test/store')
        assert config.collection_name == 'test_collection'
        assert config.similarity_threshold == 0.6
        assert config.max_results == 8
        assert config.batch_size == 16
        assert config.chunk_size == 1500
        assert config.chunk_overlap == 75
        assert config.min_chunk_size == 75
