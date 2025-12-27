# parser.py
import os
import csv
from typing import List, Dict
import PyPDF2  # pip install PyPDF2
import pandas as pd  # pip install pandas
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from config import Config

class DocumentParser:
    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or Config.CHUNK_SIZE
        self.overlap = overlap or Config.CHUNK_OVERLAP

    def load_file(self, filepath: str) -> str:
        """Determines file type and extracts text."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File {filepath} not found.")

        if filepath.endswith('.pdf'):
            return self._read_pdf(filepath)
        elif filepath.endswith('.txt') or filepath.endswith('.md'):
            return self._read_text(filepath)
        elif filepath.endswith('.csv'):
            raise ValueError("Use load_csv() for CSV files instead of load_file()")
        else:
            raise ValueError("Unsupported file type")

    def _read_pdf(self, filepath: str) -> str:
        text = ""
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _read_text(self, filepath: str) -> str:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def chunk_text(self, text: str) -> List[str]:
        """Splits text into chunks with overlap."""
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            # Move forward by chunk_size minus the overlap
            start += (self.chunk_size - self.overlap)
        
        return chunks

    def load_csv(self, filepath: str) -> List[Dict]:
        """
        Load scraped Google Groups CSV data.

        Args:
            filepath: Path to CSV file from universal_scraper.py

        Returns:
            List of dictionaries with text content and metadata
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"CSV file {filepath} not found.")

        df = pd.read_csv(filepath, encoding='utf-8')

        # Validate required columns
        required_cols = ['content', 'title', 'url']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"CSV missing required columns: {missing_cols}")

        records = []
        for idx, row in df.iterrows():
            # Handle missing values
            content = str(row.get('content', '')).strip()
            if not content or content == 'nan':
                continue

            record = {
                'text': content,
                'title': str(row.get('title', 'Unknown')),
                'url': str(row.get('url', '')),
                'date': str(row.get('date', 'Unknown')),
                'author': str(row.get('author', 'Unknown')),
                'group_url': str(row.get('group_url', ''))
            }
            records.append(record)

        return records

    def process_csv(self, filepath: str) -> List[Dict]:
        """
        Process CSV file by loading and chunking each thread's content.

        Args:
            filepath: Path to CSV file

        Returns:
            List of chunked documents with metadata
        """
        records = self.load_csv(filepath)
        chunked_docs = []

        for record in records:
            # Chunk the content
            chunks = self.chunk_text(record['text'])

            # Create metadata for each chunk
            for i, chunk in enumerate(chunks):
                chunked_doc = {
                    'text': chunk,
                    'source': filepath,
                    'title': record['title'],
                    'url': record['url'],
                    'date': record['date'],
                    'author': record['author'],
                    'group_url': record['group_url'],
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
                chunked_docs.append(chunked_doc)

        return chunked_docs

    def process_document(self, filepath: str) -> List[Dict]:
        """Orchestrates loading and chunking based on file type."""
        if filepath.endswith('.csv'):
            return self.process_csv(filepath)

        raw_text = self.load_file(filepath)
        text_chunks = self.chunk_text(raw_text)

        # Return structured data ready for embedding
        return [{"text": chunk, "source": filepath} for chunk in text_chunks]