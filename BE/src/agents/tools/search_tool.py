from typing import Dict, Any, List, Optional
from google.genai import types
from google.adk.tools.tool_context import ToolContext
from .base_image_tool import BaseArtifactTool
from .search_func import search_func
from ...utils.logger import setup_logger

logger = setup_logger('search_tool_class', 'search_tool.log')

class SearchTool(BaseArtifactTool):
    """Tool for searching documents and retrieving associated images."""
    
    def __init__(self, search_instance=None):
        super().__init__(
            name="search_tool",
            description="Search for documents and retrieve associated images based on a query.",
            search_instance=search_instance
        )
    
    def _get_search_params_schema(self) -> Dict[str, types.Schema]:
        """Define the parameters schema for the search operation."""
        return {
            "query": types.Schema(
                type=types.Type.STRING,
                description="The search query string."
            ),
            "limit": types.Schema(
                type=types.Type.INTEGER,
                description="Maximum number of results to return (default: 5)."
            ),
            "score_threshold": types.Schema(
                type=types.Type.NUMBER,
                description="Minimum similarity score threshold (optional)."
            )
        }
    
    def _get_required_params(self) -> list[str]:
        """Define required parameters for the search operation."""
        return ["query"]
    
    async def _execute_search(self, args: dict[str, Any], tool_context: ToolContext) -> Dict[str, str]:
        """Execute the search and return dict of {artifact_name: data_string}."""
        query = args.get("query")
        limit = args.get("limit", 5)
        score_threshold = args.get("score_threshold")
        
        # Get user_id from tool_context
        try:
            user_id = tool_context._invocation_context.user_id
        except AttributeError:
            logger.warning("Could not retrieve user_id from tool_context. Using default 'unknown'.")
            user_id = "unknown"
            
        logger.info(f"Executing search for user {user_id} with query: {query}")
        
        # Call the search function
        # search_func is synchronous, but _execute_search is async.
        # Since search_func does I/O (network), it might block the event loop.
        # However, for this implementation, we'll call it directly. 
        # If needed, we could wrap it in run_in_executor.
        
        results = search_func(
            query=query,
            user_id=user_id,
            limit=limit,
            score_threshold=score_threshold
        )
        
        return results
