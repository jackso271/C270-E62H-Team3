import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import MySQLDatabaseError, get_mysql_connection


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
SOURCE_FILES = [
    ("success_logins.json", True),
    ("successful_logins.json", True),
    ("failed_logins.json", False),
]


def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            records = json.load(file)
    except json.JSONDecodeError as error:
        return None, f"{path.name} is not valid JSON: {error.msg}"

    if not isinstance(records, list):
        return None, f"{path.name} must contain a JSON list"

    return records, None


def parse_datetime(value):
    try:
        return datetime.strptime(str(value), DATE_FORMAT).strftime(DATE_FORMAT)
    except (TypeError, ValueError):
        return None


def normalize_success(record):
    login_identifier = (
        record.get("username")
        or record.get("login_input")
        or record.get("login_id")
        or record.get("email")
        or record.get("student_id")
    )
    attempted_at = parse_datetime(record.get("time"))

    if not login_identifier or attempted_at is None:
        return None

    return {
        "login_identifier": str(login_identifier).strip(),
        "was_successful": True,
        "failure_reason": None,
        "attempted_at": attempted_at,
    }


def normalize_failure(record):
    login_identifier = record.get("username") or record.get("login_id")
    reason = record.get("reason")
    attempted_at = parse_datetime(record.get("time"))

    if not login_identifier or not reason or attempted_at is None:
        return None

    return {
        "login_identifier": str(login_identifier).strip(),
        "was_successful": False,
        "failure_reason": str(reason).strip(),
        "attempted_at": attempted_at,
    }


def user_id_for_identifier(cursor, login_identifier):
    clean = str(login_identifier or "").strip()
    lower = clean.lower()
    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE LOWER(username) = %s
           OR LOWER(email) = %s
           OR student_id = %s
        LIMIT 1
        """,
        (lower, lower, clean),
    )
    row = cursor.fetchone()
    return row.get("id") if row else None


def insert_attempt(cursor, attempt):
    user_id = user_id_for_identifier(cursor, attempt["login_identifier"])
    cursor.execute(
        """
        SELECT id
        FROM login_attempts
        WHERE login_identifier = %s
          AND was_successful = %s
          AND failure_reason <=> %s
          AND attempted_at = %s
        LIMIT 1
        """,
        (
            attempt["login_identifier"],
            attempt["was_successful"],
            attempt["failure_reason"],
            attempt["attempted_at"],
        ),
    )
    if cursor.fetchone() is not None:
        return False

    cursor.execute(
        """
        INSERT INTO login_attempts (
            user_id, login_identifier, was_successful, failure_reason, attempted_at
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            user_id,
            attempt["login_identifier"],
            attempt["was_successful"],
            attempt["failure_reason"],
            attempt["attempted_at"],
        ),
    )
    return True


def collect_attempts():
    summary = {"source": 0, "inserted": 0, "skipped": 0, "invalid": 0}
    attempts = []
    invalid_sources = []

    for filename, was_successful in SOURCE_FILES:
        path = PROJECT_ROOT / "backend" / "data" / filename
        records, error = load_json_file(path)
        if error:
            invalid_sources.append(error)
            summary["invalid"] += 1
            continue

        summary["source"] += len(records)
        for record in records:
            if not isinstance(record, dict):
                summary["invalid"] += 1
                continue

            attempt = (
                normalize_success(record)
                if was_successful
                else normalize_failure(record)
            )
            if attempt is None:
                summary["invalid"] += 1
            else:
                attempts.append(attempt)

    return attempts, summary, invalid_sources


def migrate(dry_run=False):
    attempts, summary, invalid_sources = collect_attempts()

    if dry_run:
        summary["skipped"] = len(attempts)
        return summary, invalid_sources

    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()

        for attempt in attempts:
            if insert_attempt(cursor, attempt):
                summary["inserted"] += 1
            else:
                summary["skipped"] += 1

        connection.commit()
        return summary, invalid_sources
    except Exception as error:
        if connection is not None:
            connection.rollback()
        if isinstance(error, MySQLDatabaseError):
            raise
        raise MySQLDatabaseError("Login attempt migration failed.") from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def print_summary(summary, invalid_sources, dry_run=False):
    mode = "DRY RUN" if dry_run else "MIGRATION"
    print(f"{mode} login attempt migration summary")
    print(f"source record count: {summary['source']}")
    print(f"inserted count: {summary['inserted']}")
    print(f"skipped count: {summary['skipped']}")
    print(f"invalid count: {summary['invalid']}")
    for message in invalid_sources:
        print(f"invalid source: {message}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate login JSON files to MySQL login_attempts."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        summary, invalid_sources = migrate(dry_run=args.dry_run)
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print_summary(summary, invalid_sources, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
