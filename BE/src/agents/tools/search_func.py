from typing import Dict, List, Optional, Any
import base64
from ...embedding_services.embedding_client import EmbeddingClient
from ...embedding_services.vector_store import VectorStoreClient
from ...utils.s3_client import S3Client
from ...utils.logger import setup_logger

logger = setup_logger("search_tool", "search_tool.log")


def search_func(
    query: str, user_id: str, limit: int = 5, score_threshold: Optional[float] = None
) -> Dict[str, str]:
    """
    Search for documents and retrieve associated images.

    Args:
        query: The search query string.
        user_id: The user ID (used as collection name and S3 prefix).
        limit: Maximum number of results to return.
        score_threshold: Minimum similarity score threshold.

    Returns:
        A dictionary containing:
        - 'text': A formatted string of search results.
        - 'bookname_image_{id}': Base64 encoded image strings.
    """
    try:
        # Initialize clients
        embedding_client = EmbeddingClient()
        vector_store = VectorStoreClient()
        s3_client = S3Client()

        # Check if collection exists
        if not vector_store.collection_exists(user_id):
            logger.warning(f"Collection '{user_id}' not found.")
            return {"text": f"No collection found for user {user_id}."}

        # Generate query embedding
        query_vector = embedding_client.embed_text(query)

        # Perform vector search
        search_results = vector_store.search(
            collection_name=user_id,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
        )

        if not search_results:
            return {"text": "No results found."}

        # Process results
        text_output = ""
        images_map = {}

        for i, result in enumerate(search_results):
            score = result["score"]
            payload = result["payload"]

            book_name = payload.get("book_name", "Unknown Book")
            text_content = payload.get("text", "")
            images = payload.get("images", [])

            # Format text output
            text_output += f"top{i+1} :\n"
            text_output += f"similarity score: {score:.4f}\n"
            text_output += f"{book_name}\n"
            text_output += f"{text_content}\n\n"

            for img_filename in images:
                key_name = img_filename.rsplit(".", 1)[0]  # Remove extension

                if key_name in images_map:
                    continue

                try:
                    s3_key = f"{user_id}/{img_filename}"

                    image_obj = s3_client.download_fileobj(s3_key)
                    image_bytes = image_obj.getvalue()
                    base64_str = base64.b64encode(image_bytes).decode("utf-8")
                    data_uri = f"data:image/png;base64,{base64_str}"

                    images_map[key_name] = data_uri

                except Exception as e:
                    logger.error(f"Failed to fetch image {s3_key}: {str(e)}")
                    continue

        response = {"text": text_output}
        response.update(images_map)

        return response

    except Exception as e:
        logger.error(f"Error in search_tool: {str(e)}")
        return {"text": f"Error executing search: {str(e)}"}
