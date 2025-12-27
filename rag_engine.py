# rag_engine.py
from typing import List, Dict, Optional, Set
import os
import sys
import hashlib
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from config import Config
from src.logger import setup_logger

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

logger = setup_logger("rag_engine")


class RAGChatbot:
    """RAG-powered chatbot using Chroma vector DB and OpenAI."""

    def __init__(self, vector_db_path: str = None, api_key: str = None):
        """
        Initialize the RAG chatbot.

        Args:
            vector_db_path: Path to Chroma database directory
            api_key: OpenAI API key (defaults to Config.OPENAI_API_KEY)
        """
        self.vector_db_path = vector_db_path or Config.VECTOR_DB_PATH
        self.api_key = api_key or Config.OPENAI_API_KEY

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY in .env file."
            )

        logger.info("Initializing RAG engine...")

        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=Config.EMBEDDING_MODEL,
            openai_api_key=self.api_key
        )
        logger.info(f"Using embedding model: {Config.EMBEDDING_MODEL}")

        # Initialize or load vector store
        db_path = Path(self.vector_db_path)
        db_path.mkdir(parents=True, exist_ok=True)

        self.vector_store = Chroma(
            persist_directory=str(db_path),
            embedding_function=self.embeddings,
            collection_name="google_groups"
        )
        logger.info(f"Vector store initialized at {self.vector_db_path}")

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            temperature=Config.LLM_TEMPERATURE,
            openai_api_key=self.api_key
        )
        logger.info(f"Using LLM model: {Config.LLM_MODEL}")

        # Initialize QA chain
        self._setup_qa_chain()

        # Track content hashes for deduplication
        self.content_hashes: Set[str] = self._load_content_hashes()

    def _get_hash_file_path(self) -> Path:
        """Get path to content hashes file."""
        return Path(self.vector_db_path) / "content_hashes.txt"

    def _load_content_hashes(self) -> Set[str]:
        """Load previously ingested content hashes from disk."""
        hash_file = self._get_hash_file_path()
        if hash_file.exists():
            with open(hash_file, 'r') as f:
                hashes = set(line.strip() for line in f if line.strip())
                logger.info(f"Loaded {len(hashes)} content hashes for deduplication")
                return hashes
        return set()

    def _save_content_hashes(self):
        """Save content hashes to disk."""
        hash_file = self._get_hash_file_path()
        hash_file.parent.mkdir(parents=True, exist_ok=True)
        with open(hash_file, 'w') as f:
            for hash_val in sorted(self.content_hashes):
                f.write(f"{hash_val}\n")
        logger.debug(f"Saved {len(self.content_hashes)} content hashes")

    def _compute_content_hash(self, text: str) -> str:
        """
        Compute SHA-256 hash of normalized text content.

        Args:
            text: Text content to hash

        Returns:
            Hexadecimal hash string
        """
        # Normalize: lowercase, strip whitespace, remove multiple spaces
        normalized = ' '.join(text.lower().split())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def _setup_qa_chain(self):
        """Set up the RetrievalQA chain with custom prompt."""
        template = """You are a helpful assistant answering questions about discussions from Google Groups mailing lists.

Use the following context from community discussions to answer the question. If you don't know the answer based on the context, say so. Include relevant details like author names and dates when available.

Context:
{context}

Question: {question}

Answer:"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(
                search_kwargs={"k": Config.RETRIEVAL_K}
            ),
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True
        )
        logger.debug("QA chain configured")

    def ingest(self, documents: List[Dict], batch_size: int = 100, skip_duplicates: bool = True):
        """
        Ingest processed chunks from parser.py into the vector DB.

        Args:
            documents: List of document dictionaries with 'text' and metadata
            batch_size: Number of documents to process at once
            skip_duplicates: Whether to skip duplicate content (default: True)
        """
        if not documents:
            logger.warning("No documents to ingest")
            return

        logger.info(f"Processing {len(documents)} chunks for ingestion...")

        # Convert to LangChain Document objects, checking for duplicates
        docs = []
        duplicates_skipped = 0

        for doc in documents:
            text = doc.get("text", "")
            if not text.strip():
                continue

            # Check for duplicate content
            if skip_duplicates:
                content_hash = self._compute_content_hash(text)
                if content_hash in self.content_hashes:
                    duplicates_skipped += 1
                    logger.debug(f"Skipping duplicate content (hash: {content_hash[:8]}...)")
                    continue
                # Add to hash set
                self.content_hashes.add(content_hash)

            # Extract metadata (exclude 'text' field)
            metadata = {k: v for k, v in doc.items() if k != "text"}
            docs.append(Document(page_content=text, metadata=metadata))

        if duplicates_skipped > 0:
            logger.info(f"Skipped {duplicates_skipped} duplicate chunks")

        if not docs:
            logger.warning("No new documents to ingest (all were duplicates)")
            return

        logger.info(f"Ingesting {len(docs)} unique chunks...")

        # Batch ingestion
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            self.vector_store.add_documents(batch)
            logger.info(f"Ingested batch {i//batch_size + 1}: {len(batch)} documents")

        # Persist to disk
        self.vector_store.persist()
        self._save_content_hashes()
        logger.info(f"Ingestion complete. Added {len(docs)} new documents (skipped {duplicates_skipped} duplicates)")

    def retrieve(self, query: str, k: int = None) -> List[Document]:
        """
        Search the vector DB for the top k most relevant text chunks.

        Args:
            query: Search query
            k: Number of results to return (defaults to Config.RETRIEVAL_K)

        Returns:
            List of Document objects with content and metadata
        """
        k = k or Config.RETRIEVAL_K
        logger.debug(f"Retrieving top {k} documents for query: {query[:50]}...")

        try:
            results = self.vector_store.similarity_search(query, k=k)
            logger.info(f"Retrieved {len(results)} documents")
            return results
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []

    def query(self, user_question: str, return_sources: bool = True) -> Dict:
        """
        Execute the full RAG pipeline: retrieve context and generate answer.

        Args:
            user_question: User's question
            return_sources: Whether to include source documents in response

        Returns:
            Dictionary with 'answer' and optionally 'sources'
        """
        logger.info(f"Processing query: {user_question[:100]}...")

        try:
            result = self.qa_chain.invoke({"query": user_question})

            response = {
                "answer": result["result"],
                "question": user_question
            }

            if return_sources and "source_documents" in result:
                sources = []
                for doc in result["source_documents"]:
                    source = {
                        "content": doc.page_content[:200] + "...",
                        "metadata": doc.metadata
                    }
                    sources.append(source)
                response["sources"] = sources

            logger.info("Query completed successfully")
            return response

        except Exception as e:
            logger.error(f"Error during query: {e}", exc_info=True)
            return {
                "answer": f"Error processing query: {str(e)}",
                "question": user_question
            }

    def persist(self):
        """Explicitly save vector DB to disk."""
        logger.info("Persisting vector database...")
        self.vector_store.persist()
        logger.info("Database persisted")

    def clear_database(self):
        """Clear all vectors and content hashes from the database."""
        logger.warning("Clearing entire vector database...")
        # Delete and recreate the collection
        self.vector_store.delete_collection()
        self.vector_store = Chroma(
            persist_directory=self.vector_db_path,
            embedding_function=self.embeddings,
            collection_name="google_groups"
        )
        # Clear content hashes
        self.content_hashes.clear()
        hash_file = self._get_hash_file_path()
        if hash_file.exists():
            hash_file.unlink()
        logger.info("Database and deduplication hashes cleared")

    def get_stats(self) -> Dict:
        """
        Get statistics about the vector database.

        Returns:
            Dictionary with database statistics
        """
        try:
            collection = self.vector_store._collection
            count = collection.count()

            stats = {
                "total_documents": count,
                "unique_content_hashes": len(self.content_hashes),
                "database_path": self.vector_db_path,
                "embedding_model": Config.EMBEDDING_MODEL,
                "llm_model": Config.LLM_MODEL
            }

            logger.debug(f"Database stats: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}