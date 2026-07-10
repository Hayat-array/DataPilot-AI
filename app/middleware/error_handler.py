from flask import jsonify
from werkzeug.exceptions import HTTPException

def setup_error_handlers(app):
    """Sets up global error handling to ensure all HTTP and Python exceptions return JSON."""
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Determine status code and message
        if isinstance(e, HTTPException):
            code = getattr(e, "code", 500)
            message = getattr(e, "description", str(e))
            error_code = e.name.upper().replace(" ", "_")
        else:
            code = 500
            message = "An unexpected error occurred on the server."
            error_code = "INTERNAL_SERVER_ERROR"
            
            # Log full stack trace for internal server errors
            app.logger.exception(f"Unhandled Exception: {str(e)}")
            
        response = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message
            }
        }
        return jsonify(response), code
