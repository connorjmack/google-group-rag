# Scholar-RAG: Community Archive Ingestion Pipeline

## Overview
Scholar-RAG is a production-ready data ingestion and retrieval framework designed to extract, structure, and index technical knowledge from distributed community archives.

While formal academic literature is easily accessible via standard APIs, a significant volume of specialized domain knowledge—particularly in fields like climate modeling, energy systems, and geospatial analysis—resides in unstructured mailing lists and Google Groups. This repository provides a generalized pipeline to harvest these "dark data" sources, converting threaded email discussions into a structured corpus suitable for Retrieval-Augmented Generation (RAG) applications.

## Repository Structure
The pipeline consists of three integrated modules:
1.  **Scraper** (`src/universal_scraper.py`): Production-grade Selenium-based scraper with pagination, checkpointing, and robust error handling
2.  **Parser** (`parser.py`): Document processor that chunks text and preserves metadata for optimal retrieval
3.  **RAG Engine** (`rag_engine.py`): OpenAI-powered question-answering system with Chroma vector database

## Key Features

### Scraping
* **Pagination Support:** Automatically navigates through multiple pages to scrape entire group archives
* **Checkpoint/Resume:** Crash-resistant with automatic progress saving and resume capability
* **URL Deduplication:** Tracks scraped URLs to avoid re-scraping the same threads across runs
* **Smart Content Extraction:** Multiple fallback selectors for robust message extraction
* **Author Metadata:** Captures author, date, and URL information for source attribution
* **Configurable Delays:** Ethical crawling with randomized delays (3-6s default)

### Data Processing
* **Intelligent Chunking:** Text splitting with configurable overlap for context preservation
* **Metadata Preservation:** Thread titles, authors, dates, and URLs attached to each chunk
* **Multi-Format Support:** CSV (Google Groups), PDF, and plain text

### RAG System
* **Vector Similarity Search:** Chroma database with OpenAI embeddings
* **Content Deduplication:** SHA-256 hashing to detect and skip duplicate content during ingestion
* **Source Attribution:** Responses include citations with author and date information
* **Production-Ready:** Full error handling, logging, and batch processing
* **Customizable Prompts:** Tailored for community discussion context

## Installation

### 1. Using Conda (Recommended)
```bash
conda env create -f environment.yml
conda activate scholar-rag
```

### 2. Using pip
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the example environment file and add your OpenAI API key:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key (required for embeddings and LLM)
- `TARGET_GROUPS`: Comma-separated Google Group URLs to scrape
- `MAX_THREADS_PER_GROUP`: Maximum threads to scrape per group (default: 100)

## Quick Start

### Option 1: Run Full Pipeline (Scrape → Parse → Ingest → Query)
```bash
python run_pipeline.py --mode full
```

This will:
1. Scrape configured Google Groups
2. Parse and chunk the content
3. Ingest into vector database
4. Start interactive Q&A mode

### Option 2: Run Individual Steps

**Scrape only:**
```bash
python run_pipeline.py --mode scrape
# or
python src/universal_scraper.py
```

**Ingest existing CSV:**
```bash
python run_pipeline.py --mode ingest --csv data/google_group_data.csv
```

**Query only (requires existing database):**
```bash
python run_pipeline.py --mode query
```

## Detailed Usage

### 1. Scraping Google Groups

The scraper supports:
- Multiple groups (configured in `.env`)
- Automatic pagination
- Checkpoint/resume on crashes
- Author and metadata extraction

```python
from src.universal_scraper import GoogleGroupsScraper

scraper = GoogleGroupsScraper(headless=True)
records = scraper.run()
# Output: data/google_group_data.csv
```

**Resume from checkpoint:**
If the scraper crashes, simply re-run it. It will automatically resume from the last checkpoint saved in `data/scraper_checkpoint.json`.

### 2. Parsing and Chunking

Process the scraped CSV into chunked documents:

```python
from parser import DocumentParser

parser = DocumentParser(chunk_size=1000, overlap=100)
chunks = parser.process_csv("data/google_group_data.csv")

# Each chunk contains:
# - text: The content chunk
# - title: Thread title
# - author: Post author
# - date: Post date
# - url: Thread URL
# - chunk_index: Position in thread
```

### 3. RAG System

Initialize and query the RAG system:

```python
from rag_engine import RAGChatbot

# Initialize (creates/loads vector DB)
rag = RAGChatbot()

# Ingest documents
rag.ingest(chunks)

# Query
result = rag.query("What are the main challenges in carbon dioxide removal?")
print(result['answer'])

# View sources
for source in result['sources']:
    print(f"- {source['metadata']['title']} by {source['metadata']['author']}")
```

**Database management:**
```python
# Get statistics
stats = rag.get_stats()
print(f"Total documents: {stats['total_documents']}")

# Clear database
rag.clear_database()

# Persist manually (auto-persists after ingestion)
rag.persist()
```

## Configuration

All settings are managed via `.env` file and `config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_GROUPS` | carbondioxideremoval | Comma-separated Google Group URLs |
| `MAX_THREADS_PER_GROUP` | 100 | Max threads to scrape per group |
| `HEADLESS_MODE` | false | Run browser invisibly |
| `MIN_DELAY` / `MAX_DELAY` | 3 / 6 | Request delay range (seconds) |
| `CHUNK_SIZE` | 1000 | Characters per chunk |
| `CHUNK_OVERLAP` | 100 | Overlap between chunks |
| `RETRIEVAL_K` | 3 | Number of chunks to retrieve |
| `EMBEDDING_MODEL` | text-embedding-3-small | OpenAI embedding model |
| `LLM_MODEL` | gpt-4-turbo-preview | OpenAI LLM model |

