"""
Document Indexer - Automatically index new books from data directory
"""
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from .embedding_client import EmbeddingClient
from .vector_store import VectorStoreClient
from ..utils.logger import setup_logger
from ..utils.load_config import load_config

logger = setup_logger('document_indexer', 'embedding.log')


class DocumentIndexer:
    """Automatically scan and index documents from data directory"""
    
    def __init__(
        self,
        data_dir: Optional[str] = None,
        embedding_client: Optional[EmbeddingClient] = None,
        vector_store: Optional[VectorStoreClient] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize document indexer
        
        Args:
            data_dir: Root directory containing book subfolders
            embedding_client: EmbeddingClient instance
            vector_store: VectorStoreClient instance
            chunk_size: Maximum number of words per chunk
            chunk_overlap: Number of overlapping words between chunks
            config: Configuration dict (if None, loads from config.yaml)
        """
        # Load config if not provided
        if config is None:
            config = load_config()
        
        indexing_config = config.get('indexing', {})
        
        self.data_dir = Path(data_dir or indexing_config.get('data_dir', './data'))
        self.chunk_size = chunk_size or indexing_config.get('chunk_size', 512)
        self.chunk_overlap = chunk_overlap or indexing_config.get('chunk_overlap', 50)
        
        # Use provided clients or create new ones with config
        self.embedding_client = embedding_client or EmbeddingClient(config=config)
        self.vector_store = vector_store or VectorStoreClient(config=config)
        
        logger.info(f"Document indexer initialized: {self.data_dir}")
    
    def scan_new_books(self) -> List[str]:
        """
        Scan data directory for new books that haven't been indexed
        
        Returns:
            List of book names (subfolder names) that need indexing
        """
        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {self.data_dir}")
            return []
        
        # Get all subfolders in data directory
        subfolders = [
            f.name for f in self.data_dir.iterdir() 
            if f.is_dir() and not f.name.startswith('.') and f.name != 'uploads'
        ]
        
        # Get existing collections
        existing_collections = self.vector_store.list_collections()
        
        # Find books that are not indexed yet
        new_books = [book for book in subfolders if book not in existing_collections]
        
        logger.info(f"Found {len(subfolders)} books, {len(new_books)} need indexing")
        return new_books
    
    def index_book(self, book_name: str) -> Dict[str, Any]:
        """
        Index a single book
        
        Args:
            book_name: Name of the book (subfolder name)
            
        Returns:
            Indexing statistics
        """
        logger.info(f"Starting indexing for book: {book_name}")
        
        book_dir = self.data_dir / book_name
        json_file = book_dir / f"{book_name}.json"
        
        if not json_file.exists():
            logger.error(f"Book metadata not found: {json_file}")
            raise FileNotFoundError(f"Book metadata not found: {json_file}")
        
        # Load book data
        with open(json_file, 'r', encoding='utf-8') as f:
            book_data = json.load(f)
        
        logger.info(f"Loaded book: {book_data['book_name']} with {book_data['total_chapters']} chapters")
        
        # Prepare chunks for embedding
        chunks = []
        for chapter in book_data['chapters']:
            chapter_chunks = self._create_chunks(
                text=chapter['content'],
                chapter_id=chapter['chapter_id'],
                chapter_title=chapter['title'],
                book_name=book_name
            )
            chunks.extend(chapter_chunks)
        
        logger.info(f"Created {len(chunks)} chunks from {book_data['total_chapters']} chapters")
        
        # Get batch size from config
        if config is None:
            config = load_config()
        batch_size = config.get('embedding', {}).get('batch_size', 32)
        
        # Generate embeddings
        texts = [chunk['text'] for chunk in chunks]
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        
        embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc=f"Embedding {book_name}"):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.embedding_client.embed_texts(batch_texts)
            embeddings.extend(batch_embeddings)
        
        # Get embedding dimension and create collection
        vector_dim = len(embeddings[0]) if embeddings else 768
        self.vector_store.create_collection(book_name, vector_dim)
        
        # Prepare points for Qdrant
        points = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = self._generate_point_id(book_name, chunk['chapter_id'], idx)
            
            points.append({
                'id': point_id,
                'vector': embedding,
                'payload': {
                    'book_name': book_name,
                    'chapter_id': chunk['chapter_id'],
                    'chapter_title': chunk['chapter_title'],
                    'chunk_index': idx,
                    'text': chunk['text'],
                    'start_pos': chunk.get('start_pos', 0),
                    'end_pos': chunk.get('end_pos', 0)
                }
            })
        
        # Upsert to Qdrant
        logger.info(f"Upserting {len(points)} points to collection '{book_name}'")
        self.vector_store.upsert_points(book_name, points)
        
        # Get collection info
        collection_info = self.vector_store.get_collection_info(book_name)
        
        logger.info(f"Successfully indexed book '{book_name}': {collection_info}")
        
        return {
            'book_name': book_name,
            'total_chapters': book_data['total_chapters'],
            'total_chunks': len(chunks),
            'collection_info': collection_info
        }
    
    def index_all_new_books(self) -> List[Dict[str, Any]]:
        """
        Scan and index all new books in data directory
        
        Returns:
            List of indexing results for each book
        """
        new_books = self.scan_new_books()
        
        if not new_books:
            logger.info("No new books to index")
            return []
        
        results = []
        for book_name in new_books:
            try:
                result = self.index_book(book_name)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to index book '{book_name}': {str(e)}")
                results.append({
                    'book_name': book_name,
                    'error': str(e)
                })
        
        logger.info(f"Indexed {len([r for r in results if 'error' not in r])}/{len(new_books)} books")
        return results
    
    def reindex_book(self, book_name: str) -> Dict[str, Any]:
        """
        Re-index an existing book (delete and re-create collection)
        
        Args:
            book_name: Name of the book to re-index
            
        Returns:
            Indexing statistics
        """
        logger.info(f"Re-indexing book: {book_name}")
        
        # Delete existing collection if it exists
        if self.vector_store.collection_exists(book_name):
            logger.info(f"Deleting existing collection: {book_name}")
            self.vector_store.delete_collection(book_name)
        
        # Index the book
        return self.index_book(book_name)
    
    def _create_chunks(
        self,
        text: str,
        chapter_id: int,
        chapter_title: str,
        book_name: str
    ) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text content to chunk
            chapter_id: Chapter identifier
            chapter_title: Chapter title
            book_name: Book name
            
        Returns:
            List of chunk dictionaries
        """
        # Simple word-based chunking
        words = text.split()
        chunks = []
        
        if len(words) <= self.chunk_size:
            # Single chunk if text is small
            chunks.append({
                'text': text,
                'chapter_id': chapter_id,
                'chapter_title': chapter_title,
                'book_name': book_name,
                'start_pos': 0,
                'end_pos': len(words)
            })
        else:
            # Split into overlapping chunks
            start = 0
            chunk_idx = 0
            
            while start < len(words):
                end = min(start + self.chunk_size, len(words))
                chunk_words = words[start:end]
                chunk_text = ' '.join(chunk_words)
                
                chunks.append({
                    'text': chunk_text,
                    'chapter_id': chapter_id,
                    'chapter_title': chapter_title,
                    'book_name': book_name,
                    'start_pos': start,
                    'end_pos': end
                })
                
                # Move to next chunk with overlap
                if end >= len(words):
                    break
                start += self.chunk_size - self.chunk_overlap
                chunk_idx += 1
        
        return chunks
    
    @staticmethod
    def _generate_point_id(book_name: str, chapter_id: int, chunk_idx: int) -> str:
        """
        Generate a unique point ID for Qdrant
        
        Args:
            book_name: Name of the book
            chapter_id: Chapter identifier
            chunk_idx: Chunk index
            
        Returns:
            Unique point ID (hash)
        """
        # Create a unique identifier string
        id_string = f"{book_name}_{chapter_id}_{chunk_idx}"
        
        # Generate MD5 hash and convert to integer
        hash_obj = hashlib.md5(id_string.encode())
        # Take first 16 characters of hex and convert to int
        point_id = int(hash_obj.hexdigest()[:16], 16)
        
        return point_id
