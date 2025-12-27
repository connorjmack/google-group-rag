"""
Unit tests for parser.py

Run with: pytest tests/test_parser.py -v
"""

import pytest
import tempfile
import csv
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from parser import DocumentParser


class TestDocumentParser:
    """Test suite for DocumentParser class."""

    def setup_method(self):
        """Set up test fixtures before each test."""
        self.parser = DocumentParser(chunk_size=20, overlap=5)

    def test_chunk_text_basic(self):
        """Test basic text chunking functionality."""
        text = "Hello world this is a test of chunking"
        chunks = self.parser.chunk_text(text)

        # Should create multiple chunks
        assert len(chunks) > 1
        # First chunk should be 20 chars
        assert len(chunks[0]) == 20
        # Should have overlap
        assert chunks[0][-5:] == chunks[1][:5]

    def test_chunk_text_short_text(self):
        """Test chunking with text shorter than chunk size."""
        text = "Short text"
        chunks = self.parser.chunk_text(text)

        # Should create single chunk
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_empty(self):
        """Test chunking with empty text."""
        text = ""
        chunks = self.parser.chunk_text(text)

        # Should create single empty chunk
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_chunk_size_configuration(self):
        """Test that chunk size is configurable."""
        parser = DocumentParser(chunk_size=10, overlap=2)
        text = "0123456789abcdefghij"
        chunks = parser.chunk_text(text)

        assert len(chunks[0]) == 10
        assert chunks[0] == "0123456789"

    def test_load_csv_basic(self):
        """Test loading CSV file with scraped data."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['title', 'content', 'url', 'date', 'author', 'group_url'])
            writer.writeheader()
            writer.writerow({
                'title': 'Test Thread',
                'content': 'This is test content',
                'url': 'https://example.com/thread1',
                'date': '2024-01-01',
                'author': 'Test Author',
                'group_url': 'https://example.com/group'
            })
            csv_path = f.name

        try:
            records = self.parser.load_csv(csv_path)

            assert len(records) == 1
            assert records[0]['title'] == 'Test Thread'
            assert records[0]['text'] == 'This is test content'
            assert records[0]['author'] == 'Test Author'
        finally:
            Path(csv_path).unlink()

    def test_load_csv_missing_file(self):
        """Test loading non-existent CSV file."""
        with pytest.raises(FileNotFoundError):
            self.parser.load_csv('/nonexistent/file.csv')

    def test_load_csv_missing_columns(self):
        """Test loading CSV with missing required columns."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['title', 'date'])
            writer.writeheader()
            writer.writerow({'title': 'Test', 'date': '2024-01-01'})
            csv_path = f.name

        try:
            with pytest.raises(ValueError, match="missing required columns"):
                self.parser.load_csv(csv_path)
        finally:
            Path(csv_path).unlink()

    def test_load_csv_empty_content(self):
        """Test that rows with empty content are skipped."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['title', 'content', 'url'])
            writer.writeheader()
            writer.writerow({'title': 'Test 1', 'content': '', 'url': 'url1'})
            writer.writerow({'title': 'Test 2', 'content': 'Valid content', 'url': 'url2'})
            csv_path = f.name

        try:
            records = self.parser.load_csv(csv_path)
            # Should only get the record with valid content
            assert len(records) == 1
            assert records[0]['title'] == 'Test 2'
        finally:
            Path(csv_path).unlink()

    def test_process_csv_creates_chunks(self):
        """Test that process_csv properly chunks content."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['title', 'content', 'url', 'date', 'author', 'group_url'])
            writer.writeheader()
            # Create content longer than chunk size to force multiple chunks
            long_content = "x" * 100
            writer.writerow({
                'title': 'Long Thread',
                'content': long_content,
                'url': 'https://example.com/long',
                'date': '2024-01-01',
                'author': 'Author',
                'group_url': 'https://example.com/group'
            })
            csv_path = f.name

        try:
            chunks = self.parser.process_csv(csv_path)

            # Should create multiple chunks
            assert len(chunks) > 1
            # Each chunk should preserve metadata
            for chunk in chunks:
                assert chunk['title'] == 'Long Thread'
                assert chunk['author'] == 'Author'
                assert chunk['url'] == 'https://example.com/long'
                assert 'chunk_index' in chunk
                assert 'total_chunks' in chunk
        finally:
            Path(csv_path).unlink()

    def test_process_csv_chunk_metadata(self):
        """Test that chunk metadata is correctly populated."""
        parser = DocumentParser(chunk_size=10, overlap=2)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['title', 'content', 'url'])
            writer.writeheader()
            writer.writerow({
                'title': 'Test',
                'content': 'This is test content that will be chunked',
                'url': 'https://example.com/test'
            })
            csv_path = f.name

        try:
            chunks = parser.process_csv(csv_path)

            # Verify chunk indices
            for i, chunk in enumerate(chunks):
                assert chunk['chunk_index'] == i
                assert chunk['total_chunks'] == len(chunks)
        finally:
            Path(csv_path).unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
