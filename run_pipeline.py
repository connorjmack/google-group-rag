#!/usr/bin/env python3
"""
End-to-end pipeline: Scrape → Parse → Ingest → Query

This script demonstrates the complete Scholar-RAG workflow.
"""

import sys
from pathlib import Path
from config import Config
from src.universal_scraper import GoogleGroupsScraper
from parser import DocumentParser
from rag_engine import RAGChatbot
from src.logger import setup_logger

logger = setup_logger("pipeline")


def run_full_pipeline():
    """Execute the complete pipeline from scraping to querying."""

    logger.info("=" * 60)
    logger.info("Starting Scholar-RAG Pipeline")
    logger.info("=" * 60)

    # Step 1: Scrape Google Groups
    logger.info("\n[1/4] SCRAPING Google Groups...")
    try:
        scraper = GoogleGroupsScraper()
        records = scraper.run()
        logger.info(f"✓ Scraped {len(records)} threads")
    except Exception as e:
        logger.error(f"✗ Scraping failed: {e}")
        sys.exit(1)

    # Step 2: Parse and chunk the CSV
    logger.info("\n[2/4] PARSING and chunking scraped data...")
    try:
        parser = DocumentParser()
        csv_path = Config.OUTPUT_FILE

        if not Path(csv_path).exists():
            logger.error(f"CSV file not found: {csv_path}")
            sys.exit(1)

        chunks = parser.process_csv(csv_path)
        logger.info(f"✓ Created {len(chunks)} chunks from {len(records)} threads")
    except Exception as e:
        logger.error(f"✗ Parsing failed: {e}")
        sys.exit(1)

    # Step 3: Ingest into vector database
    logger.info("\n[3/4] INGESTING chunks into vector database...")
    try:
        rag = RAGChatbot()
        rag.ingest(chunks)

        stats = rag.get_stats()
        logger.info(f"✓ Database contains {stats['total_documents']} documents")
    except Exception as e:
        logger.error(f"✗ Ingestion failed: {e}")
        sys.exit(1)

    # Step 4: Interactive query mode
    logger.info("\n[4/4] QUERY MODE - Ask questions about the data")
    logger.info("=" * 60)

    print("\nEnter your questions (or 'quit' to exit):\n")

    while True:
        try:
            question = input("Q: ").strip()

            if question.lower() in ['quit', 'exit', 'q']:
                logger.info("Exiting query mode")
                break

            if not question:
                continue

            result = rag.query(question, return_sources=True)

            print(f"\nA: {result['answer']}\n")

            if 'sources' in result and result['sources']:
                print("Sources:")
                for i, source in enumerate(result['sources'][:3], 1):
                    metadata = source['metadata']
                    print(f"  [{i}] {metadata.get('title', 'Unknown')} "
                          f"by {metadata.get('author', 'Unknown')} "
                          f"({metadata.get('date', 'Unknown')})")
                    print(f"      URL: {metadata.get('url', 'N/A')}\n")

        except KeyboardInterrupt:
            print("\n")
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Query error: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("Pipeline complete!")
    logger.info("=" * 60)


def scrape_only():
    """Run only the scraping step."""
    logger.info("Running scraper only...")
    scraper = GoogleGroupsScraper()
    scraper.run()


def ingest_existing_csv(csv_path: str = None):
    """Ingest an existing CSV file into the vector database."""
    csv_path = csv_path or Config.OUTPUT_FILE

    logger.info(f"Ingesting existing CSV: {csv_path}")

    # Parse
    parser = DocumentParser()
    chunks = parser.process_csv(csv_path)
    logger.info(f"Created {len(chunks)} chunks")

    # Ingest
    rag = RAGChatbot()
    rag.ingest(chunks)

    stats = rag.get_stats()
    logger.info(f"Database now contains {stats['total_documents']} documents")


def query_only():
    """Run only the query interface (assumes data already ingested)."""
    logger.info("Starting query-only mode...")

    rag = RAGChatbot()
    stats = rag.get_stats()

    if stats.get('total_documents', 0) == 0:
        logger.error("No documents in database. Run ingestion first.")
        sys.exit(1)

    logger.info(f"Database contains {stats['total_documents']} documents")
    print("\nEnter your questions (or 'quit' to exit):\n")

    while True:
        try:
            question = input("Q: ").strip()

            if question.lower() in ['quit', 'exit', 'q']:
                break

            if not question:
                continue

            result = rag.query(question, return_sources=True)
            print(f"\nA: {result['answer']}\n")

            if 'sources' in result:
                print("Sources:")
                for i, source in enumerate(result['sources'][:3], 1):
                    metadata = source['metadata']
                    print(f"  [{i}] {metadata.get('title', 'Unknown')}")

        except KeyboardInterrupt:
            print("\n")
            break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scholar-RAG Pipeline")
    parser.add_argument(
        "--mode",
        choices=["full", "scrape", "ingest", "query"],
        default="full",
        help="Pipeline mode (default: full)"
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Path to CSV file for ingestion mode"
    )

    args = parser.parse_args()

    if args.mode == "full":
        run_full_pipeline()
    elif args.mode == "scrape":
        scrape_only()
    elif args.mode == "ingest":
        ingest_existing_csv(args.csv)
    elif args.mode == "query":
        query_only()
