"""
Unit tests for scraper checkpoint functionality

Run with: pytest tests/test_checkpoint.py -v
"""

import pytest
import tempfile
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.universal_scraper import Checkpoint


class TestCheckpoint:
    """Test suite for Checkpoint class."""

    def setup_method(self):
        """Set up test fixtures before each test."""
        # Create temporary checkpoint file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.checkpoint_path = self.temp_file.name

    def teardown_method(self):
        """Clean up after each test."""
        Path(self.checkpoint_path).unlink(missing_ok=True)

    def test_checkpoint_creation(self):
        """Test creating a new checkpoint."""
        checkpoint = Checkpoint(self.checkpoint_path)

        assert checkpoint.data is not None
        assert "groups" in checkpoint.data
        assert "scraped_urls" in checkpoint.data

    def test_checkpoint_save_and_load(self):
        """Test saving and loading checkpoint data."""
        checkpoint1 = Checkpoint(self.checkpoint_path)
        checkpoint1.update_thread_progress("https://example.com/group1", 5)

        # Create new checkpoint instance to load from disk
        checkpoint2 = Checkpoint(self.checkpoint_path)

        assert checkpoint2.get_last_thread_index("https://example.com/group1") == 5

    def test_thread_progress_tracking(self):
        """Test tracking thread scraping progress."""
        checkpoint = Checkpoint(self.checkpoint_path)
        group_url = "https://example.com/group1"

        # Initially should return -1
        assert checkpoint.get_last_thread_index(group_url) == -1

        # Update progress
        checkpoint.update_thread_progress(group_url, 10)
        assert checkpoint.get_last_thread_index(group_url) == 10

        # Update again
        checkpoint.update_thread_progress(group_url, 20)
        assert checkpoint.get_last_thread_index(group_url) == 20

    def test_group_completion_tracking(self):
        """Test marking groups as completed."""
        checkpoint = Checkpoint(self.checkpoint_path)
        group_url = "https://example.com/group1"

        # Initially not completed
        assert checkpoint.is_group_completed(group_url) is False

        # Mark as completed
        checkpoint.mark_group_completed(group_url)
        assert checkpoint.is_group_completed(group_url) is True

    def test_url_deduplication(self):
        """Test URL deduplication tracking."""
        checkpoint = Checkpoint(self.checkpoint_path)
        url1 = "https://example.com/thread1"
        url2 = "https://example.com/thread2"

        # Initially no URLs scraped
        assert checkpoint.is_url_scraped(url1) is False
        assert checkpoint.get_scraped_count() == 0

        # Mark URL as scraped
        checkpoint.mark_url_scraped(url1)
        assert checkpoint.is_url_scraped(url1) is True
        assert checkpoint.is_url_scraped(url2) is False
        assert checkpoint.get_scraped_count() == 1

        # Mark another URL
        checkpoint.mark_url_scraped(url2)
        assert checkpoint.is_url_scraped(url2) is True
        assert checkpoint.get_scraped_count() == 2

    def test_duplicate_url_handling(self):
        """Test that marking the same URL twice doesn't create duplicates."""
        checkpoint = Checkpoint(self.checkpoint_path)
        url = "https://example.com/thread1"

        checkpoint.mark_url_scraped(url)
        checkpoint.mark_url_scraped(url)  # Mark again

        # Should still only count once
        assert checkpoint.get_scraped_count() == 1

    def test_multiple_groups(self):
        """Test tracking multiple groups simultaneously."""
        checkpoint = Checkpoint(self.checkpoint_path)
        group1 = "https://example.com/group1"
        group2 = "https://example.com/group2"

        checkpoint.update_thread_progress(group1, 5)
        checkpoint.update_thread_progress(group2, 10)

        assert checkpoint.get_last_thread_index(group1) == 5
        assert checkpoint.get_last_thread_index(group2) == 10

        checkpoint.mark_group_completed(group1)
        assert checkpoint.is_group_completed(group1) is True
        assert checkpoint.is_group_completed(group2) is False

    def test_persistence_across_instances(self):
        """Test that checkpoint data persists across different instances."""
        url1 = "https://example.com/thread1"
        url2 = "https://example.com/thread2"
        group = "https://example.com/group1"

        # Create checkpoint and add data
        checkpoint1 = Checkpoint(self.checkpoint_path)
        checkpoint1.mark_url_scraped(url1)
        checkpoint1.update_thread_progress(group, 15)

        # Create new instance
        checkpoint2 = Checkpoint(self.checkpoint_path)

        # Verify data persisted
        assert checkpoint2.is_url_scraped(url1) is True
        assert checkpoint2.is_url_scraped(url2) is False
        assert checkpoint2.get_last_thread_index(group) == 15
        assert checkpoint2.get_scraped_count() == 1

    def test_checkpoint_file_format(self):
        """Test that checkpoint file has correct JSON structure."""
        checkpoint = Checkpoint(self.checkpoint_path)
        checkpoint.mark_url_scraped("https://example.com/thread1")
        checkpoint.update_thread_progress("https://example.com/group1", 5)
        checkpoint.save()

        # Read and verify JSON structure
        with open(self.checkpoint_path, 'r') as f:
            data = json.load(f)

        assert "groups" in data
        assert "scraped_urls" in data
        assert isinstance(data["scraped_urls"], list)
        assert "https://example.com/thread1" in data["scraped_urls"]
        assert "https://example.com/group1" in data["groups"]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
