import platform
from flask import Blueprint
from app import extensions
from app.utils.response import success_response, error_response

health_bp = Blueprint("health", __name__)

@health_bp.route("/live", methods=["GET"])
def live():
    """Simple check to verify the app is running."""
    return success_response(message="Service is live.")

@health_bp.route("/ready", methods=["GET"])
def ready():
    """Checks dependencies like database connectivity."""
    try:
        if extensions.db is not None:
            # Send ping command to Mongo
            extensions.db.command("ping")
            return success_response(message="Service is ready. DB connection OK.")
        else:
            return error_response(
                code="DATABASE_NOT_INITIALIZED",
                message="MongoDB database object is not initialized.",
                status_code=503
            )
    except Exception as e:
        return error_response(
            code="DATABASE_UNREACHABLE",
            message=f"Database check failed: {str(e)}",
            status_code=503
        )

@health_bp.route("/health", methods=["GET"])
def health():
    """Returns detailed health status report."""
    db_ok = False
    db_msg = "Not initialized"
    if extensions.db is not None:
        try:
            extensions.db.command("ping")
            db_ok = True
            db_msg = "Connected"
        except Exception as e:
            db_msg = f"Unreachable: {str(e)}"
            
    status = "UP" if db_ok else "DEGRADED"
    data = {
        "status": status,
        "checks": {
            "database": {
                "status": "UP" if db_ok else "DOWN",
                "message": db_msg
            }
        }
    }
    
    status_code = 200 if db_ok else 503
    return success_response(data=data, message="Health check complete.", status_code=status_code)

@health_bp.route("/version", methods=["GET"])
def version():
    """Returns application metadata version."""
    from flask import current_app
    data = {
        "version": current_app.config.get("VERSION", "1.0.0"),
        "build": current_app.config.get("BUILD_DATE", "2026-07-09"),
        "python": platform.python_version()
    }
    return success_response(data=data, message="Version check successful.")
