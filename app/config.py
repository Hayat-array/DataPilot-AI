import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent

class BaseConfig:
    """Base Configuration"""
    SECRET_KEY = os.environ.get("SECRET_KEY", "default-secret-key-change-me")
    
    # Databases
    MONGO_URI = os.environ.get("MONGO_URI")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "datapilot_db")
    
    # API Keys
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    
    # RAG / Vector Store settings
    UPSTASH_URL = os.environ.get("UPSTASH_URL")
    UPSTASH_TOKEN = os.environ.get("UPSTASH_TOKEN")
    
    # Folders
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    OUTPUT_FOLDER = os.environ.get("OUTPUT_FOLDER", str(BASE_DIR / "outputs"))
    REPORT_FOLDER = os.environ.get("REPORT_FOLDER", str(BASE_DIR / "reports"))
    GENERATED_CODE_FOLDER = os.environ.get("GENERATED_CODE_FOLDER", str(BASE_DIR / "generated_code"))
    LOG_FOLDER = os.environ.get("LOG_FOLDER", str(BASE_DIR / "logs"))
    
    # Versioning
    VERSION = "1.0.0"
    BUILD_DATE = "2026-07-09"
    
    # Flask settings
    TESTING = False
    DEBUG = False

class DevelopmentConfig(BaseConfig):
    """Development Configuration"""
    DEBUG = True

class TestingConfig(BaseConfig):
    """Testing Configuration"""
    TESTING = True
    DEBUG = True
    MONGO_DB_NAME = "datapilot_test_db"
    UPLOAD_FOLDER = str(BaseConfig.UPLOAD_FOLDER + "_test")

class ProductionConfig(BaseConfig):
    """Production Configuration"""
    DEBUG = False
    TESTING = False

class DockerConfig(ProductionConfig):
    """Docker Container Configuration"""
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/datapilot_db")

class CloudConfig(ProductionConfig):
    """Cloud/Deployment Configuration"""
    # Placeholder for cloud configurations

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "docker": DockerConfig,
    "cloud": CloudConfig,
    "default": DevelopmentConfig
}
