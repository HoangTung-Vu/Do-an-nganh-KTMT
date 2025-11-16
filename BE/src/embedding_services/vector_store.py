"""
Vector Store Client - Interface with Qdrant vector database
"""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest
)
from ..utils.logger import setup_logger
from ..utils.load_config import load_config

logger = setup_logger('vector_store', 'embedding.log')


class VectorStoreClient:
    """Client for Qdrant vector database - Each book is a separate collection"""
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Qdrant client
        
        Args:
            url: Qdrant server URL (e.g., http://ec2-instance:6333)
            api_key: API key for authentication (optional)
            config: Configuration dict (if None, loads from config.yaml)
        """
        # Load config if not provided
        if config is None:
            config = load_config()
        
        vector_config = config.get('vector_store', {})
        
        self.url = url or vector_config.get('url', 'http://localhost:6333')
        self.api_key = api_key or vector_config.get('api_key')
        
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=60
        )
        
        logger.info(f"Qdrant client initialized: {self.url}")
    
    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists
        
        Args:
            collection_name: Name of the collection to check
            
        Returns:
            True if collection exists, False otherwise
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            exists = collection_name in collection_names
            logger.debug(f"Collection '{collection_name}' exists: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Error checking collection existence: {str(e)}")
            return False
    
    def create_collection(self, collection_name: str, vector_size: int, distance: Distance = Distance.COSINE):
        """
        Create a new collection if it doesn't exist
        
        Args:
            collection_name: Name of the collection to create
            vector_size: Dimension of the vectors
            distance: Distance metric (COSINE, EUCLID, DOT)
        """
        try:
            # Check if collection exists
            if self.collection_exists(collection_name):
                logger.info(f"Collection '{collection_name}' already exists")
                return
            
            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            logger.info(f"Created collection '{collection_name}' with vector size {vector_size}")
            
        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            raise
    
    def upsert_points(
        self,
        collection_name: str,
        points: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        Insert or update points in the collection
        
        Args:
            collection_name: Name of the collection
            points: List of dictionaries with 'id', 'vector', and 'payload' keys
            batch_size: Number of points to upsert in each batch
            
        Returns:
            Number of points upserted
        """
        try:
            total_points = len(points)
            logger.info(f"Upserting {total_points} points to '{collection_name}'")
            
            # Prepare PointStruct objects
            point_structs = [
                PointStruct(
                    id=point['id'],
                    vector=point['vector'],
                    payload=point.get('payload', {})
                )
                for point in points
            ]
            
            # Upsert in batches
            for i in range(0, len(point_structs), batch_size):
                batch = point_structs[i:i + batch_size]
                self.client.upsert(
                    collection_name=collection_name,
                    points=batch
                )
                logger.debug(f"Upserted batch {i//batch_size + 1}/{(len(point_structs)-1)//batch_size + 1}")
            
            logger.info(f"Successfully upserted {total_points} points")
            return total_points
            
        except Exception as e:
            logger.error(f"Error upserting points: {str(e)}")
            raise
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors
        
        Args:
            collection_name: Name of the collection to search in
            query_vector: Query vector to search for
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score threshold
            filter_conditions: Optional filters on payload fields
            
        Returns:
            List of search results with id, score, and payload
        """
        try:
            # Build filter if provided
            query_filter = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                query_filter = Filter(must=conditions)
            
            # Perform search
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter
            )
            
            # Format results
            results = []
            for hit in search_results:
                results.append({
                    'id': hit.id,
                    'score': hit.score,
                    'payload': hit.payload
                })
            
            logger.info(f"Search in '{collection_name}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise
    
    def delete_by_filter(self, collection_name: str, filter_conditions: Dict[str, Any]) -> int:
        """
        Delete points matching filter conditions
        
        Args:
            collection_name: Name of the collection
            filter_conditions: Filters on payload fields
            
        Returns:
            Number of points deleted (approximate)
        """
        try:
            conditions = []
            for key, value in filter_conditions.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            
            query_filter = Filter(must=conditions)
            
            self.client.delete(
                collection_name=collection_name,
                points_selector=query_filter
            )
            
            logger.info(f"Deleted points from '{collection_name}' matching filter: {filter_conditions}")
            return 0  # Qdrant doesn't return count
            
        except Exception as e:
            logger.error(f"Error deleting points: {str(e)}")
            raise
    
    def delete_collection(self, collection_name: str):
        """
        Delete an entire collection
        
        Args:
            collection_name: Name of the collection to delete
        """
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
            
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about the collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection metadata including point count and vector config
        """
        try:
            info = self.client.get_collection(collection_name=collection_name)
            return {
                'name': collection_name,
                'points_count': info.points_count,
                'vector_size': info.config.params.vectors.size,
                'distance': info.config.params.vectors.distance.name
            }
            
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            raise
    
    def list_collections(self) -> List[str]:
        """
        List all collections in the database
        
        Returns:
            List of collection names
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            logger.info(f"Found {len(collection_names)} collections")
            return collection_names
            
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            raise
