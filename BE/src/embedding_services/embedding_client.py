"""
Embedding Client - Interface with vLLM OpenAI-compatible embedding service
"""
from typing import List, Dict, Any, Optional
from openai import OpenAI
from ..utils.logger import setup_logger
from ..utils.load_config import load_config

logger = setup_logger('embedding_client', 'embedding.log')


class EmbeddingClient:
    """Client for vLLM embedding service with OpenAI-compatible API"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize embedding client
        
        Args:
            base_url: vLLM server URL (e.g., http://localhost:8000/v1)
            api_key: API key for authentication (can be dummy for vLLM)
            model: Model name to use for embeddings
            max_retries: Maximum number of retries on failure
            timeout: Request timeout in seconds
            config: Configuration dict (if None, loads from config.yaml)
        """
        # Load config if not provided
        if config is None:
            config = load_config()
        
        embedding_config = config.get('embedding', {})
        
        self.base_url = base_url or embedding_config.get('base_url', 'http://localhost:8000/v1')
        self.api_key = api_key or embedding_config.get('api_key', 'EMPTY')
        self.model = model or embedding_config.get('model', 'BAAI/bge-m3')
        self.max_retries = max_retries or embedding_config.get('max_retries', 3)
        self.timeout = timeout or embedding_config.get('timeout', 60)
        
        # Initialize OpenAI client pointing to vLLM
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            max_retries=self.max_retries,
            timeout=self.timeout
        )
        
        logger.info(f"Embedding client initialized: {self.base_url} | Model: {self.model}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for text (length: {len(text)} chars, dim: {len(embedding)})")
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            embeddings = [item.embedding for item in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings (dim: {len(embeddings[0]) if embeddings else 0})")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings from this model
        
        Returns:
            Embedding dimension size
        """
        try:
            # Generate a test embedding to determine dimension
            test_embedding = self.embed_text("test")
            dim = len(test_embedding)
            logger.info(f"Embedding dimension: {dim}")
            return dim
            
        except Exception as e:
            logger.error(f"Error getting embedding dimension: {str(e)}")
            raise
