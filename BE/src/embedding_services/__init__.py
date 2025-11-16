"""
Embedding Services Package - Document indexing and vector search
Includes:
- Embedding client: Interface with vLLM OpenAI-compatible embedding service
- Vector store: Qdrant vector database client (each book = one collection)
- Document indexer: Automatic scanning and indexing of new books
"""
from .embedding_client import EmbeddingClient
from .vector_store import VectorStoreClient
from .document_indexer import DocumentIndexer

__all__ = ["EmbeddingClient", "VectorStoreClient", "DocumentIndexer"]