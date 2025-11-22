import base64
from typing import Any, Dict, List
from google.genai import types

from .base_image_tool import BaseImageTool
from google.adk.tools.tool_context import ToolContext
from ...embedding_services.embedding_client import EmbeddingClient
from ...utils.s3_client import S3Client
from ...utils.logger import setup_logger

logger = setup_logger(__name__, 'search_tool.log')

class SearchTool(BaseImageTool):
    """Tool for semantic search over indexed documents with image retrieval."""
    
    def __init__(self, name: str, description: str, search_instance):
        """
        Initialize SearchTool.
        
        Args:
            name: Tool name
            description: Tool description
            search_instance: VectorStoreClient instance
        """
        super().__init__(name=name, description=description, search_instance=search_instance)
        self.embedding_client = EmbeddingClient()
        self.s3_client = S3Client()
        
    def _get_search_params_schema(self) -> Dict[str, types.Schema]:
        """Define the parameters schema for the search operation."""
        return {
            "query": types.Schema(
                type=types.Type.STRING,
                description="The search query text."
            ),
            "user_id": types.Schema(
                type=types.Type.STRING,
                description="The ID of the user performing the search."
            ),
            "topk": types.Schema(
                type=types.Type.INTEGER,
                description="Number of top results to return.",
                default=5
            )
        }
    
    def _get_required_params(self) -> list[str]:
        """Define required parameters for the search operation."""
        return ["query", "user_id"]
    
    async def _execute_search(self, args: dict[str, Any], tool_context: ToolContext) -> Dict[str, str]:
        """
        Execute the search and return dict of {artifact_name: base64_image} and text content.
        
        Returns:
            Dictionary where:
            - 'text': Formatted string of top results
            - other keys: 'image_id' mapped to base64 image string
        """
        query = args["query"]
        user_id = args["user_id"]
        topk = args.get("topk", 5)
        
        logger.info(f"Executing search for user {user_id}: '{query}' (topk={topk})")
        
        # 1. Generate embedding for query
        try:
            query_vector = self.embedding_client.embed_text(query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return {"text": f"Error processing query: {str(e)}"}
            
        # 2. Search vector store
        # Note: collection_name is now user_id
        try:
            if not self.search_instance.collection_exists(user_id):
                return {"text": f"No index found for user {user_id}. Please index some documents first."}
                
            results = self.search_instance.search(
                collection_name=user_id,
                query_vector=query_vector,
                limit=topk
            )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"text": f"Search failed: {str(e)}"}
            
        if not results:
            return {"text": "No matching results found."}
            
        # 3. Process results
        formatted_text_parts = []
        output_dict = {}
        
        for idx, result in enumerate(results):
            payload = result.get('payload', {})
            score = result.get('score', 0.0)
            
            text_content = payload.get('text', 'No text content')
            book_name = payload.get('book_name', 'Unknown Book')
            chapter_title = payload.get('chapter_title', 'Unknown Chapter')
            images = payload.get('images', [])
            
            # Format text entry
            entry = f"Top {idx + 1} (Score: {score:.4f}):\n"
            entry += f"Source: {book_name} - {chapter_title}\n"
            entry += f"Content: {text_content}\n"
            
            if images:
                entry += f"Images: {', '.join(images)}\n"
                
                # Download and process images
                for img_name in images:
                    # Construct S3 key: user_id/image_name (flattened structure)
                    # img_name is already bookname_image_{id}.png
                    s3_key = f"{user_id}/{img_name}"
                    
                    try:
                        # Download image to memory
                        img_obj = self.s3_client.download_fileobj(s3_key)
                        img_bytes = img_obj.getvalue()
                        
                        # Convert to base64
                        base64_str = base64.b64encode(img_bytes).decode('utf-8')
                        
                        # Add to output dict
                        output_dict[img_name] = base64_str
                        
                    except Exception as e:
                        logger.warning(f"Failed to retrieve image {s3_key}: {e}")
                        entry += f"[Failed to retrieve image {img_name}]\n"
            
            formatted_text_parts.append(entry)
            
        # Combine text
        output_dict["text"] = "\n".join(formatted_text_parts)
        
        return output_dict
