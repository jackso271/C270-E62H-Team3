import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import MySQLDatabaseError, get_mysql_connection


REQUIRED_COLUMNS = {
    "two_factor_enabled": "BOOLEAN NOT NULL DEFAULT FALSE",
    "two_factor_secret": "VARCHAR(64) NULL",
}
LEGACY_ENABLED_COLUMN = "two_facter_enabled"


def user_columns(cursor):
    cursor.execute("SHOW COLUMNS FROM users")
    return {row[0] for row in cursor.fetchall()}


def migration_plan(columns):
    statements = []
    adding_enabled_column = "two_factor_enabled" not in columns

    for column, definition in REQUIRED_COLUMNS.items():
        if column not in columns:
            statements.append(
                f"ALTER TABLE users ADD COLUMN {column} {definition}"
            )

    if (
        LEGACY_ENABLED_COLUMN in columns
        and ("two_factor_enabled" in columns or adding_enabled_column)
    ):
        statements.append(
            """
            UPDATE users
            SET two_factor_enabled = two_facter_enabled
            WHERE two_factor_enabled = FALSE
              AND two_facter_enabled = TRUE
            """
        )

    return statements


def migrate(dry_run=False):
    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor()
        columns = user_columns(cursor)
        statements = migration_plan(columns)

        if dry_run:
            return {"planned": len(statements), "applied": 0}

        if not statements:
            return {"planned": 0, "applied": 0}

        connection.start_transaction()
        for statement in statements:
            cursor.execute(statement)
        connection.commit()

        return {"planned": len(statements), "applied": len(statements)}
    except Exception as error:
        if connection is not None:
            connection.rollback()
        if isinstance(error, MySQLDatabaseError):
            raise
        raise MySQLDatabaseError("2FA column migration failed.") from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def print_summary(summary, dry_run=False):
    mode = "DRY RUN" if dry_run else "MIGRATION"
    print(f"{mode} 2FA column migration summary")
    print(f"planned statement count: {summary['planned']}")
    print(f"applied statement count: {summary['applied']}")


def main():
    parser = argparse.ArgumentParser(
        description="Add non-destructive 2FA columns to the users table."
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
