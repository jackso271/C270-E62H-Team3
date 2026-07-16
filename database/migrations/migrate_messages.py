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
SOURCE_FILE = LEGACY_DATA_DIR / "messages.json"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def load_source_records():
    with open(SOURCE_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("messages.json must contain a JSON list.")

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
    path = LEGACY_DATA_DIR / filename
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
    sender = normalize_text(record.get("sender"))
    receiver = normalize_text(record.get("receiver"))
    text = normalize_text(record.get("text") or record.get("message"))
    sent_at = parse_datetime(record.get("timestamp"))

    if product_id is None or not sender or not receiver or not text or sent_at is None:
        return None

    return {
        "id": valid_positive_int(record.get("id")),
        "product_id": product_id,
        "sender_identifier": sender,
        "receiver_identifier": receiver,
        "message_text": text,
        "sent_at": sent_at,
        "read_at": sent_at if record.get("read", False) else None,
    }


def collect_messages():
    records = load_source_records()
    summary = {
        "source": len(records),
        "inserted": 0,
        "skipped": 0,
        "invalid": 0,
        "unresolved_senders": 0,
        "unresolved_receivers": 0,
        "missing_products": 0,
    }
    messages = []

    for record in records:
        message = normalize_record(record)
        if message is None:
            summary["invalid"] += 1
        else:
            messages.append(message)

    return messages, summary


def insert_message(cursor, message, sender_id, receiver_id):
    if message["id"] is not None:
        cursor.execute(
            """
            INSERT INTO messages (
                id, product_id, sender_id, receiver_id, sender_identifier,
                receiver_identifier, message_text, sent_at, read_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE id = id
            """,
            (
                message["id"],
                message["product_id"],
                sender_id,
                receiver_id,
                message["sender_identifier"],
                message["receiver_identifier"],
                message["message_text"],
                message["sent_at"],
                message["read_at"],
            ),
        )
        return cursor.rowcount == 1

    cursor.execute(
        """
        SELECT id
        FROM messages
        WHERE product_id = %s
          AND sender_identifier = %s
          AND receiver_identifier = %s
          AND message_text = %s
          AND sent_at = %s
        LIMIT 1
        """,
        (
            message["product_id"],
            message["sender_identifier"],
            message["receiver_identifier"],
            message["message_text"],
            message["sent_at"],
        ),
    )
    if cursor.fetchone() is not None:
        return False

    cursor.execute(
        """
        INSERT INTO messages (
            product_id, sender_id, receiver_id, sender_identifier,
            receiver_identifier, message_text, sent_at, read_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            message["product_id"],
            sender_id,
            receiver_id,
            message["sender_identifier"],
            message["receiver_identifier"],
            message["message_text"],
            message["sent_at"],
            message["read_at"],
        ),
    )
    return True


def evaluate_messages(messages, lookup, product_ids, insert=None):
    summary = {
        "inserted": 0,
        "skipped": 0,
        "unresolved_senders": 0,
        "unresolved_receivers": 0,
        "missing_products": 0,
    }
    unresolved_senders = set()
    unresolved_receivers = set()
    missing_products = set()

    for message in messages:
        if message["product_id"] not in product_ids:
            missing_products.add(message["product_id"])
            summary["missing_products"] += 1
            summary["skipped"] += 1
            continue

        sender_id = lookup.get(normalize_key(message["sender_identifier"]))
        receiver_id = lookup.get(normalize_key(message["receiver_identifier"]))

        if sender_id is None:
            unresolved_senders.add(message["sender_identifier"])
            summary["unresolved_senders"] += 1
        if receiver_id is None:
            unresolved_receivers.add(message["receiver_identifier"])
            summary["unresolved_receivers"] += 1

        if insert is None:
            summary["skipped"] += 1
        elif insert(message, sender_id, receiver_id):
            summary["inserted"] += 1
        else:
            summary["skipped"] += 1

    return summary, unresolved_senders, unresolved_receivers, missing_products


def migrate(dry_run=False):
    messages, summary = collect_messages()

    if dry_run:
        detail, senders, receivers, products = evaluate_messages(
            messages,
            user_lookup_from_rows(load_json_rows("users.json")),
            product_ids_from_rows(load_json_rows("products.json")),
        )
        summary.update(detail)
        return summary, sorted(senders), sorted(receivers), sorted(products)

    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()
        lookup = user_lookup_from_rows(user_rows_from_mysql(cursor))
        product_ids = product_ids_from_mysql(cursor)

        detail, senders, receivers, products = evaluate_messages(
            messages,
            lookup,
            product_ids,
            insert=lambda message, sender_id, receiver_id: insert_message(
                cursor,
                message,
                sender_id,
                receiver_id,
            ),
        )
        summary.update(detail)
        connection.commit()
        return summary, sorted(senders), sorted(receivers), sorted(products)
    except Exception as error:
        if connection is not None:
            connection.rollback()
        if isinstance(error, MySQLDatabaseError):
            raise
        raise MySQLDatabaseError("Message migration failed.") from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def print_summary(summary, unresolved_senders, unresolved_receivers, missing_products, dry_run=False):
    mode = "DRY RUN" if dry_run else "MIGRATION"
    print(f"{mode} message migration summary")
    print(f"source record count: {summary['source']}")
    print(f"inserted count: {summary['inserted']}")
    print(f"skipped count: {summary['skipped']}")
    print(f"invalid count: {summary['invalid']}")
    print(f"unresolved sender count: {summary['unresolved_senders']}")
    print(f"unresolved receiver count: {summary['unresolved_receivers']}")
    print(f"missing product count: {summary['missing_products']}")
    if unresolved_senders:
        print("unresolved senders:")
        for sender in unresolved_senders:
            print(f"- {sender}")
    if unresolved_receivers:
        print("unresolved receivers:")
        for receiver in unresolved_receivers:
            print(f"- {receiver}")
    if missing_products:
        print("missing products:")
        for product_id in missing_products:
            print(f"- {product_id}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate database/legacy_seed_data/messages.json to MySQL."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        summary, senders, receivers, products = migrate(dry_run=args.dry_run)
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print_summary(summary, senders, receivers, products, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
