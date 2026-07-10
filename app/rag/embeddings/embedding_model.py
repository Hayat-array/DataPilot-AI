import os
import logging
from langchain_community.embeddings import HuggingFaceEmbeddings

class MockEmbeddings:
    """Mock Embeddings to prevent runtime crashes if local weights aren't cached or network is down."""
    def embed_documents(self, texts):
        # Return dummy 384 dimensional vectors (common size for MiniLM)
        return [[0.1] * 384 for _ in texts]
        
    def embed_query(self, text):
        return [0.1] * 384

def get_embeddings_model():
    """Returns local HuggingFace embeddings or a MockEmbeddings fallback."""
    logger = logging.getLogger("agent")
    
    # Check if we should use Mock for testing/speed
    if os.environ.get("USE_MOCK_EMBEDDINGS") == "true":
        logger.info("RAG: Using Mock Embeddings as configured.")
        return MockEmbeddings()
        
    try:
        logger.info("RAG: Initializing local HuggingFace embeddings (all-MiniLM-L6-v2)...")
        # Initialize HuggingFace embeddings
        model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return model
    except Exception as e:
        logger.warning(f"RAG: HuggingFaceEmbeddings initialization failed: {str(e)}. Falling back to MockEmbeddings.")
        return MockEmbeddings()
