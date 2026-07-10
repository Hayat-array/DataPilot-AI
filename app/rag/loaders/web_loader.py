import logging
from langchain_community.document_loaders import WebBaseLoader

def load_web_url(url):
    """Loads a webpage URL into LangChain Documents."""
    logger = logging.getLogger("agent")
    logger.info(f"RAG: Loading Web page: {url}")
    try:
        loader = WebBaseLoader(url)
        return loader.load()
    except Exception as e:
        logger.error(f"RAG: WebBaseLoader failed: {str(e)}")
        return []
