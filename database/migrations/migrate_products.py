import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import MySQLDatabaseError, get_mysql_connection


SOURCE_FILE = PROJECT_ROOT / "backend" / "data" / "products.json"


def load_source_records():
    with open(SOURCE_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("products.json must contain a JSON list.")

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


def parse_price(value):
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

    if price < 0:
        return None

    return price.quantize(Decimal("0.01"))


def normalize_record(record):
    if not isinstance(record, dict):
        return None

    title = normalize_text(record.get("title")) or normalize_text(record.get("name"))
    description = normalize_text(record.get("description"))
    price = parse_price(record.get("price"))
    seller = normalize_text(record.get("seller"))

    if not title or price is None or not seller:
        return None

    return {
        "id": valid_positive_int(record.get("id")),
        "title": title,
        "description": description,
        "price": price,
        "image_url": normalize_text(record.get("image_url")) or None,
        "seller_identifier": seller,
        "category": normalize_text(record.get("category")) or "Others",
        "status": normalize_text(record.get("status")) or "Available",
    }


def user_lookup_from_json():
    path = PROJECT_ROOT / "backend" / "data" / "users.json"
    try:
        with open(path, "r", encoding="utf-8") as file:
            users = json.load(file)
    except Exception:
        return {}

    lookup = {}
    for user in users if isinstance(users, list) else []:
        user_id = valid_positive_int(user.get("id"))
        if user_id is None:
            continue
        for key in ["username", "name", "email", "student_id"]:
            value = normalize_key(user.get(key))
            if value:
                lookup[value] = user_id
    return lookup


def user_lookup_from_mysql(cursor):
    cursor.execute("SELECT id, name, username, email, student_id FROM users")
    rows = cursor.fetchall()
    lookup = {}
    for row in rows:
        for key in ["username", "name", "email", "student_id"]:
            value = normalize_key(row.get(key))
            if value:
                lookup[value] = row.get("id")
    return lookup


def category_id(cursor, category):
    cursor.execute(
        """
        INSERT INTO categories (name)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)
        """,
        (category,),
    )
    return cursor.lastrowid


def insert_product(cursor, product, seller_id):
    cat_id = category_id(cursor, product["category"])

    if product["id"] is not None:
        cursor.execute(
            """
            INSERT INTO products (
                id, seller_id, seller_identifier, category_id, title,
                description, price, image_url, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE id = id
            """,
            (
                product["id"],
                seller_id,
                product["seller_identifier"],
                cat_id,
                product["title"],
                product["description"],
                product["price"],
                product["image_url"],
                product["status"],
            ),
        )
        return cursor.rowcount == 1

    cursor.execute(
        """
        SELECT id
        FROM products
        WHERE seller_identifier = %s
          AND title = %s
          AND price = %s
        LIMIT 1
        """,
        (product["seller_identifier"], product["title"], product["price"]),
    )
    if cursor.fetchone() is not None:
        return False

    cursor.execute(
        """
        INSERT INTO products (
            seller_id, seller_identifier, category_id, title,
            description, price, image_url, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            seller_id,
            product["seller_identifier"],
            cat_id,
            product["title"],
            product["description"],
            product["price"],
            product["image_url"],
            product["status"],
        ),
    )
    return True


def collect_products():
    records = load_source_records()
    summary = {
        "source": len(records),
        "inserted": 0,
        "skipped": 0,
        "invalid": 0,
    }
    products = []

    for record in records:
        product = normalize_record(record)
        if product is None:
            summary["invalid"] += 1
        else:
            products.append(product)

    return products, summary


def migrate(dry_run=False):
    products, summary = collect_products()
    unmatched_sellers = set()

    if dry_run:
        lookup = user_lookup_from_json()
        for product in products:
            if normalize_key(product["seller_identifier"]) not in lookup:
                unmatched_sellers.add(product["seller_identifier"])
        summary["skipped"] = len(products)
        return summary, sorted(unmatched_sellers)

    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()
        lookup = user_lookup_from_mysql(cursor)

        for product in products:
            seller_id = lookup.get(normalize_key(product["seller_identifier"]))
            if seller_id is None:
                unmatched_sellers.add(product["seller_identifier"])

            if insert_product(cursor, product, seller_id):
                summary["inserted"] += 1
            else:
                summary["skipped"] += 1

        connection.commit()
        return summary, sorted(unmatched_sellers)
    except Exception as error:
        if connection is not None:
            connection.rollback()
        if isinstance(error, MySQLDatabaseError):
            raise
        raise MySQLDatabaseError("Product migration failed.") from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def print_summary(summary, unmatched_sellers, dry_run=False):
    mode = "DRY RUN" if dry_run else "MIGRATION"
    print(f"{mode} product migration summary")
    print(f"source record count: {summary['source']}")
    print(f"inserted count: {summary['inserted']}")
    print(f"skipped count: {summary['skipped']}")
    print(f"invalid count: {summary['invalid']}")
    if unmatched_sellers:
        print("unmatched sellers:")
        for seller in unmatched_sellers:
            print(f"- {seller}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate backend/data/products.json to MySQL."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        summary, unmatched_sellers = migrate(dry_run=args.dry_run)
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print_summary(summary, unmatched_sellers, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
