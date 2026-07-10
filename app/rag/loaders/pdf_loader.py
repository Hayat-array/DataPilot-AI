import logging
from langchain_community.document_loaders import PyPDFLoader

def load_pdf(file_path):
    """Loads a PDF document into LangChain Documents."""
    logger = logging.getLogger("agent")
    logger.info(f"RAG: Loading PDF file: {file_path}")
    try:
        loader = PyPDFLoader(file_path)
        return loader.load()
    except Exception as e:
        logger.error(f"RAG: PyPDFLoader failed: {str(e)}")
        # Simple plain text fallback if pdf parsing package is not installed
        return []
