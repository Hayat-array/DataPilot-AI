import os
import sys
import pytest

# Ensure the backend directory is in python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Set environment before loading application factory
os.environ["FLASK_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-12345"
os.environ["MONGO_URI"] = "mongodb://localhost:27017/datapilot_test_db"
os.environ["VALIDATE_ENV_ON_START"] = "false"

from app import create_app

@pytest.fixture
def app():
    """App fixture for testing."""
    app = create_app("testing")
    return app

@pytest.fixture
def client(app):
    """Client fixture for testing API requests."""
    return app.test_client()
