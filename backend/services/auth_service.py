from datetime import datetime

import pyotp
from werkzeug.security import check_password_hash, generate_password_hash

from backend.db import (
    MySQLDatabaseError,
    execute_mysql_query,
)
from backend.services.notification_service import add_notification


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def normalize_text(value):
    """Return a stripped string for form and JSON values."""
    return str(value or "").strip()


def normalize_email(value):
    """Return a stripped, lower-case email address."""
    return normalize_text(value).lower()


def email_username(email):
    """Use the part before @ as a fallback username or name."""
    clean_email = normalize_email(email)
    if "@" in clean_email:
        return clean_email.split("@", 1)[0]
    return clean_email


def get_user_identifier(user):
    """Return the best available display identifier for a user."""
    return (
        normalize_text(user.get("username"))
        or email_username(user.get("email"))
        or normalize_text(user.get("student_id"))
        or "N/A"
    )


def ensure_user_shape(user):
    """Fill missing user fields so legacy accounts remain usable."""
    username = normalize_text(user.get("username"))
    email = normalize_email(user.get("email"))
    student_id = normalize_text(user.get("student_id"))

    if not username:
        username = email_username(email) or student_id

    name = normalize_text(user.get("name"))
    if not name:
        name = username or email_username(email) or "N/A"

    user["id"] = user.get("id")
    user["name"] = name
    user["username"] = username
    user["email"] = email
    user["student_id"] = student_id
    user["school"] = normalize_text(user.get("school")) or "N/A"
    user["password"] = user.get("password", "")
    user["role"] = normalize_text(user.get("role")) or "student"
    user["blocked"] = user.get("blocked", False)
    user["created_at"] = normalize_text(user.get("created_at")) or "N/A"
    user["last_login"] = normalize_text(user.get("last_login")) or "N/A"
    return user


def format_datetime(value):
    if isinstance(value, datetime):
        return value.strftime(DATE_FORMAT)
    return normalize_text(value) or "N/A"


def mysql_user_from_row(row, include_password=False):
    two_factor_secret = row.get("two_factor_secret")
    user = {
        "id": row.get("id"),
        "name": row.get("name") or "N/A",
        "username": row.get("username") or "N/A",
        "email": row.get("email") or "N/A",
        "student_id": row.get("student_id") or "",
        "school": row.get("school") or "N/A",
        "role": row.get("role") or "student",
        "blocked": bool(row.get("is_blocked")),
        "two_factor_enabled": bool(row.get("two_factor_enabled")) or bool(two_factor_secret),
        "two_factor_secret": two_factor_secret,
        "created_at": format_datetime(row.get("created_at")),
        "last_login": format_datetime(row.get("last_login_at")),
        "status_updated_at": format_datetime(row.get("status_updated_at")),
    }

    if include_password:
        user["password"] = row.get("password_hash") or ""

    return user


def is_unknown_2fa_column_error(error):
    current = error

    while current is not None:
        message = str(current)
        if "Unknown column" in message and "two_factor" in message:
            return True
        current = current.__cause__ or current.__context__

    return False


