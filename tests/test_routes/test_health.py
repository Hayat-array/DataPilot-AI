from unittest.mock import patch

def test_live_endpoint(client):
    """Test standard live endpoint."""
    response = client.get("/api/health/live")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Service is live."

def test_version_endpoint(client):
    """Test version endpoint returns valid metadata."""
    response = client.get("/api/health/version")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert "version" in json_data["data"]
    assert "build" in json_data["data"]
    assert "python" in json_data["data"]

def test_ready_endpoint_db_ok(client):
    """Test ready endpoint when DB is reachable."""
    with patch("app.routes.health.db") as mock_db:
        # Mock successful db.command("ping")
        mock_db.command.return_value = {"ok": 1.0}
        response = client.get("/api/health/ready")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True
        assert "Service is ready. DB connection OK." in json_data["message"]

def test_ready_endpoint_db_down(client):
    """Test ready endpoint when DB is unreachable."""
    with patch("app.routes.health.db") as mock_db:
        # Mock database connection timeout
        mock_db.command.side_effect = Exception("Connection timed out")
        response = client.get("/api/health/ready")
        assert response.status_code == 503
        json_data = response.get_json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "DATABASE_UNREACHABLE"
