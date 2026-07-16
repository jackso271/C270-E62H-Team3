import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import MySQLDatabaseError, get_mysql_connection


SOURCE_FILE = PROJECT_ROOT / "backend" / "data" / "reports.json"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def load_source_records():
    with open(SOURCE_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("reports.json must contain a JSON list.")

    return records


def parse_datetime(value):
    if not value:
        return datetime.now().strftime(DATE_FORMAT)

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

    if number <= 0:
        return None

    return number


def normalize_record(record):
    if not isinstance(record, dict):
        return None

    product_title = str(record.get("product_title") or "").strip()
    reason = str(record.get("reason") or "").strip()
    created_at = parse_datetime(record.get("reported_at"))

    if not product_title or not reason or created_at is None:
        return None

    return {
        "id": valid_positive_int(record.get("id")),
        "product_id": valid_positive_int(record.get("product_id")),
        "product_title": product_title,
        "seller_identifier": str(record.get("seller") or "").strip() or None,
        "reported_by": str(record.get("reported_by") or "").strip() or None,
        "reason": reason,
        "comments": str(record.get("comments") or "").strip() or None,
        "status": str(record.get("status") or "Pending").strip() or "Pending",
        "created_at": created_at,
    }


def duplicate_without_id(cursor, report):
    cursor.execute(
        """
        SELECT id
        FROM reports
        WHERE product_id <=> %s
          AND product_title = %s
          AND seller_identifier <=> %s
          AND reported_by <=> %s
          AND reason = %s
          AND comments <=> %s
          AND created_at = %s
        LIMIT 1
        """,
        (
            report["product_id"],
            report["product_title"],
            report["seller_identifier"],
            report["reported_by"],
            report["reason"],
            report["comments"],
            report["created_at"],
        ),
    )
    return cursor.fetchone() is not None


def insert_report(cursor, report):
    if report["id"] is not None:
        cursor.execute(
            """
            INSERT INTO reports (
                id, product_id, product_title, seller_identifier, reported_by,
                reason, comments, status, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE id = id
            """,
            (
                report["id"],
                report["product_id"],
                report["product_title"],
                report["seller_identifier"],
                report["reported_by"],
                report["reason"],
                report["comments"],
                report["status"],
                report["created_at"],
            ),
        )
        return cursor.rowcount == 1

    if duplicate_without_id(cursor, report):
        return False

    cursor.execute(
        """
        INSERT INTO reports (
            product_id, product_title, seller_identifier, reported_by,
            reason, comments, status, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            report["product_id"],
            report["product_title"],
            report["seller_identifier"],
            report["reported_by"],
            report["reason"],
            report["comments"],
            report["status"],
            report["created_at"],
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

    reports = []
    for record in records:
        report = normalize_record(record)
        if report is None:
            summary["invalid"] += 1
        else:
            reports.append(report)

    if dry_run:
        summary["skipped"] = len(reports)
        return summary

    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()

        for report in reports:
            if insert_report(cursor, report):
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
        raise MySQLDatabaseError("Report migration failed.") from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def print_summary(summary, dry_run=False):
    mode = "DRY RUN" if dry_run else "MIGRATION"
    print(f"{mode} report migration summary")
    print(f"source record count: {summary['source']}")
    print(f"inserted count: {summary['inserted']}")
    print(f"skipped count: {summary['skipped']}")
    print(f"invalid count: {summary['invalid']}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate backend/data/reports.json to MySQL."
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
