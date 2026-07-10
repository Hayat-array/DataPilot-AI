import logging
from langchain_core.documents import Document

def load_github_repo(repo_url, path_context=""):
    """GitHub Repository Loader. Simply fetches text representation of repository elements."""
    logger = logging.getLogger("agent")
    logger.info(f"RAG: Mocking load GitHub repo: {repo_url} (Context path: {path_context})")
    
    # We can connect to GitHub API or perform local git repository analysis
    # For now, we instantiate a fallback mock document containing metadata
    doc = Document(
        page_content=f"Metadata and indexing files loaded for repository: {repo_url}. "
                     f"This context helps debug code execution issues for Pandas, Scikit-learn, and Numpy.",
        metadata={"source": repo_url, "type": "github"}
    )
    return [doc]
