import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import MySQLDatabaseError, get_mysql_connection


LEGACY_DATA_DIR = PROJECT_ROOT / "database" / "legacy_seed_data"
SOURCE_FILE = LEGACY_DATA_DIR / "users.json"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def load_source_records():
    with open(SOURCE_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("users.json must contain a JSON list.")

    return records


def parse_datetime(value):
    if not value or str(value).strip() == "N/A":
        return None

    try:
        return datetime.strptime(str(value), DATE_FORMAT).strftime(DATE_FORMAT)
    except ValueError:
        return None


def valid_positive_int(value):
    if isinstance(value, bool):
        return None

    try:
        number = int(value)
    except (TypeError, ValueError):
        return None

    return number if number > 0 else None


def password_hash(value):
    password = str(value or "").strip()
    if not password:
        return None
    if password.startswith(("pbkdf2:", "scrypt:", "argon2:")):
        return password
    return generate_password_hash(password)


def normalize_record(record):
    if not isinstance(record, dict):
        return None

    name = str(record.get("name") or record.get("username") or "").strip()
    username = str(record.get("username") or "").strip()
    email = str(record.get("email") or "").strip().lower()
    student_id = str(record.get("student_id") or "").strip() or None
    hashed_password = password_hash(record.get("password") or record.get("password_hash"))

    if not name or not username or not email or hashed_password is None:
        return None

    return {
        "id": valid_positive_int(record.get("id")),
        "name": name,
        "username": username,
        "email": email,
        "student_id": student_id,
        "school": str(record.get("school") or "N/A").strip() or "N/A",
        "password_hash": hashed_password,
        "role": str(record.get("role") or "student").strip() or "student",
        "is_blocked": bool(record.get("blocked", False)),
        "created_at": parse_datetime(record.get("created_at")),
        "last_login_at": parse_datetime(record.get("last_login")),
        "status_updated_at": parse_datetime(record.get("status_updated_at")),
    }


def insert_user(cursor, user):
    if user["id"] is not None:
        cursor.execute(
            """
            INSERT INTO users (
                id, name, username, email, student_id, school, password_hash,
                role, is_blocked, created_at, last_login_at, status_updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                    COALESCE(%s, CURRENT_TIMESTAMP), %s, %s)
            ON DUPLICATE KEY UPDATE id = id
            """,
            (
                user["id"],
                user["name"],
                user["username"],
                user["email"],
                user["student_id"],
                user["school"],
                user["password_hash"],
                user["role"],
                user["is_blocked"],
                user["created_at"],
                user["last_login_at"],
                user["status_updated_at"],
            ),
        )
        return cursor.rowcount == 1

    cursor.execute(
        """
        INSERT INTO users (
            name, username, email, student_id, school, password_hash,
            role, is_blocked, created_at, last_login_at, status_updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                COALESCE(%s, CURRENT_TIMESTAMP), %s, %s)
        ON DUPLICATE KEY UPDATE id = id
        """,
        (
            user["name"],
            user["username"],
            user["email"],
            user["student_id"],
            user["school"],
            user["password_hash"],
            user["role"],
            user["is_blocked"],
            user["created_at"],
            user["last_login_at"],
            user["status_updated_at"],
        ),
    )
    return cursor.rowcount == 1


def migrate(dry_run=False):
    records = load_source_records()
    summary = {"source": len(records), "inserted": 0, "skipped": 0, "invalid": 0}
    users = []

    for record in records:
        user = normalize_record(record)
        if user is None:
            summary["invalid"] += 1
        else:
            users.append(user)

    if dry_run:
        summary["skipped"] = len(users)
        return summary

    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()

        for user in users:
            if insert_user(cursor, user):
                summary["inserted"] += 1
            else:
                summary["skipped"] += 1

        connection.commit()
        return summary
    except Exception as error:
        if connection is not None:
            connection.rollback()
        if isinstance(error, MySQLDatabaseError):
            raise
        raise MySQLDatabaseError("User migration failed.") from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def print_summary(summary, dry_run=False):
    mode = "DRY RUN" if dry_run else "MIGRATION"
    print(f"{mode} user migration summary")
    print(f"source record count: {summary['source']}")
    print(f"inserted count: {summary['inserted']}")
    print(f"skipped count: {summary['skipped']}")
    print(f"invalid count: {summary['invalid']}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate database/legacy_seed_data/users.json to MySQL."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        summary = migrate(dry_run=args.dry_run)
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print_summary(summary, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
