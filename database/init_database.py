import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import MySQLDatabaseError, get_mysql_connection, mysql_config
from database.migrations import (
    migrate_login_attempts,
    migrate_messages,
    migrate_notifications,
    migrate_products,
    migrate_purchase_requests,
    migrate_reports,
    migrate_users,
    migrate_wishlists,
)


SCHEMA_FILE = PROJECT_ROOT / "database" / "schema.sql"
VERIFY_TABLES = [
    "notifications",
    "reports",
    "users",
    "login_attempts",
    "categories",
    "products",
    "purchase_requests",
    "wishlists",
    "messages",
]
REQUIRED_COLUMNS = {
    "notifications": {"id", "title", "message", "status", "created_at"},
    "reports": {
        "id",
        "product_id",
        "product_title",
        "seller_identifier",
        "reported_by",
        "reason",
        "comments",
        "status",
        "created_at",
        "reviewed_at",
    },
    "users": {
        "id",
        "name",
        "username",
        "email",
        "student_id",
        "school",
        "password_hash",
        "role",
        "is_blocked",
        "created_at",
        "last_login_at",
        "status_updated_at",
    },
    "login_attempts": {
        "id",
        "user_id",
        "login_identifier",
        "was_successful",
        "failure_reason",
        "attempted_at",
    },
    "categories": {"id", "name"},
    "products": {
        "id",
        "seller_id",
        "seller_identifier",
        "legacy_seller_name",
        "category_id",
        "title",
        "description",
        "price",
        "image_url",
        "status",
        "created_at",
        "updated_at",
    },
    "purchase_requests": {
        "id",
        "product_id",
        "buyer_id",
        "buyer_identifier",
        "status",
        "rejection_reason",
        "requested_at",
        "reviewed_at",
    },
    "wishlists": {"user_id", "product_id", "added_at"},
    "messages": {
        "id",
        "product_id",
        "sender_id",
        "receiver_id",
        "sender_identifier",
        "receiver_identifier",
        "message_text",
        "sent_at",
        "read_at",
    },
}
MIGRATIONS = [
    ("Notifications", migrate_notifications.migrate),
    ("Reports", migrate_reports.migrate),
    ("Users", migrate_users.migrate),
    ("Login Attempts", migrate_login_attempts.migrate),
    ("Products", migrate_products.migrate),
    ("Purchase Requests", migrate_purchase_requests.migrate),
    ("Wishlists", migrate_wishlists.migrate),
    ("Messages", migrate_messages.migrate),
]


def print_mysql_unreachable():
    print("\u274c Unable to connect to MySQL.")
    print("Please ensure MySQL Server is running.")


def server_connection():
    config = mysql_config()
    server_config = dict(config)
    server_config.pop("database", None)

    try:
        import mysql.connector

        return mysql.connector.connect(**server_config)
    except Exception as error:
        raise MySQLDatabaseError("Unable to connect to MySQL server.") from error


def verify_mysql_reachable():
    connection = None
    try:
        connection = server_connection()
        return True
    except MySQLDatabaseError:
        print_mysql_unreachable()
        return False
    finally:
        if connection is not None:
            connection.close()


def split_sql_statements(sql):
    statements = []
    current = []
    quote = None
    line_comment = False
    block_comment = False
    index = 0

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if line_comment:
            if char in "\r\n":
                line_comment = False
                current.append(char)
            index += 1
            continue

        if block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue

        if quote is None:
            if char == "-" and next_char == "-":
                previous = sql[index - 1] if index > 0 else "\n"
                after = sql[index + 2] if index + 2 < len(sql) else "\n"
                if previous in "\r\n\t " and after in "\r\n\t ":
                    line_comment = True
                    index += 2
                    continue
            if char == "#":
                line_comment = True
                index += 1
                continue
            if char == "/" and next_char == "*":
                block_comment = True
                index += 2
                continue
            if char in ("'", '"', "`"):
                quote = char
                current.append(char)
                index += 1
                continue
            if char == ";":
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
                index += 1
                continue
        else:
            current.append(char)
            if char == "\\" and quote != "`" and next_char:
                current.append(next_char)
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue

        current.append(char)
        index += 1

    statement = "".join(current).strip()
    if statement:
        statements.append(statement)

    return statements


