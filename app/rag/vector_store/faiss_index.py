import os
import logging
from langchain_community.vectorstores import FAISS
from app.rag.embeddings.embedding_model import get_embeddings_model

def build_faiss_index(documents, index_path="vector_store/faiss_index"):
    """Builds a FAISS index from documents and saves it to disk."""
    logger = logging.getLogger("agent")
    logger.info(f"RAG: Building FAISS index from {len(documents)} document chunks...")
    try:
        embeddings = get_embeddings_model()
        db = FAISS.from_documents(documents, embeddings)
        # Ensure path directory exists
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        db.save_local(index_path)
        logger.info(f"RAG: Saved FAISS index to {index_path}")
        return db
    except Exception as e:
        logger.error(f"RAG: Failed to build/save FAISS index: {str(e)}")
        return None

def load_faiss_index(index_path="vector_store/faiss_index"):
    """Loads a FAISS index from disk."""
    logger = logging.getLogger("agent")
    logger.info(f"RAG: Loading FAISS index from {index_path}...")
    try:
        embeddings = get_embeddings_model()
        if os.path.exists(os.path.join(index_path, "index.faiss")):
            db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
            logger.info("RAG: FAISS index loaded successfully.")
            return db
        else:
            logger.warning(f"RAG: FAISS files not found at {index_path}")
            return None
    except Exception as e:
        logger.error(f"RAG: Failed to load FAISS index: {str(e)}")
        return None