def load_user_2fa_fields(user):
    if not user or not user.get("id"):
        return user

    try:
        rows = execute_mysql_query(
            """
            SELECT two_factor_enabled, two_factor_secret
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            (user.get("id"),),
            fetch=True,
        )
    except MySQLDatabaseError as error:
        if is_unknown_2fa_column_error(error):
            user["two_factor_enabled"] = False
            user["two_factor_secret"] = None
            return user
        raise

    if not rows:
        user["two_factor_enabled"] = False
        user["two_factor_secret"] = None
        return user

    two_factor_secret = rows[0].get("two_factor_secret")
    user["two_factor_enabled"] = (
        bool(rows[0].get("two_factor_enabled")) or bool(two_factor_secret)
    )
    user["two_factor_secret"] = two_factor_secret
    return user


def mysql_login_attempt_from_row(row):
    attempted_at = row.get("attempted_at")
    if isinstance(attempted_at, datetime):
        time_text = attempted_at.strftime(DATE_FORMAT)
    else:
        time_text = str(attempted_at or "")

    if row.get("was_successful"):
        return {
            "name": row.get("name") or row.get("username") or "Unknown",
            "username": row.get("username") or row.get("login_identifier"),
            "role": row.get("role") or "student",
            "time": time_text,
        }

    return {
        "username": row.get("login_identifier"),
        "reason": row.get("failure_reason") or "Failed login",
        "time": time_text,
    }


def get_all_users(include_password=False):
    rows = execute_mysql_query(
        """
        SELECT id, name, username, email, student_id, school, password_hash,
               role, is_blocked, created_at, last_login_at, status_updated_at
        FROM users
        ORDER BY id
        """,
        fetch=True,
    )
    return [
        load_user_2fa_fields(mysql_user_from_row(row, include_password=include_password))
        for row in rows
    ]


def get_success_logs():
    rows = execute_mysql_query(
        """
        SELECT la.login_identifier, la.was_successful, la.failure_reason,
               la.attempted_at, u.name, u.username, u.role
        FROM login_attempts la
        LEFT JOIN users u ON u.id = la.user_id
        WHERE la.was_successful = TRUE
        ORDER BY la.attempted_at DESC, la.id DESC
        """,
        fetch=True,
    )
    return [mysql_login_attempt_from_row(row) for row in rows]


def get_failed_logs():
    rows = execute_mysql_query(
        """
        SELECT la.login_identifier, la.was_successful, la.failure_reason,
               la.attempted_at, u.name, u.username, u.role
        FROM login_attempts la
        LEFT JOIN users u ON u.id = la.user_id
        WHERE la.was_successful = FALSE
        ORDER BY la.attempted_at DESC, la.id DESC
        """,
        fetch=True,
    )
    return [mysql_login_attempt_from_row(row) for row in rows]


def password_matches(saved_password, password):
    saved_password = str(saved_password or "").strip()

    if saved_password.startswith(("pbkdf2:", "scrypt:", "argon2:")):
        return check_password_hash(saved_password, password)

    return password == saved_password


def find_mysql_user_by_login_id(login_id):
    clean_login_id = normalize_text(login_id)
    lower_login_id = clean_login_id.lower()
    rows = execute_mysql_query(
        """
        SELECT id, name, username, email, student_id, school, password_hash,
               role, is_blocked, created_at, last_login_at, status_updated_at
        FROM users
        WHERE LOWER(username) = %s
           OR LOWER(email) = %s
           OR student_id = %s
           OR LOWER(name) = %s
        LIMIT 1
        """,
        (lower_login_id, lower_login_id, clean_login_id, lower_login_id),
        fetch=True,
    )

    if not rows:
        return None

    return load_user_2fa_fields(mysql_user_from_row(rows[0], include_password=True))


def insert_login_attempt(login_identifier, was_successful, reason=None, user_id=None):
    execute_mysql_query(
        """
        INSERT INTO login_attempts (
            user_id, login_identifier, was_successful, failure_reason
        )
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, login_identifier, was_successful, reason),
    )


def create_admin():
    """Ensure the default admin account exists for demonstrations and marking."""
    existing = find_mysql_user_by_login_id("admin")
    if existing:
        return

    execute_mysql_query(
        """
        INSERT INTO users (
            id, name, username, email, student_id, school, password_hash,
            role, is_blocked, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON DUPLICATE KEY UPDATE role = VALUES(role)
        """,
        (
            1,
            "Admin",
            "admin",
            "admin@rp.edu.sg",
            "admin",
            "N/A",
            generate_password_hash("admin123"),
            "admin",
            False,
        ),
    )


