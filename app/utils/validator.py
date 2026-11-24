def validate_environment(app):
    """Log the base dashboard configuration status without requiring unused services."""
    app.logger.info("Base dashboard requires no external services for local profiling and charts.")
