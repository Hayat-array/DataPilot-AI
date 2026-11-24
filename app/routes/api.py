"""Dataset upload and cache APIs for the browser-based analyst."""

import csv
import json
import math
import os
import time
import uuid
import zipfile
from datetime import date, datetime

from flask import Blueprint, current_app, request
from werkzeug.utils import secure_filename

from app.utils.response import error_response, success_response

api_bp = Blueprint("api_routes", __name__)
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}
MAX_DATASET_ROWS = 10_000
MAX_DATASET_COLUMNS = 100
UPLOAD_CACHE_TTL_SECONDS = 60 * 60


def _cleanup_expired_uploads(upload_folder: str):
    """Remove expired temporary files from a reused serverless worker."""
    cutoff = time.time() - UPLOAD_CACHE_TTL_SECONDS
    try:
        with os.scandir(upload_folder) as entries:
            for entry in entries:
                try:
                    if (entry.is_file(follow_symlinks=False) and
                            entry.stat(follow_symlinks=False).st_mtime < cutoff):
                        os.remove(entry.path)
                except OSError:
                    current_app.logger.warning("Unable to remove an expired temporary upload")
    except OSError:
        current_app.logger.warning("Unable to inspect the temporary upload directory")


def _resolve_upload_path(filename: str) -> str | None:
    """Resolve only server-issued filenames within the configured upload directory."""
    if not isinstance(filename, str) or not filename or secure_filename(filename) != filename:
        return None

    upload_root = os.path.realpath(current_app.config["UPLOAD_FOLDER"])
    file_path = os.path.realpath(os.path.join(upload_root, filename))
    try:
        if os.path.commonpath((upload_root, file_path)) != upload_root:
            return None
    except ValueError:
        return None
    return file_path


def _json_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return _json_value(value.item())
    return str(value)


def _normalize_rows(columns, rows):
    columns = [str(column).strip() for column in columns]
    if (not columns or len(columns) > MAX_DATASET_COLUMNS or
            any(not column for column in columns) or len(set(columns)) != len(columns)):
        raise ValueError("Dataset must contain 1 to 100 uniquely named columns.")

    normalized = []
    iterator = iter(rows)
    end = object()
    for row_index in range(MAX_DATASET_ROWS + 1):
        row = next(iterator, end)
        if row is end:
            break
        if row_index == MAX_DATASET_ROWS:
            raise ValueError("Dataset exceeds the 10,000 row limit.")
        if not isinstance(row, dict):
            raise TypeError("Dataset rows must be JSON objects or tabular records.")
        normalized.append({column: _json_value(row.get(column)) for column in columns})
    if not normalized:
        raise ValueError("Dataset contains no records.")
    return columns, normalized


def _read_dataset(file_path: str):
    extension = os.path.splitext(file_path)[1].lower()
    if extension == ".csv":
        csv.field_size_limit(10_000)
        with open(file_path, newline="", encoding="utf-8-sig") as source:
            reader = csv.reader(source)
            columns = next(reader, [])
            def rows():
                for values in reader:
                    if not values:
                        continue
                    if len(values) > len(columns):
                        raise ValueError("CSV row contains more values than the header.")
                    yield {column: values[index] if index < len(values) else None
                           for index, column in enumerate(columns)}
            return _normalize_rows(columns, rows())

    if extension == ".json":
        with open(file_path, encoding="utf-8") as source:
            payload = json.load(source)
        if isinstance(payload, dict):
            records = next((value for value in payload.values() if isinstance(value, list)), None)
            records = records if records is not None else [payload]
        else:
            records = payload
        if not isinstance(records, list) or not records or not isinstance(records[0], dict):
            raise ValueError("JSON must contain an object or a non-empty array of objects.")
        columns = list(dict.fromkeys(key for row in records if isinstance(row, dict) for key in row))
        return _normalize_rows(columns, records)

    if extension == ".xlsx":
        with zipfile.ZipFile(file_path) as archive:
            members = archive.infolist()
            uncompressed_size = sum(member.file_size for member in members)
            if (len(members) > 1_000 or uncompressed_size > 64 * 1024 * 1024 or
                    any(member.file_size / max(member.compress_size, 1) > 100 for member in members)):
                raise ValueError("Spreadsheet archive expands beyond the supported size.")

        from openpyxl import load_workbook

        workbook = load_workbook(file_path, read_only=True, data_only=True)
        try:
            sheet = workbook.active
            iterator = sheet.iter_rows(values_only=True)
            headers = next(iterator, None)
            if not headers:
                raise ValueError("Spreadsheet contains no header row.")
            columns = [str(value) if value is not None else "" for value in headers]
            rows = ({column: values[index] if index < len(values) else None
                     for index, column in enumerate(columns)}
                    for values in iterator)
            return _normalize_rows(columns, rows)
        finally:
            workbook.close()

    if extension == ".xls":
        import xlrd

        workbook = xlrd.open_workbook(file_path, on_demand=True)
        try:
            sheet = workbook.sheet_by_index(0)
            columns = [str(value) for value in sheet.row_values(0)] if sheet.nrows else []
            rows = ({column: sheet.cell_value(row_index, column_index)
                     for column_index, column in enumerate(columns)}
                    for row_index in range(1, min(sheet.nrows, MAX_DATASET_ROWS + 2)))
            return _normalize_rows(columns, rows)
        finally:
            workbook.release_resources()

    raise ValueError("Unsupported dataset format.")


