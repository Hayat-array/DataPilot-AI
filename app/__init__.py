import os

from flask import Flask, request

from app.config import config_by_name
from app.extensions import init_extensions
from app.logger import setup_logging
from app.middleware.error_handler import setup_error_handlers
from app.middleware.request_id import setup_request_id_middleware
from app.routes.api import api_bp
from app.routes.frontend import frontend_bp
from app.routes.health import health_bp
from app.routes.swagger import swagger_bp


def create_app(config_name=None):
    """Flask Application Factory."""
    if not config_name:
        config_name = os.environ.get("FLASK_ENV", "development")
        
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))
    
    # Initialize logger
    setup_logging(app)
    
    # Environment Validation
    validate_env = os.environ.get("VALIDATE_ENV_ON_START", "true").lower() == "true"
    if validate_env and config_name != "testing":
        from app.utils.validator import validate_environment
        validate_environment(app)
        
    # Initialize extensions
    init_extensions(app)
    
    # Setup middleware
    setup_request_id_middleware(app)
    setup_error_handlers(app)
    
    # Register blueprints
    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(swagger_bp, url_prefix="/api")
    app.register_blueprint(frontend_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if not app.config.get("DEBUG") and request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000")
        return response

    app.logger.info(f"Flask Application initialized with config: {config_name}")
    return app
