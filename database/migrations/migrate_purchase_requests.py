import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import MySQLDatabaseError, get_mysql_connection


SOURCE_FILE = PROJECT_ROOT / "backend" / "data" / "requests.json"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def load_source_records():
    with open(SOURCE_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("requests.json must contain a JSON list.")

    return records


def normalize_text(value):
    return str(value or "").strip()


def normalize_key(value):
    return normalize_text(value).lower()


def valid_positive_int(value):
    if isinstance(value, bool):
        return None

    try:
        number = int(value)
    except (TypeError, ValueError):
        return None

    return number if number > 0 else None


def parse_datetime(value):
    if not value:
        return datetime.now().strftime(DATE_FORMAT)

    try:
        return datetime.strptime(str(value), DATE_FORMAT).strftime(DATE_FORMAT)
    except ValueError:
        return None


def load_json_rows(filename):
    path = PROJECT_ROOT / "backend" / "data" / filename
    try:
        with open(path, "r", encoding="utf-8") as file:
            rows = json.load(file)
    except Exception:
        return []

    return rows if isinstance(rows, list) else []


def user_lookup_from_rows(rows):
    lookup = {}
    for user in rows:
        user_id = valid_positive_int(user.get("id"))
        if user_id is None:
            continue
        for key in ["username", "email", "student_id", "name"]:
            value = normalize_key(user.get(key))
            if value:
                lookup[value] = user_id
    return lookup


def product_ids_from_rows(rows):
    return {
        product_id for product_id in
        (valid_positive_int(product.get("id")) for product in rows)
        if product_id is not None
    }


def user_rows_from_mysql(cursor):
    cursor.execute("SELECT id, name, username, email, student_id FROM users")
    return cursor.fetchall()


def product_ids_from_mysql(cursor):
    cursor.execute("SELECT id FROM products")
    return {row["id"] for row in cursor.fetchall()}


def normalize_record(record):
    if not isinstance(record, dict):
        return None

    product_id = valid_positive_int(record.get("product_id"))
    requested_at = parse_datetime(record.get("time"))
    status = normalize_text(record.get("status")) or "Pending"

    if product_id is None or requested_at is None:
        return None

    reviewed_at = None
    if record.get("reviewed_at"):
        reviewed_at = parse_datetime(record.get("reviewed_at"))
        if reviewed_at is None:
            return None

    return {
        "id": valid_positive_int(record.get("id")),
        "product_id": product_id,
        "buyer_identifier": normalize_text(record.get("buyer")) or None,
        "status": status,
        "rejection_reason": normalize_text(record.get("rejection_reason")) or None,
        "requested_at": requested_at,
        "reviewed_at": reviewed_at,
    }


def collect_requests():
    records = load_source_records()
    summary = {
        "source": len(records),
        "inserted": 0,
        "skipped": 0,
        "invalid": 0,
        "unresolved_buyers": 0,
        "missing_products": 0,
    }
    requests = []

    for record in records:
        request = normalize_record(record)
        if request is None:
            summary["invalid"] += 1
        else:
            requests.append(request)

    return requests, summary


def insert_request(cursor, request, buyer_id):
    if request["id"] is not None:
        cursor.execute(
            """
            INSERT INTO purchase_requests (
                id, product_id, buyer_id, buyer_identifier, status,
                rejection_reason, requested_at, reviewed_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE id = id
            """,
            (
                request["id"],
                request["product_id"],
                buyer_id,
                request["buyer_identifier"],
                request["status"],
                request["rejection_reason"],
                request["requested_at"],
                request["reviewed_at"],
            ),
        )
        return cursor.rowcount == 1

    cursor.execute(
        """
        SELECT id
        FROM purchase_requests
        WHERE product_id = %s
          AND buyer_identifier <=> %s
          AND status = %s
          AND requested_at = %s
        LIMIT 1
        """,
        (
            request["product_id"],
            request["buyer_identifier"],
            request["status"],
            request["requested_at"],
        ),
    )
    if cursor.fetchone() is not None:
        return False

    cursor.execute(
        """
        INSERT INTO purchase_requests (
            product_id, buyer_id, buyer_identifier, status,
            rejection_reason, requested_at, reviewed_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            request["product_id"],
            buyer_id,
            request["buyer_identifier"],
            request["status"],
            request["rejection_reason"],
            request["requested_at"],
            request["reviewed_at"],
        ),
    )
    return True


def migrate(dry_run=False):
    requests, summary = collect_requests()
    unresolved_buyers = set()
    missing_products = set()

    if dry_run:
        lookup = user_lookup_from_rows(load_json_rows("users.json"))
        product_ids = product_ids_from_rows(load_json_rows("products.json"))

        for request in requests:
            if request["product_id"] not in product_ids:
                missing_products.add(request["product_id"])
                summary["missing_products"] += 1
                continue

            buyer_identifier = request["buyer_identifier"]
            if buyer_identifier and normalize_key(buyer_identifier) not in lookup:
                unresolved_buyers.add(buyer_identifier)
                summary["unresolved_buyers"] += 1
            summary["skipped"] += 1

        return summary, sorted(unresolved_buyers), sorted(missing_products)

    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()

        lookup = user_lookup_from_rows(user_rows_from_mysql(cursor))
        product_ids = product_ids_from_mysql(cursor)

        for request in requests:
            if request["product_id"] not in product_ids:
                missing_products.add(request["product_id"])
                summary["missing_products"] += 1
                summary["skipped"] += 1
                continue

            buyer_identifier = request["buyer_identifier"]
            buyer_id = None
            if buyer_identifier:
                buyer_id = lookup.get(normalize_key(buyer_identifier))
                if buyer_id is None:
                    unresolved_buyers.add(buyer_identifier)
                    summary["unresolved_buyers"] += 1

            if insert_request(cursor, request, buyer_id):
                summary["inserted"] += 1
            else:
                summary["skipped"] += 1

        connection.commit()
        return summary, sorted(unresolved_buyers), sorted(missing_products)
    except Exception as error:
        if connection is not None:
            connection.rollback()
        if isinstance(error, MySQLDatabaseError):
            raise
        raise MySQLDatabaseError("Purchase request migration failed.") from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def print_summary(summary, unresolved_buyers, missing_products, dry_run=False):
    mode = "DRY RUN" if dry_run else "MIGRATION"
    print(f"{mode} purchase request migration summary")
    print(f"source record count: {summary['source']}")
    print(f"inserted count: {summary['inserted']}")
    print(f"skipped count: {summary['skipped']}")
    print(f"invalid count: {summary['invalid']}")
    print(f"unresolved buyer count: {summary['unresolved_buyers']}")
    print(f"missing product count: {summary['missing_products']}")
    if unresolved_buyers:
        print("unresolved buyers:")
        for buyer in unresolved_buyers:
            print(f"- {buyer}")
    if missing_products:
        print("missing products:")
        for product_id in missing_products:
            print(f"- {product_id}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate backend/data/requests.json to MySQL."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        summary, unresolved_buyers, missing_products = migrate(dry_run=args.dry_run)
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print_summary(summary, unresolved_buyers, missing_products, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
