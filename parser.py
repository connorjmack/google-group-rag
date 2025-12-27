# parser.py
import os
from typing import List, Dict
import PyPDF2  # pip install PyPDF2

class DocumentParser:
    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def load_file(self, filepath: str) -> str:
        """Determines file type and extracts text."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File {filepath} not found.")
            
        if filepath.endswith('.pdf'):
            return self._read_pdf(filepath)
        elif filepath.endswith('.txt') or filepath.endswith('.md'):
            return self._read_text(filepath)
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

    def process_document(self, filepath: str) -> List[Dict]:
        """Orchestrates loading and chunking."""
        raw_text = self.load_file(filepath)
        text_chunks = self.chunk_text(raw_text)
        
        # Return structured data ready for embedding
        return [{"text": chunk, "source": filepath} for chunk in text_chunks]