def create_schema():
    connection = None
    cursor = None

    try:
        connection = server_connection()
        cursor = connection.cursor()
        connection.start_transaction()

        for statement in split_sql_statements(SCHEMA_FILE.read_text(encoding="utf-8")):
            cursor.execute(statement)

        connection.commit()
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def run_migrations():
    completed = []

    for label, migrate in MIGRATIONS:
        try:
            migrate(dry_run=False)
        except Exception as error:
            print(f"\u274c {label} migration failed.")
            print()
            print("Reason:")
            print()
            print(format_error_chain(error))
            print()
            print("Database initialization aborted.")
            return completed, False
        completed.append(label)

    return completed, True


def format_error_chain(error):
    messages = []
    current = error

    while current is not None:
        message = str(current)
        if message:
            messages.append(message)
        current = current.__cause__ or current.__context__

    return "\nCaused by: ".join(messages) if messages else repr(error)


def verification_details():
    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor()

        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        table_set = set(tables)

        missing_tables = [
            table for table in REQUIRED_COLUMNS
            if table not in table_set
        ]
        missing_columns = {}

        for table, required_columns in REQUIRED_COLUMNS.items():
            if table not in table_set:
                continue

            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            actual_columns = {row[0] for row in cursor.fetchall()}
            missing = sorted(required_columns - actual_columns)
            if missing:
                missing_columns[table] = missing

        counts = {}
        for table in VERIFY_TABLES:
            if table not in table_set:
                counts[table] = None
                continue
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]

        return tables, missing_tables, missing_columns, counts
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def print_success_summary(completed):
    print("======================================")
    print("RP Marketplace Database Initialized")
    print("======================================")
    print()
    print("\u2713 Schema created")
    print()
    for label in completed:
        print(f"\u2713 {label} migrated")
        print()
    print("======================================")
    print()
    print("Database Ready")
    print()
    print("======================================")


def print_verification(tables, missing_tables, missing_columns, counts):
    print()
    print("SHOW TABLES")
    for table in tables:
        print(table)

    print()
    print("Required Tables")
    if missing_tables:
        for table in missing_tables:
            print(f"{table} : missing")
    else:
        print("all required tables present")

    print()
    print("Required Columns")
    if missing_columns:
        for table, columns in sorted(missing_columns.items()):
            print(f"{table} : missing {', '.join(columns)}")
    elif missing_tables:
        print("skipped missing table column checks")
    else:
        print("all required columns present")

    print()
    print("Record Counts")
    for table in VERIFY_TABLES:
        count = counts[table]
        value = "table missing" if count is None else count
        print(f"{table} : {value}")


def verify_database():
    try:
        tables, missing_tables, missing_columns, counts = verification_details()
    except MySQLDatabaseError:
        print_mysql_unreachable()
        return False
    except Exception as error:
        print("Database verification failed.")
        print()
        print("Reason:")
        print()
        print(format_error_chain(error))
        return False

    print_verification(tables, missing_tables, missing_columns, counts)
    return not missing_tables and not missing_columns


def main():
    parser = argparse.ArgumentParser(
        description="Initialize or verify the RP Marketplace MySQL database."
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify connection, tables, required columns, and row counts.",
    )
    args = parser.parse_args()

    if args.verify:
        return 0 if verify_database() else 1

    if not verify_mysql_reachable():
        return 1

    try:
        create_schema()
    except Exception as error:
        print("Schema creation failed.")
        print()
        print("Reason:")
        print()
        print(format_error_chain(error))
        print()
        print("Database initialization aborted.")
        return 1

    completed, ok = run_migrations()
    if not ok:
        return 1

    print_success_summary(completed)
    return 0 if verify_database() else 1


if __name__ == "__main__":
    raise SystemExit(main())
