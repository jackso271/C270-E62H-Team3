import json
import os
from pathlib import Path

from flask import current_app


DATA_FILES = {
    "users": "users.json",
    "success_logs": "success_logins.json",
    "failed_logs": "failed_logins.json",
    "products": "products.json",
    "requests": "requests.json",
    "notifications": "notifications.json",
    "account_creation_logs": "account_creation_logs.json",
    "successful_logins": "successful_logins.json",
}


def get_data_dir():
    """Return the configured JSON data folder."""
    return Path(current_app.config["DATA_DIR"])


def data_file(name):
    """Build an absolute path for a known JSON data file."""
    return get_data_dir() / DATA_FILES[name]


def ensure_data_files(data_dir):
    """Create the data directory and any missing JSON files."""
    os.makedirs(data_dir, exist_ok=True)

    for filename in DATA_FILES.values():
        path = Path(data_dir) / filename
        if not path.exists():
            path.write_text("[]", encoding="utf-8")


def load_json(file_path):
    """Load a JSON list from disk. Invalid or empty files return an empty list."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return []


def save_json(file_path, data):
    """Save JSON data using readable indentation for teammates."""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
