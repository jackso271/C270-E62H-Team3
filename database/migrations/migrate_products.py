import argparse
import json
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import MySQLDatabaseError, get_mysql_connection


SOURCE_FILE = PROJECT_ROOT / "backend" / "data" / "products.json"
FALLBACK_USERNAME_ENV = "LEGACY_PRODUCT_OWNER_USERNAME"


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


def user_rows_from_json():
    path = PROJECT_ROOT / "backend" / "data" / "users.json"
    try:
        with open(path, "r", encoding="utf-8") as file:
            users = json.load(file)
    except Exception:
        return []

    if not isinstance(users, list):
        return []

    return users


def user_lookup_from_rows(rows):
    lookup = {}
    for user in rows:
        user_id = valid_positive_int(user.get("id"))
        if user_id is None:
            continue
        for key in ["username", "name", "email", "student_id"]:
            value = normalize_key(user.get(key))
            if value:
                lookup[value] = {
                    "id": user_id,
                    "username": normalize_text(user.get("username")),
                    "name": normalize_text(user.get("name")),
                    "role": normalize_text(user.get("role")) or "student",
                }
    return lookup


def non_admin_users(rows):
    return [
        user for user in rows
        if normalize_key(user.get("role")) != "admin"
    ]


def available_non_admin_usernames(rows):
    usernames = []
    for user in non_admin_users(rows):
        username = normalize_text(user.get("username"))
        if username:
            usernames.append(username)
    return usernames


def configured_fallback_username():
    return normalize_text(os.getenv(FALLBACK_USERNAME_ENV))


def fallback_config_error(message, available):
    return ValueError(
        message
        + "\nSet LEGACY_PRODUCT_OWNER_USERNAME in your local .env before "
        "migrating legacy products."
        + "\nAvailable non-admin usernames: "
        + (", ".join(available) if available else "none")
    )


def fallback_user_from_rows(rows):
    fallback_username = configured_fallback_username()
    available = available_non_admin_usernames(rows)

    if not fallback_username:
        raise fallback_config_error(
            "LEGACY_PRODUCT_OWNER_USERNAME is required for unmatched legacy "
            "product sellers.",
            available,
        )

    for user in non_admin_users(rows):
        if normalize_key(user.get("username")) == normalize_key(fallback_username):
            user_id = valid_positive_int(user.get("id"))
            if user_id is None:
                raise fallback_config_error(
                    "Configured legacy product owner "
                    f"'{fallback_username}' is invalid because it has no valid id.",
                    available,
                )
            return {
                "id": user_id,
                "username": normalize_text(user.get("username")),
                "name": normalize_text(user.get("name")),
                "role": normalize_text(user.get("role")) or "student",
            }

    raise fallback_config_error(
        "Configured legacy product owner "
        f"'{fallback_username}' was not found as a non-admin user.",
        available,
    )


def user_rows_from_mysql(cursor):
    cursor.execute("SELECT id, name, username, email, student_id, role FROM users")
    return cursor.fetchall()


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


def insert_product(cursor, product, seller_id, seller_identifier, legacy_seller_name):
    cat_id = category_id(cursor, product["category"])

    if product["id"] is not None:
        cursor.execute(
            """
            INSERT INTO products (
                id, seller_id, seller_identifier, legacy_seller_name,
                category_id, title, description, price, image_url, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE id = id
            """,
            (
                product["id"],
                seller_id,
                seller_identifier,
                legacy_seller_name,
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
        WHERE seller_id = %s
          AND title = %s
          AND price = %s
        LIMIT 1
        """,
        (seller_id, product["title"], product["price"]),
    )
    if cursor.fetchone() is not None:
        return False

    cursor.execute(
        """
        INSERT INTO products (
            seller_id, seller_identifier, legacy_seller_name, category_id,
            title, description, price, image_url, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            seller_id,
            seller_identifier,
            legacy_seller_name,
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


def resolve_product_owner(product, lookup, fallback_user):
    matched_user = lookup.get(normalize_key(product["seller_identifier"]))
    if matched_user:
        return {
            "seller_id": matched_user["id"],
            "seller_identifier": (
                matched_user.get("username")
                or matched_user.get("name")
                or product["seller_identifier"]
            ),
            "legacy_seller_name": None,
            "fallback": False,
        }

    return {
        "seller_id": fallback_user["id"],
            "seller_identifier": (
                fallback_user.get("username")
                or fallback_user.get("name")
                or configured_fallback_username()
            ),
        "legacy_seller_name": product["seller_identifier"],
        "fallback": True,
    }


def migrate(dry_run=False):
    products, summary = collect_products()
    fallback_mappings = {}
    summary["normal_matches"] = 0
    summary["fallback_mapped"] = 0

    if dry_run:
        users = user_rows_from_json()
        lookup = user_lookup_from_rows(users)
        fallback_user = fallback_user_from_rows(users)

        for product in products:
            owner = resolve_product_owner(product, lookup, fallback_user)
            if owner["fallback"]:
                summary["fallback_mapped"] += 1
                fallback_mappings[product["seller_identifier"]] = (
                    owner["seller_identifier"]
                )
            else:
                summary["normal_matches"] += 1

        summary["skipped"] = len(products)
        return summary, fallback_mappings

    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()
        users = user_rows_from_mysql(cursor)
        lookup = user_lookup_from_rows(users)
        fallback_user = fallback_user_from_rows(users)

        for product in products:
            owner = resolve_product_owner(product, lookup, fallback_user)
            if owner["fallback"]:
                summary["fallback_mapped"] += 1
                fallback_mappings[product["seller_identifier"]] = (
                    owner["seller_identifier"]
                )
            else:
                summary["normal_matches"] += 1

            if insert_product(
                cursor,
                product,
                owner["seller_id"],
                owner["seller_identifier"],
                owner["legacy_seller_name"],
            ):
                summary["inserted"] += 1
            else:
                summary["skipped"] += 1

        connection.commit()
        return summary, fallback_mappings
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


def print_summary(summary, fallback_mappings, dry_run=False):
    mode = "DRY RUN" if dry_run else "MIGRATION"
    print(f"{mode} product migration summary")
    print(f"source record count: {summary['source']}")
    print(f"normally matched sellers: {summary['normal_matches']}")
    print(f"fallback-mapped sellers: {summary['fallback_mapped']}")
    print(f"inserted count: {summary['inserted']}")
    print(f"skipped count: {summary['skipped']}")
    print(f"invalid count: {summary['invalid']}")
    if fallback_mappings:
        print("fallback seller mappings:")
        for seller, fallback in sorted(fallback_mappings.items()):
            print(f"- {seller} -> {fallback}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate backend/data/products.json to MySQL."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        summary, fallback_mappings = migrate(dry_run=args.dry_run)
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print_summary(summary, fallback_mappings, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
