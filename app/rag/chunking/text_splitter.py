import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter

def split_document(documents, chunk_size=1000, chunk_overlap=200):
    """Splits LangChain documents into chunks."""
    logger = logging.getLogger("agent")
    logger.info(f"RAG: Splitting {len(documents)} document(s) into chunks (Size: {chunk_size}, Overlap: {chunk_overlap})")
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    try:
        chunks = splitter.split_documents(documents)
        logger.info(f"RAG: Generated {len(chunks)} chunk(s).")
        return chunks
    except Exception as e:
        logger.error(f"RAG: Splitting failed: {str(e)}")
        return []
