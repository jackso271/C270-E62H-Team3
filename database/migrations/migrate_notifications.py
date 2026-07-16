import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import MySQLDatabaseError, get_mysql_connection


LEGACY_DATA_DIR = PROJECT_ROOT / "database" / "legacy_seed_data"
SOURCE_FILE = LEGACY_DATA_DIR / "notifications.json"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def load_source_records():
    with open(SOURCE_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("notifications.json must contain a JSON list.")

    return records


def parse_created_at(value):
    if not value:
        return datetime.now().strftime(DATE_FORMAT)

    try:
        return datetime.strptime(str(value), DATE_FORMAT).strftime(DATE_FORMAT)
    except ValueError:
        return None


def valid_id(value):
    if isinstance(value, bool):
        return None

    try:
        notification_id = int(value)
    except (TypeError, ValueError):
        return None

    if notification_id <= 0:
        return None

    return notification_id


def normalize_record(record):
    if not isinstance(record, dict):
        return None

    title = str(record.get("title") or "").strip()
    message = str(record.get("message") or "").strip()
    status = str(record.get("status") or "Info").strip() or "Info"
    created_at = parse_created_at(record.get("time"))

    if not title or not message or created_at is None:
        return None

    return {
        "id": valid_id(record.get("id")),
        "title": title,
        "message": message,
        "status": status,
        "created_at": created_at,
    }


def duplicate_without_id(cursor, notification):
    cursor.execute(
        """
        SELECT id
        FROM notifications
        WHERE title = %s
          AND message = %s
          AND status = %s
          AND created_at = %s
        LIMIT 1
        """,
        (
            notification["title"],
            notification["message"],
            notification["status"],
            notification["created_at"],
        ),
    )
    return cursor.fetchone() is not None


def insert_notification(cursor, notification):
    if notification["id"] is not None:
        cursor.execute(
            """
            INSERT INTO notifications (id, title, message, status, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE id = id
            """,
            (
                notification["id"],
                notification["title"],
                notification["message"],
                notification["status"],
                notification["created_at"],
            ),
        )
        return cursor.rowcount == 1

    if duplicate_without_id(cursor, notification):
        return False

    cursor.execute(
        """
        INSERT INTO notifications (title, message, status, created_at)
        VALUES (%s, %s, %s, %s)
        """,
        (
            notification["title"],
            notification["message"],
            notification["status"],
            notification["created_at"],
        ),
    )
    return True


def migrate(dry_run=False):
    records = load_source_records()
    summary = {
        "source": len(records),
        "inserted": 0,
        "skipped": 0,
        "invalid": 0,
    }

    normalized_records = []
    for record in records:
        notification = normalize_record(record)
        if notification is None:
            summary["invalid"] += 1
        else:
            normalized_records.append(notification)

    if dry_run:
        summary["skipped"] = len(normalized_records)
        return summary

    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()

        for notification in normalized_records:
            if insert_notification(cursor, notification):
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
        raise MySQLDatabaseError("Notification migration failed.") from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def print_summary(summary, dry_run=False):
    mode = "DRY RUN" if dry_run else "MIGRATION"
    print(f"{mode} notification migration summary")
    print(f"source record count: {summary['source']}")
    print(f"inserted count: {summary['inserted']}")
    print(f"skipped count: {summary['skipped']}")
    print(f"invalid count: {summary['invalid']}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate database/legacy_seed_data/notifications.json to MySQL."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize JSON records without connecting to MySQL.",
    )
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
