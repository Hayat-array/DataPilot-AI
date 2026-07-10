import os

def validate_environment(app):
    """Validates the environment variables on startup.
    Raises ValueError and halts the application if requirements are unmet.
    """
    required_vars = [
        ("SECRET_KEY", "Used for session security and data sign-offs."),
        ("MONGO_URI", "Required for database metadata and state management.")
    ]
    
    missing = []
    for var, desc in required_vars:
        if not os.environ.get(var):
            missing.append(f"{var} ({desc})")
            
    # Check if at least one LLM provider is available
    llm_keys = ["OPENAI_API_KEY", "GROQ_API_KEY", "GOOGLE_API_KEY"]
    has_llm = any(os.environ.get(key) for key in llm_keys)
    if not has_llm:
        missing.append("At least one LLM API key must be defined: OPENAI_API_KEY, GROQ_API_KEY, or GOOGLE_API_KEY")
        
    if missing:
        error_msg = "CRITICAL CONFIGURATION ERROR:\n" + "\n".join(f"- Missing: {m}" for m in missing)
        app.logger.critical(error_msg)
        raise ValueError(error_msg)
    
    app.logger.info("Environment validation successful. All mandatory keys are present.")
