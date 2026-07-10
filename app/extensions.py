from pymongo import MongoClient

# MongoDB Client placeholders
mongo_client = None
db = None

# Cache and Scheduler placeholders for future development
cache = None
scheduler = None

def init_extensions(app):
    """Initialize shared extensions like MongoDB, Redis, etc."""
    global mongo_client, db
    
    mongo_uri = app.config.get("MONGO_URI")
    if mongo_uri:
        try:
            mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            db_name = app.config.get("MONGO_DB_NAME", "datapilot_db")
            db = mongo_client[db_name]
            app.logger.info("MongoDB client created and linked successfully.")
        except Exception as e:
            app.logger.error(f"Failed to create MongoDB client: {str(e)}")
    else:
        app.logger.warning("MONGO_URI not configured. Database extension is disabled.")
