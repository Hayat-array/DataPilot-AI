import os
import sys

# Ensure application package path is resolvable
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app

config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(config_name)

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    app.run(host=host, port=port)
