import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(app):
    """Setup custom logging configuration writing to separate files under logs/ directory."""
    log_dir = app.config.get("LOG_FOLDER", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Base formatter including request ID
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s (Request ID: %(request_id)s): %(message)s'
    )
    
    # Custom filter to dynamically fetch request_id from context
    class RequestIdFilter(logging.Filter):
        def filter(self, record):
            try:
                from flask import g
                record.request_id = getattr(g, "request_id", "system")
            except Exception:
                record.request_id = "system"
            return True
            
    request_filter = RequestIdFilter()
    
    # Determine base logger level
    log_level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    app.logger.setLevel(log_level)
    
    # Remove existing default flask handlers to avoid duplicated messages
    for handler in list(app.logger.handlers):
        app.logger.removeHandler(handler)
        
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.addFilter(request_filter)
    app.logger.addHandler(console_handler)
    
    # 1. Main Application Handler
    app_handler = RotatingFileHandler(
        os.path.join(log_dir, "application.log"), maxBytes=10*1024*1024, backupCount=5
    )
    app_handler.setFormatter(log_format)
    app_handler.addFilter(request_filter)
    app.logger.addHandler(app_handler)
    
    # 2. Error Handler
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "error.log"), maxBytes=10*1024*1024, backupCount=5
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(log_format)
    error_handler.addFilter(request_filter)
    app.logger.addHandler(error_handler)
    
    # 3. Dedicated API Request Logger
    api_logger = logging.getLogger("api")
    api_logger.setLevel(log_level)
    # Clear existing handlers
    for h in list(api_logger.handlers):
        api_logger.removeHandler(h)
    api_handler = RotatingFileHandler(
        os.path.join(log_dir, "api.log"), maxBytes=10*1024*1024, backupCount=5
    )
    api_handler.setFormatter(log_format)
    api_handler.addFilter(request_filter)
    api_logger.addHandler(api_handler)
    
    # 4. Dedicated AI Agent Logger
    agent_logger = logging.getLogger("agent")
    agent_logger.setLevel(log_level)
    for h in list(agent_logger.handlers):
        agent_logger.removeHandler(h)
    agent_handler = RotatingFileHandler(
        os.path.join(log_dir, "agent.log"), maxBytes=10*1024*1024, backupCount=5
    )
    agent_handler.setFormatter(log_format)
    agent_handler.addFilter(request_filter)
    agent_logger.addHandler(agent_handler)
    
    # 5. Dedicated Database Operations Logger
    db_logger = logging.getLogger("database")
    db_logger.setLevel(log_level)
    for h in list(db_logger.handlers):
        db_logger.removeHandler(h)
    db_handler = RotatingFileHandler(
        os.path.join(log_dir, "database.log"), maxBytes=10*1024*1024, backupCount=5
    )
    db_handler.setFormatter(log_format)
    db_handler.addFilter(request_filter)
    db_logger.addHandler(db_handler)
    
    app.logger.info("Logging infrastructure setup complete.")
