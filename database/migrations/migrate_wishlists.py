import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import MySQLDatabaseError, get_mysql_connection


SOURCE_FILE = PROJECT_ROOT / "backend" / "data" / "wishlists.json"


def load_source_records():
    with open(SOURCE_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, (dict, list)):
        raise ValueError("wishlists.json must contain an object or list.")

    return records


def valid_positive_int(value):
    if isinstance(value, bool):
        return None

    try:
        number = int(value)
    except (TypeError, ValueError):
        return None

    return number if number > 0 else None


def load_json_rows(filename):
    path = PROJECT_ROOT / "backend" / "data" / filename
    try:
        with open(path, "r", encoding="utf-8") as file:
            rows = json.load(file)
    except Exception:
        return []

    return rows if isinstance(rows, list) else []


def ids_from_rows(rows):
    return {
        item_id for item_id in
        (valid_positive_int(row.get("id")) for row in rows)
        if item_id is not None
    }


def user_ids_from_mysql(cursor):
    cursor.execute("SELECT id FROM users")
    return {row["id"] for row in cursor.fetchall()}


def product_ids_from_mysql(cursor):
    cursor.execute("SELECT id FROM products")
    return {row["id"] for row in cursor.fetchall()}


def collect_wishlist_pairs(records):
    pairs = []
    invalid = 0

    if isinstance(records, dict):
        for raw_user_id, product_ids in records.items():
            user_id = valid_positive_int(raw_user_id)
            if user_id is None or not isinstance(product_ids, list):
                invalid += 1
                continue

            for raw_product_id in product_ids:
                product_id = valid_positive_int(raw_product_id)
                if product_id is None:
                    invalid += 1
                    continue
                pairs.append((user_id, product_id))

        return pairs, invalid

    for record in records:
        if not isinstance(record, dict):
            invalid += 1
            continue

        user_id = valid_positive_int(record.get("user_id"))
        product_id = valid_positive_int(record.get("product_id"))
        if user_id is None or product_id is None:
            invalid += 1
            continue
        pairs.append((user_id, product_id))

    return pairs, invalid


def migrate(dry_run=False):
    records = load_source_records()
    pairs, invalid = collect_wishlist_pairs(records)
    summary = {
        "source": len(pairs) + invalid,
        "inserted": 0,
        "skipped": 0,
        "invalid": invalid,
        "missing_users": 0,
        "missing_products": 0,
    }
    missing_users = set()
    missing_products = set()
    seen = set()

    if dry_run:
        user_ids = ids_from_rows(load_json_rows("users.json"))
        product_ids = ids_from_rows(load_json_rows("products.json"))

        for user_id, product_id in pairs:
            key = (user_id, product_id)
            if key in seen:
                summary["skipped"] += 1
                continue
            seen.add(key)

            if user_id not in user_ids:
                missing_users.add(user_id)
                summary["missing_users"] += 1
                summary["skipped"] += 1
                continue
            if product_id not in product_ids:
                missing_products.add(product_id)
                summary["missing_products"] += 1
                summary["skipped"] += 1
                continue
            summary["skipped"] += 1

        return summary, sorted(missing_users), sorted(missing_products)

    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()

        user_ids = user_ids_from_mysql(cursor)
        product_ids = product_ids_from_mysql(cursor)

        for user_id, product_id in pairs:
            key = (user_id, product_id)
            if key in seen:
                summary["skipped"] += 1
                continue
            seen.add(key)

            if user_id not in user_ids:
                missing_users.add(user_id)
                summary["missing_users"] += 1
                summary["skipped"] += 1
                continue
            if product_id not in product_ids:
                missing_products.add(product_id)
                summary["missing_products"] += 1
                summary["skipped"] += 1
                continue

            cursor.execute(
                """
                INSERT INTO wishlists (user_id, product_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE user_id = user_id
                """,
                (user_id, product_id),
            )
            if cursor.rowcount == 1:
                summary["inserted"] += 1
            else:
                summary["skipped"] += 1

        connection.commit()
        return summary, sorted(missing_users), sorted(missing_products)
    except Exception as error:
        if connection is not None:
            connection.rollback()
        if isinstance(error, MySQLDatabaseError):
            raise
        raise MySQLDatabaseError("Wishlist migration failed.") from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def print_summary(summary, missing_users, missing_products, dry_run=False):
    mode = "DRY RUN" if dry_run else "MIGRATION"
    print(f"{mode} wishlist migration summary")
    print(f"source record count: {summary['source']}")
    print(f"inserted count: {summary['inserted']}")
    print(f"skipped count: {summary['skipped']}")
    print(f"invalid count: {summary['invalid']}")
    print(f"missing user count: {summary['missing_users']}")
    print(f"missing product count: {summary['missing_products']}")
    if missing_users:
        print("missing users:")
        for user_id in missing_users:
            print(f"- {user_id}")
    if missing_products:
        print("missing products:")
        for product_id in missing_products:
            print(f"- {product_id}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate backend/data/wishlists.json to MySQL."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        summary, missing_users, missing_products = migrate(dry_run=args.dry_run)
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print_summary(summary, missing_users, missing_products, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
