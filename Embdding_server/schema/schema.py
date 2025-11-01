from pydantic import BaseModel, Field

class EmbeddingRequest(BaseModel):
    texts : list[str] = Field(..., description="List of texts to be embedded")
    batch_size = Field(8, description="Number of texts to process in a single batch")
    normalize : bool = Field(True, description="Whether to normalize the embeddings")

class EmbeddingResponse(BaseModel):
    embeddings: list[list[float]] = Field(..., description="List of embeddings corresponding to the input texts")
    embeddings_with_metadata : list[tuple[str, list[float]]] = Field(..., description="List of tuples containing text and its corresponding embedding")

class RerankRequest(BaseModel):
    query: str = Field(..., description="The query text for ranking")
    documents: list[str] = Field(..., description="List of documents to be ranked")
    top_k: int = Field(5, description="Number of top documents to return based on relevance")


class RerankResponse(BaseModel):
    ranked_documents: list[str] = Field(..., description="List of documents ranked by relevance to the query")
    scores : list[float] = Field(..., description="Relevance scores corresponding to the ranked documents")
    all_info : list[tuple[str, float]] = Field(..., description="List of all documents with their relevance scores")
