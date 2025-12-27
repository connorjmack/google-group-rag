# __init__.py

# This allows you to do:
# from my_package import DocumentParser, RAGChatbot
# Instead of:
# from my_package.parser import DocumentParser
# from my_package.rag_engine import RAGChatbot

from .parser import DocumentParser
from .rag_engine import RAGChatbot

__all__ = ["DocumentParser", "RAGChatbot"]