## Project Structure

```
google-group-rag/
├── config.py                 # Configuration loader
├── .env.example             # Example environment variables
├── run_pipeline.py          # End-to-end pipeline script
├── parser.py                # Document parsing and chunking
├── rag_engine.py            # RAG chatbot implementation
├── requirements.txt         # Python dependencies
├── src/
│   ├── logger.py           # Logging configuration
│   └── universal_scraper.py # Google Groups scraper
├── data/                    # Output directory (gitignored)
│   ├── google_group_data.csv
│   ├── scraper_checkpoint.json
│   ├── chroma_db/          # Vector database
│   └── scraper.log         # Log file
└── notebooks/              # Jupyter notebooks for exploration
```

## Logging

All components use structured logging:
- **Console output:** INFO level and above
- **Log file:** `data/scraper.log` - DEBUG level for troubleshooting
- **Log level:** Configure via `LOG_LEVEL` in `.env`

## Best Practices

1. **Start small:** Test with `MAX_THREADS_PER_GROUP=5` first
2. **Monitor logs:** Check `data/scraper.log` for detailed progress
3. **Use checkpoints:** Don't delete `scraper_checkpoint.json` until scraping is complete
4. **Rate limiting:** Default delays (3-6s) are conservative; adjust if needed
5. **API costs:** Monitor OpenAI usage - embeddings cost ~$0.13 per 1M tokens

## Troubleshooting

**Scraper fails with "Element not found":**
- Google Groups UI may have changed
- Check logs for specific selector that failed
- Try running without `--headless` to see browser

**"No documents in database" error:**
- Run ingestion step first: `python run_pipeline.py --mode ingest`
- Verify CSV file exists: `ls data/google_group_data.csv`

**OpenAI API errors:**
- Verify `OPENAI_API_KEY` is set correctly in `.env`
- Check API quota and billing status
- Reduce batch size if rate limited

## Examples

### Scrape Multiple Groups
Edit `.env`:
```
TARGET_GROUPS=https://groups.google.com/g/carbondioxideremoval,https://groups.google.com/g/pangeo
```

### Custom Chunk Size for Technical Content
```python
parser = DocumentParser(chunk_size=1500, overlap=200)
chunks = parser.process_csv("data/google_group_data.csv")
```

### Query with More Context
Edit `.env`:
```
RETRIEVAL_K=5  # Retrieve 5 chunks instead of 3
```

## Deduplication

Scholar-RAG implements two-level deduplication to avoid wasting resources:

### URL-Level Deduplication (Scraper)
- Tracks all scraped thread URLs in `data/scraper_checkpoint.json`
- Automatically skips threads that have already been scraped
- Persists across multiple scraping sessions
- Prevents re-downloading the same content

**How it works:**
```python
# URLs are tracked in checkpoint file
{
  "scraped_urls": [
    "https://groups.google.com/g/group1/c/thread1",
    "https://groups.google.com/g/group1/c/thread2"
  ]
}
```

### Content-Level Deduplication (RAG Engine)
- Uses SHA-256 hashing of normalized text content
- Detects duplicate chunks even if they come from different sources
- Normalization handles case differences and whitespace variations
- Hashes stored in `data/chroma_db/content_hashes.txt`

**How it works:**
```python
# Text normalization before hashing
"  Hello   World  " → "hello world" → SHA-256 hash

# Duplicate detection
if content_hash in existing_hashes:
    skip_document()
```

**Benefits:**
- Reduces vector database size (saves storage and API costs)
- Faster retrieval (fewer vectors to search)
- No duplicate results in answers
- Resume scraping without re-processing

**Disable deduplication** (not recommended):
```python
# In RAG ingestion
rag.ingest(chunks, skip_duplicates=False)
```

## Testing

The project includes comprehensive unit tests covering core functionality.

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_parser.py -v
```

### Test Coverage
- ✅ **Parser**: CSV loading, text chunking, metadata preservation
- ✅ **Checkpoint**: Progress tracking, URL deduplication, persistence
- ✅ **RAG Deduplication**: Content hashing, normalization, duplicate detection
- ✅ **Error Handling**: Missing files, invalid data, edge cases

See `tests/README.md` for detailed testing documentation.

### Writing Tests
Example test structure:
```python
def test_chunk_text():
    parser = DocumentParser(chunk_size=20, overlap=5)
    chunks = parser.chunk_text("Hello world test")
    assert len(chunks) > 0
    assert len(chunks[0]) <= 20
```

## Performance & Costs

### Scraping Performance
- **Speed**: ~3-6 seconds per thread (configurable)
- **Throughput**: ~600-1200 threads/hour
- **Resume capability**: Zero overhead for crashes

### RAG Engine Costs (OpenAI)
- **Embeddings**: ~$0.13 per 1M tokens (text-embedding-3-small)
- **LLM**: ~$10 per 1M tokens (GPT-4 Turbo)
- **Example**: 1000 threads (~500K tokens) ≈ $0.07 for embeddings

**Cost savings from deduplication:**
- URL deduplication: Saves 100% of duplicate thread scraping time
- Content deduplication: Typically 5-15% savings on embedding costs

## License
This project is licensed under the terms specified in the LICENSE file