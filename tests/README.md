# Scholar-RAG Unit Tests

This directory contains unit tests for the Scholar-RAG project.

## Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_parser.py -v
pytest tests/test_checkpoint.py -v
pytest tests/test_rag_deduplication.py -v
```

### Run with coverage report
```bash
pytest tests/ --cov=. --cov-report=html
```

### Run specific test
```bash
pytest tests/test_parser.py::TestDocumentParser::test_chunk_text_basic -v
```

## Test Structure

- **test_parser.py**: Tests for document parsing and chunking functionality
  - CSV loading and validation
  - Text chunking with overlap
  - Metadata preservation

- **test_checkpoint.py**: Tests for scraper checkpoint system
  - Progress tracking and resumption
  - URL deduplication
  - Multi-group handling
  - Data persistence

- **test_rag_deduplication.py**: Tests for RAG engine deduplication
  - Content hashing
  - Hash normalization (case, whitespace)
  - Duplicate detection
  - Hash file persistence

## Test Coverage

The tests cover:
- ✅ Text chunking algorithms
- ✅ CSV parsing and validation
- ✅ Checkpoint save/load operations
- ✅ URL deduplication in scraper
- ✅ Content deduplication in RAG engine
- ✅ Metadata preservation through pipeline
- ✅ Error handling (missing files, invalid data)

## Writing New Tests

Follow these conventions:

1. **File naming**: `test_<module>.py`
2. **Class naming**: `Test<ClassName>`
3. **Method naming**: `test_<functionality>`
4. **Fixtures**: Use `setup_method()` and `teardown_method()`
5. **Assertions**: Use pytest assertions (`assert`, `pytest.raises`)

Example:
```python
class TestMyFeature:
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DocumentParser()

    def test_my_functionality(self):
        """Test description."""
        result = self.parser.some_method()
        assert result == expected_value
```

## Continuous Integration

These tests can be integrated with CI/CD pipelines:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

## Notes

- Some RAG engine tests require `OPENAI_API_KEY` to be set but mock actual API calls
- Scraper tests don't require a browser driver (only testing checkpoint logic)
- All tests use temporary files and clean up after themselves
