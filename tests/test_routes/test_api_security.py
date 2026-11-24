from io import BytesIO

from openpyxl import Workbook


def test_upload_and_load_cached_csv(client, app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    response = client.post(
        "/api/upload",
        data={"file": (BytesIO(b"name,value\nalpha,12\nbeta,8\n"), "metrics.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    filename = response.get_json()["data"]["filename"]
    assert (tmp_path / filename).stat().st_mode & 0o777 == 0o600

    cached = client.post("/api/load-cached", json={"filename": filename})
    assert cached.status_code == 200
    assert cached.get_json()["data"]["columns"] == ["name", "value"]
    assert cached.get_json()["data"]["data"][0]["name"] == "alpha"


def test_upload_and_load_cached_xlsx(client, app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["name", "score"])
    sheet.append(["Ada", 98])
    spreadsheet = BytesIO()
    workbook.save(spreadsheet)
    spreadsheet.seek(0)

    response = client.post(
        "/api/upload",
        data={"file": (spreadsheet, "grades.xlsx")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    filename = response.get_json()["data"]["filename"]
    cached = client.post("/api/load-cached", json={"filename": filename})
    assert cached.get_json()["data"]["data"][0] == {"name": "Ada", "score": 98}


def test_upload_rejects_datasets_over_row_limit(client, app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    content = "value\\n" + "1\\n" * 10_001
    response = client.post(
        "/api/upload",
        data={"file": (BytesIO(content.encode()), "too-many.csv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "FILE_READ_ERROR"
    assert list(tmp_path.iterdir()) == []


def test_load_cached_rejects_path_traversal(client):
    response = client.post("/api/load-cached", json={"filename": "../secret.csv"})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_FILENAME"


def test_chat_does_not_execute_generated_code(client):
    response = client.post("/api/chat", json={"message": "read files", "filename": "dataset.csv"})
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "ANALYSIS_EXECUTION_DISABLED"


def test_upload_rejects_unsupported_extensions(client):
    response = client.post(
        "/api/upload",
        data={"file": (BytesIO(b"payload"), "payload.exe")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_upload_enforces_request_size_limit(client, app):
    app.config["MAX_CONTENT_LENGTH"] = 128
    response = client.post(
        "/api/upload",
        data={"file": (BytesIO(b"x" * 512), "large.csv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 413


def test_security_headers_are_present(client):
    response = client.get("/api/health/live")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
