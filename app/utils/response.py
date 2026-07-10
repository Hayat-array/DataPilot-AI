from flask import jsonify

def success_response(data=None, message="Operation successful.", status_code=200):
    """Generates standard success response."""
    response = {
        "success": True,
        "message": message,
        "data": data or {}
    }
    return jsonify(response), status_code

def error_response(code, message, status_code=400):
    """Generates standard error response manually."""
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    return jsonify(response), status_code
