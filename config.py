import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Config:
    # Google Groups Scraper
    TARGET_GROUPS: List[str] = os.getenv("TARGET_GROUPS", "https://groups.google.com/g/carbondioxideremoval").split(",")
    MAX_THREADS_PER_GROUP: int = int(os.getenv("MAX_THREADS_PER_GROUP", "100"))
    OUTPUT_FILE: str = os.getenv("OUTPUT_FILE", "data/google_group_data.csv")
    CHECKPOINT_FILE: str = os.getenv("CHECKPOINT_FILE", "data/scraper_checkpoint.json")

    # Scraper Behavior
    HEADLESS_MODE: bool = os.getenv("HEADLESS_MODE", "false").lower() == "true"
    MIN_DELAY: int = int(os.getenv("MIN_DELAY", "3"))
    MAX_DELAY: int = int(os.getenv("MAX_DELAY", "6"))
    PAGE_LOAD_WAIT: int = int(os.getenv("PAGE_LOAD_WAIT", "5"))

    # RAG Engine
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "data/chroma_db")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    RETRIEVAL_K: int = int(os.getenv("RETRIEVAL_K", "3"))

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "data/scraper.log")
