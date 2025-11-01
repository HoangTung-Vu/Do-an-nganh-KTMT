from sentence_transformers import SentenceTransformer

def load_model(model_name: str, **config) -> SentenceTransformer:
    """
    Load a pre-trained SentenceTransformer model.

    Args:
        model_name (str): The name of the pre-trained model to load.

    Returns:
        SentenceTransformer: The loaded SentenceTransformer model.
    """
    model = SentenceTransformer(model_name, **config)
    return model