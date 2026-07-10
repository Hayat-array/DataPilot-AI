# Prompts specific to RAG flows
RAG_PROMPT_TEMPLATE = """You are an expert Data Scientist.
Use the following official documentation context to resolve the execution failure or complete the task.

Context:
{context}

Error/Task:
{query}

Corrected Python Code:
"""
