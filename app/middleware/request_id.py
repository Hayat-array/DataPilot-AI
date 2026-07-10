import time
import uuid
import logging
from flask import request, g

def setup_request_id_middleware(app):
    """Sets up before and after request hooks to assign Request IDs and log executions."""
    api_logger = logging.getLogger("api")
    
    @app.before_request
    def before_request():
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        g.request_id = request_id
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        # Calculate time taken
        execution_time = 0.0
        if hasattr(g, "start_time"):
            execution_time = time.time() - g.start_time
            
        request_id = getattr(g, "request_id", "unknown")
        response.headers["X-Request-ID"] = request_id
        
        # Gather attributes for logging
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        user_agent = request.headers.get("User-Agent", "unknown")
        
        log_message = (
            f"Request ID: {request_id} | "
            f"Method: {request.method} | "
            f"Path: {request.path} | "
            f"Status: {response.status_code} | "
            f"Time: {execution_time:.4f}s | "
            f"IP: {ip} | "
            f"UA: {user_agent}"
        )
        
        # Log to flask application logger and api logger
        app.logger.info(log_message)
        api_logger.info(log_message)
        
        return response
