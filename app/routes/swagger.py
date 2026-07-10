from flask import Blueprint, jsonify, render_template_string

swagger_bp = Blueprint("swagger", __name__)

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "DataPilot AI API",
        "description": "Production-grade autonomous AI Data Analysis Platform backend API.",
        "version": "1.0.0"
    },
    "paths": {
        "/api/health/live": {
            "get": {
                "summary": "Liveness Check",
                "responses": {
                    "200": {
                        "description": "Service is live"
                    }
                }
            }
        },
        "/api/health/ready": {
            "get": {
                "summary": "Readiness Check",
                "responses": {
                    "200": {
                        "description": "Service is ready"
                    },
                    "503": {
                        "description": "Database or external service is down"
                    }
                }
            }
        },
        "/api/health/health": {
            "get": {
                "summary": "Health Status",
                "responses": {
                    "200": {
                        "description": "Detailed health parameters"
                    }
                }
            }
        },
        "/api/health/version": {
            "get": {
                "summary": "Version Information",
                "responses": {
                    "200": {
                        "description": "Platform version metadata"
                    }
                }
            }
        }
    }
}

@swagger_bp.route("/docs/openapi.json", methods=["GET"])
def openapi_json():
    """Serves the OpenAPI description JSON."""
    return jsonify(OPENAPI_SPEC)

@swagger_bp.route("/docs", methods=["GET"])
def swagger_ui():
    """Serves the Swagger UI page rendered dynamically."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>DataPilot AI API Docs</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
        <link rel="icon" type="image/png" href="https://unpkg.com/swagger-ui-dist@5/favicon-32x32.png" sizes="32x32" />
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js" charset="UTF-8"></script>
        <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js" charset="UTF-8"></script>
        <script>
            window.onload = () => {
                window.ui = SwaggerUIBundle({
                    url: '/api/docs/openapi.json',
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout",
                    deepLinking: true,
                    showExtensions: true,
                    showCommonExtensions: true
                });
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)
