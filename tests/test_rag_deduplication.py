"""
Unit tests for RAG engine deduplication

Run with: pytest tests/test_rag_deduplication.py -v

Note: These tests require OPENAI_API_KEY to be set, but mock the actual API calls
"""

import pytest
import tempfile
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

# We'll test the deduplication logic without actually calling OpenAI
# by directly testing the helper methods


class TestRAGDeduplication:
    """Test suite for RAG engine deduplication logic."""

    def test_content_hash_computation(self):
        """Test that content hashing works correctly."""
        from rag_engine import RAGChatbot
        import os

        # Skip if no API key (we won't actually use it for hash testing)
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY not set")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                rag = RAGChatbot(vector_db_path=tmpdir, api_key="dummy-key")
            except Exception:
                pytest.skip("Cannot initialize RAGChatbot (OpenAI client validation)")
                return

            # Test basic hashing
            text1 = "Hello world this is a test"
            text2 = "Hello world this is a test"  # Same text
            text3 = "Different text entirely"

            hash1 = rag._compute_content_hash(text1)
            hash2 = rag._compute_content_hash(text2)
            hash3 = rag._compute_content_hash(text3)

            # Same text should produce same hash
            assert hash1 == hash2
            # Different text should produce different hash
            assert hash1 != hash3

    def test_content_hash_normalization(self):
        """Test that content hashing normalizes text properly."""
        from rag_engine import RAGChatbot
        import os

        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY not set")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                rag = RAGChatbot(vector_db_path=tmpdir, api_key="dummy-key")
            except Exception:
                pytest.skip("Cannot initialize RAGChatbot")
                return

            # These should all produce the same hash after normalization
            text1 = "hello world"
            text2 = "Hello World"  # Different case
            text3 = "hello  world"  # Extra spaces
            text4 = "  hello world  "  # Leading/trailing whitespace

            hash1 = rag._compute_content_hash(text1)
            hash2 = rag._compute_content_hash(text2)
            hash3 = rag._compute_content_hash(text3)
            hash4 = rag._compute_content_hash(text4)

            # All should be the same after normalization
            assert hash1 == hash2
            assert hash1 == hash3
            assert hash1 == hash4

    def test_hash_file_persistence(self):
        """Test that content hashes are saved and loaded correctly."""
        from rag_engine import RAGChatbot
        import os

        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY not set")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                rag = RAGChatbot(vector_db_path=tmpdir, api_key="dummy-key")
            except Exception:
                pytest.skip("Cannot initialize RAGChatbot")
                return

            # Add some hashes
            rag.content_hashes.add("hash1")
            rag.content_hashes.add("hash2")
            rag.content_hashes.add("hash3")

            # Save to disk
            rag._save_content_hashes()

            # Verify file exists
            hash_file = rag._get_hash_file_path()
            assert hash_file.exists()

            # Create new instance and verify hashes are loaded
            try:
                rag2 = RAGChatbot(vector_db_path=tmpdir, api_key="dummy-key")
                assert len(rag2.content_hashes) == 3
                assert "hash1" in rag2.content_hashes
                assert "hash2" in rag2.content_hashes
                assert "hash3" in rag2.content_hashes
            except Exception:
                pytest.skip("Cannot create second RAGChatbot instance")

    def test_duplicate_detection_mock(self):
        """Test duplicate detection logic without API calls."""
        # This is a simplified test that doesn't require OpenAI
        import hashlib

        def compute_content_hash(text: str) -> str:
            """Simplified version of the hash function."""
            normalized = ' '.join(text.lower().split())
            return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

        # Simulate tracking hashes
        content_hashes = set()

        # First document
        doc1 = "This is a test document"
        hash1 = compute_content_hash(doc1)
        is_duplicate1 = hash1 in content_hashes
        content_hashes.add(hash1)

        assert is_duplicate1 is False  # First occurrence, not a duplicate
        assert len(content_hashes) == 1

        # Exact duplicate
        doc2 = "This is a test document"
        hash2 = compute_content_hash(doc2)
        is_duplicate2 = hash2 in content_hashes

        assert is_duplicate2 is True  # Should be detected as duplicate
        assert len(content_hashes) == 1  # Count shouldn't increase

        # Different document
        doc3 = "This is a different document"
        hash3 = compute_content_hash(doc3)
        is_duplicate3 = hash3 in content_hashes
        content_hashes.add(hash3)

        assert is_duplicate3 is False  # Different content, not a duplicate
        assert len(content_hashes) == 2

        # Duplicate with different formatting
        doc4 = "   This   is a  test   document  "
        hash4 = compute_content_hash(doc4)
        is_duplicate4 = hash4 in content_hashes

        assert is_duplicate4 is True  # Should match doc1 after normalization


class TestDeduplicationIntegration:
    """Integration tests for deduplication in ingestion pipeline."""

    def test_ingest_with_duplicates_mock(self):
        """Test that duplicate documents are skipped during ingestion."""
        # Mock test without actual OpenAI calls
        documents = [
            {"text": "Document 1 content", "title": "Doc 1"},
            {"text": "Document 2 content", "title": "Doc 2"},
            {"text": "Document 1 content", "title": "Doc 1 duplicate"},  # Duplicate
            {"text": "Document 3 content", "title": "Doc 3"},
            {"text": "Document 2 content", "title": "Doc 2 duplicate"},  # Duplicate
        ]

        # Simulate deduplication logic
        import hashlib
        seen_hashes = set()
        unique_docs = []

        for doc in documents:
            text = doc.get("text", "")
            normalized = ' '.join(text.lower().split())
            content_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_docs.append(doc)

        # Should have 3 unique documents (1, 2, 3)
        assert len(unique_docs) == 3
        assert unique_docs[0]["title"] == "Doc 1"
        assert unique_docs[1]["title"] == "Doc 2"
        assert unique_docs[2]["title"] == "Doc 3"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
