"""
API Endpoints for Embedding and Indexing
"""
import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.embedding_services import EmbeddingClient, VectorStoreClient, DocumentIndexer
from src.utils.logger import setup_logger

router = APIRouter(prefix="/embedding", tags=["Embedding & Indexing"])
logger = setup_logger('embedding_api', 'embedding.log')


# Global instances (singleton pattern)
_embedding_client: Optional[EmbeddingClient] = None
_vector_store: Optional[VectorStoreClient] = None
_document_indexer: Optional[DocumentIndexer] = None


def get_embedding_client() -> EmbeddingClient:
    """Get or create embedding client singleton"""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client


def get_vector_store() -> VectorStoreClient:
    """Get or create vector store singleton"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreClient()
    return _vector_store


def get_document_indexer() -> DocumentIndexer:
    """Get or create document indexer singleton"""
    global _document_indexer
    if _document_indexer is None:
        _document_indexer = DocumentIndexer(
            embedding_client=get_embedding_client(),
            vector_store=get_vector_store()
        )
    return _document_indexer


# Request/Response Models
class IndexBookRequest(BaseModel):
    """Request model for indexing a book"""
    book_name: str
    user_id: str
    force_reindex: bool = False


class SearchRequest(BaseModel):
    """Request model for vector search"""
    collection_name: str  # This is now the user_id
    query: str
    limit: int = 10
    score_threshold: Optional[float] = None


class SearchResponse(BaseModel):
    """Response model for search results"""
    results: List[Dict[str, Any]]
    total: int


# Endpoints
@router.post("/scan-and-index")
async def scan_and_index_books(background_tasks: BackgroundTasks):
    """
    Scan data directory and index all new books
    This runs in the background
    """
    try:
        indexer = get_document_indexer()
        
        # Run indexing in background
        background_tasks.add_task(indexer.index_all_new_books)
        
        # Get list of books that will be indexed
        new_books = indexer.scan_new_books()
        
        return {
            "message": f"Indexing started for {len(new_books)} books",
            "books": new_books,
            "status": "in_progress"
        }
        
    except Exception as e:
        logger.error(f"Error in scan_and_index: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index-book")
async def index_book(request: IndexBookRequest):
    """
    Index a specific book
    
    Args:
        book_name: Name of the book to index
        user_id: ID of the user who owns the book
        force_reindex: If True, re-index even if already exists
    """
    try:
        indexer = get_document_indexer()
        
        if request.force_reindex:
            result = indexer.reindex_book(request.book_name, request.user_id)
        else:
            # Check if already indexed (check if book exists in user's collection)
            # Note: This check is trickier now since collection is user_id.
            # We would need to query if book_name exists in payload.
            # For now, let's just trust the indexer or force reindex.
            # Or we can check if collection exists, but that just means user exists.
            
            # Simplified: Just call index_book, it will upsert.
            result = indexer.index_book(request.book_name, request.user_id)
        
        return {
            "message": f"Successfully indexed book '{request.book_name}'",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing book: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections")
async def list_collections():
    """
    List all indexed collections (books)
    """
    try:
        vector_store = get_vector_store()
        collections = vector_store.list_collections()
        
        # Get info for each collection
        collection_info = []
        for coll_name in collections:
            try:
                info = vector_store.get_collection_info(coll_name)
                collection_info.append(info)
            except Exception as e:
                logger.warning(f"Could not get info for collection '{coll_name}': {str(e)}")
        
        return {
            "total": len(collections),
            "collections": collection_info
        }
        
    except Exception as e:
        logger.error(f"Error listing collections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collection/{collection_name}")
async def get_collection_info(collection_name: str):
    """
    Get information about a specific collection
    """
    try:
        vector_store = get_vector_store()
        
        if not vector_store.collection_exists(collection_name):
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        info = vector_store.get_collection_info(collection_name)
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Search for similar documents in a collection
    
    Args:
        collection_name: Name of the collection (user_id) to search in
        query: Search query text
        limit: Maximum number of results
        score_threshold: Minimum similarity score
    """
    try:
        vector_store = get_vector_store()
        embedding_client = get_embedding_client()
        
        # Check if collection exists
        if not vector_store.collection_exists(request.collection_name):
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{request.collection_name}' not found"
            )
        
        # Generate query embedding
        query_vector = embedding_client.embed_text(request.query)
        
        # Search
        results = vector_store.search(
            collection_name=request.collection_name,
            query_vector=query_vector,
            limit=request.limit,
            score_threshold=request.score_threshold
        )
        
        return SearchResponse(
            results=results,
            total=len(results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collection/{collection_name}")
async def delete_collection(collection_name: str):
    """
    Delete a collection (book index)
    """
    try:
        vector_store = get_vector_store()
        
        if not vector_store.collection_exists(collection_name):
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        vector_store.delete_collection(collection_name)
        
        return {
            "message": f"Collection '{collection_name}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Check health of embedding and vector store services
    """
    try:
        embedding_client = get_embedding_client()
        vector_store = get_vector_store()
        
        # Test embedding service
        try:
            _ = embedding_client.embed_text("test")
            embedding_status = "healthy"
        except Exception as e:
            embedding_status = f"unhealthy: {str(e)}"
        
        # Test vector store
        try:
            _ = vector_store.list_collections()
            vector_store_status = "healthy"
        except Exception as e:
            vector_store_status = f"unhealthy: {str(e)}"
        
        overall_healthy = embedding_status == "healthy" and vector_store_status == "healthy"
        
        return {
            "status": "healthy" if overall_healthy else "degraded",
            "embedding_service": embedding_status,
            "vector_store": vector_store_status
        }
        
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
