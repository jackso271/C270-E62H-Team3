import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


if load_dotenv:
    load_dotenv()


TRUE_VALUES = {"1", "true", "yes", "on"}


class MySQLDatabaseError(RuntimeError):
    """Raised when MySQL notification storage cannot be used."""


def mysql_notifications_enabled():
    return os.getenv("USE_MYSQL_NOTIFICATIONS", "").strip().lower() in TRUE_VALUES


def mysql_reports_enabled():
    return os.getenv("USE_MYSQL_REPORTS", "").strip().lower() in TRUE_VALUES


def mysql_users_enabled():
    return os.getenv("USE_MYSQL_USERS", "").strip().lower() in TRUE_VALUES


def mysql_login_logs_enabled():
    return os.getenv("USE_MYSQL_LOGIN_LOGS", "").strip().lower() in TRUE_VALUES


def mysql_products_enabled():
    return os.getenv("USE_MYSQL_PRODUCTS", "").strip().lower() in TRUE_VALUES


def mysql_requests_enabled():
    return os.getenv("USE_MYSQL_REQUESTS", "").strip().lower() in TRUE_VALUES


def mysql_wishlists_enabled():
    return os.getenv("USE_MYSQL_WISHLISTS", "").strip().lower() in TRUE_VALUES


def mysql_messages_enabled():
    return os.getenv("USE_MYSQL_MESSAGES", "").strip().lower() in TRUE_VALUES


def mysql_config():
    try:
        port = int(os.getenv("MYSQL_PORT", "3306"))
    except ValueError as error:
        raise MySQLDatabaseError("MYSQL_PORT must be a valid integer.") from error

    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": port,
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "rp_marketplace"),
    }


def get_mysql_connection():
    config = mysql_config()

    try:
        import mysql.connector

        return mysql.connector.connect(**config)
    except Exception as error:
        safe_target = (
            f"{config['user']}@{config['host']}:{config['port']}/"
            f"{config['database']}"
        )
        raise MySQLDatabaseError(
            f"Unable to connect to MySQL notifications database ({safe_target})."
        ) from error


def execute_mysql_query(query, params=None, fetch=False, dictionary=True):
    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=dictionary)
        cursor.execute(query, params or ())

        if fetch:
            return cursor.fetchall()

        connection.commit()
        return cursor.lastrowid
    except MySQLDatabaseError:
        raise
    except Exception as error:
        raise MySQLDatabaseError(
            "MySQL notifications query failed."
        ) from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