def log_success(user):
    login_time = datetime.now().strftime(DATE_FORMAT)
    insert_login_attempt(
        user.get("username") or user.get("email") or str(user.get("id")),
        True,
        user_id=user.get("id"),
    )
    execute_mysql_query(
        "UPDATE users SET last_login_at = %s WHERE id = %s",
        (login_time, user.get("id")),
    )


def log_failed(username, reason):
    user = find_user_by_login_id(username)
    insert_login_attempt(
        username or "Unknown",
        False,
        reason=reason,
        user_id=user.get("id") if user else None,
    )


def log_password_reset_request(login_id):
    log_failed(login_id or "Unknown", "Password reset requested")
    add_notification(
        "Password reset requested",
        f"Password reset requested for {login_id or 'Unknown login ID'}.",
        "Info",
    )


def find_user_by_login_id(login_id):
    """Return a user matching the original login ID rules, or None."""
    return find_mysql_user_by_login_id(login_id)


def find_matching_user(login_id, password):
    """Return a user matching the original login rules, or None."""
    user = find_user_by_login_id(login_id)

    if not user:
        return None

    if password_matches(user.get("password"), password):
        user.pop("password", None)
        return user

    return None

def find_user_by_id(user_id):
    rows = execute_mysql_query(
        """
        SELECT id, name, username, email, student_id, school, password_hash,
               role, is_blocked, created_at, last_login_at, status_updated_at
        FROM users
        WHERE id = %s
        LIMIT 1
        """,
        (user_id,),
        fetch=True,
    )

    if not rows:
        return None

    return load_user_2fa_fields(mysql_user_from_row(rows[0], include_password=True))


def generate_2fa_secret():
    return pyotp.random_base32()


def verify_2fa_code(secret, code):
    clean_code = normalize_text(code)

    if not secret or not clean_code.isdigit() or len(clean_code) != 6:
        return False

    totp = pyotp.TOTP(secret)
    return totp.verify(clean_code)


def save_user_2fa_secret(user_id, secret):
    try:
        execute_mysql_query(
            """
            UPDATE users
            SET two_factor_enabled = TRUE,
                two_factor_secret = %s
            WHERE id = %s
            """,
            (secret, user_id),
        )
    except MySQLDatabaseError as error:
        if is_unknown_2fa_column_error(error):
            raise MySQLDatabaseError(
                "Two-factor authentication database columns are missing."
            ) from error
        raise

    return True


def user_has_2fa_enabled(user):
    return (
        bool(user.get("two_factor_enabled"))
        and bool(user.get("two_factor_secret"))
    )

def register_user(form):
    """Validate and save a new student account using the original rules."""
    name = normalize_text(form.get("name"))
    username = normalize_text(form.get("username"))
    email = normalize_email(form.get("email"))
    student_id = normalize_text(form.get("student_id"))
    password = normalize_text(form.get("password"))
    school = normalize_text(form.get("school")) or "N/A"
    if not name or not username or not email or not student_id or not password:
        return False, "Missing Registration Details", (
            "Name, username, email, student ID, and password are required."
        )

    if not email.endswith("@myrp.edu.sg"):
        return False, "Invalid RP Email", (
            "Only RP students using official RP emails are allowed to register."
        )

    new_username = username.lower()

    existing = execute_mysql_query(
        """
        SELECT id
        FROM users
        WHERE LOWER(username) = %s
           OR LOWER(email) = %s
           OR student_id = %s
        LIMIT 1
        """,
        (new_username, email, student_id),
        fetch=True,
    )
    if existing:
        return False, "Account Already Exists", (
            "Username, email, or student ID already exists."
        )

    execute_mysql_query(
        """
        INSERT INTO users (
            name, username, email, student_id, school, password_hash,
            role, is_blocked, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            name,
            username,
            email,
            student_id,
            school,
            generate_password_hash(password),
            "student",
            False,
            datetime.now().strftime(DATE_FORMAT),
        ),
    )

    return True, None, None
