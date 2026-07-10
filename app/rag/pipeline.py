import logging
from app.rag.loaders.pdf_loader import load_pdf
from app.rag.chunking.text_splitter import split_document
from app.rag.vector_store.vector_manager import VectorManager
from app.rag.retriever.retriever import get_retrieved_context

def ingest_file_to_rag(file_path, index_path="vector_store/faiss_index"):
    """Loads, splits and indexes a file."""
    logger = logging.getLogger("agent")
    logger.info(f"RAG: Starting ingestion pipeline for file: {file_path}")
    
    docs = load_pdf(file_path)
    if not docs:
        logger.warning("RAG: No documents loaded. Ingestion halted.")
        return False
        
    chunks = split_document(docs)
    if not chunks:
        logger.warning("RAG: No chunks generated. Ingestion halted.")
        return False
        
    manager = VectorManager(index_path)
    success = manager.ingest_documents(chunks)
    logger.info(f"RAG: Ingestion status: {success}")
    return success

def query_rag_knowledge(query, index_path="vector_store/faiss_index"):
    """Retrieves relevant context matching a query."""
    return get_retrieved_context(query, index_path)
