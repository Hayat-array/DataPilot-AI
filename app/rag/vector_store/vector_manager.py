import os
import logging
from app.rag.vector_store.faiss_index import build_faiss_index, load_faiss_index

class VectorManager:
    """Manages ingestion and querying of FAISS vectors."""
    def __init__(self, index_path="vector_store/faiss_index"):
        self.index_path = index_path
        self.db = load_faiss_index(self.index_path)
        self.logger = logging.getLogger("agent")

    def ingest_documents(self, documents):
        """Adds documents to the index, initializing it if not present."""
        if not documents:
            return False
            
        self.logger.info(f"RAG: Ingesting {len(documents)} chunks to vector store.")
        if self.db is None:
            self.db = build_faiss_index(documents, self.index_path)
        else:
            try:
                self.db.add_documents(documents)
                self.db.save_local(self.index_path)
                self.logger.info("RAG: Vector store updated successfully.")
            except Exception as e:
                self.logger.error(f"RAG: Ingestion update failed: {str(e)}")
                return False
        return True

    def similarity_search(self, query, k=3):
        """Returns similarity search matches."""
        if self.db is None:
            self.logger.warning("RAG: Similarity search requested but database is not loaded.")
            return []
        try:
            return self.db.similarity_search(query, k=k)
        except Exception as e:
            self.logger.error(f"RAG: Similarity search failed: {str(e)}")
            return []
