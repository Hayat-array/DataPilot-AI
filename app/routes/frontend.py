from flask import Blueprint, render_template

frontend_bp = Blueprint("frontend", __name__)

@frontend_bp.route("/", methods=["GET"])
def index():
    """Renders the modular dashboard HTML page."""
    return render_template("index.html")
