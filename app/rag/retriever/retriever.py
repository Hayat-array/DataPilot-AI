import logging
from app.rag.vector_store.vector_manager import VectorManager

def get_retrieved_context(query, index_path="vector_store/faiss_index"):
    """Performs similarity search and compiles page content string context."""
    logger = logging.getLogger("agent")
    logger.info(f"RAG: Retrieving context for query: '{query}'")
    
    manager = VectorManager(index_path)
    docs = manager.similarity_search(query, k=3)
    
    if not docs:
        logger.info("RAG: No relevant context found in vector store.")
        return "No relevant documentation matches found."
        
    context = ""
    for i, doc in enumerate(docs):
        src = doc.metadata.get("source", "unknown")
        context += f"--- Document Chunk {i+1} (Source: {src}) ---\n{doc.page_content}\n\n"
        
    logger.info(f"RAG: Successfully retrieved {len(docs)} documents.")
    return context