def _valid_extension(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@api_bp.route("/upload", methods=["POST"])
def upload_file():
    """Validate and cache a dataset using a server-generated filename."""
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return error_response("NO_FILE_PART", "No file part in the request", 400)
    if not uploaded_file.filename or not uploaded_file.filename.strip():
        return error_response("NO_SELECTED_FILE", "No selected file", 400)
    if not _valid_extension(uploaded_file.filename):
        return error_response("INVALID_FILE_TYPE", "File extension not allowed.", 400)

    original_name = secure_filename(uploaded_file.filename)
    if not original_name:
        return error_response("INVALID_FILENAME", "Filename is invalid", 400)

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, mode=0o700, exist_ok=True)
    os.chmod(upload_folder, 0o700)
    _cleanup_expired_uploads(upload_folder)
    filename = f"{uuid.uuid4().hex[:12]}_{original_name}"
    file_path = os.path.join(upload_folder, filename)
    uploaded_file.save(file_path)
    os.chmod(file_path, 0o600)

    try:
        columns, rows = _read_dataset(file_path)
    except Exception:  # noqa: BLE001 - parsers expose different format-specific exceptions.
        try:
            os.remove(file_path)
        except OSError:
            current_app.logger.warning("Unable to remove rejected dataset upload")
        return error_response("FILE_READ_ERROR", "The file could not be parsed as a supported dataset.", 400)

    return success_response(
        data={"filename": filename, "original_name": original_name,
              "rows": len(rows), "cols": len(columns)},
        message="File uploaded and verified successfully.",
    )


@api_bp.route("/load-cached", methods=["POST"])
def load_cached():
    """Load a previously uploaded, validated dataset from the private cache."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error_response("INVALID_REQUEST", "A JSON object is required", 400)

    filename = body.get("filename", "")
    file_path = _resolve_upload_path(filename)
    if file_path is None:
        return error_response("INVALID_FILENAME", "Filename is invalid", 400)
    if not os.path.isfile(file_path):
        return error_response("FILE_NOT_FOUND", "Cached file no longer exists", 404)

    try:
        columns, rows = _read_dataset(file_path)
    except Exception:  # noqa: BLE001 - parsers expose different format-specific exceptions.
        return error_response("LOAD_ERROR", "The cached dataset could not be read.", 400)

    return success_response(
        data={"columns": columns, "rows_count": len(rows), "cols_count": len(columns),
              "data": rows, "original_name": filename.split("_", 1)[-1]},
        message="Cached dataset loaded successfully.",
    )


@api_bp.route("/chat", methods=["POST"])
def chat_co_pilot():
    """Return a clear status until a properly isolated analysis service is available."""
    return error_response(
        "ANALYSIS_EXECUTION_DISABLED",
        "AI-generated Python execution is disabled because this deployment does not provide an isolated execution service. Dataset preview, filters, and visualizations remain available.",
        503,
    )
