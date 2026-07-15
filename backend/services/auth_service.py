from datetime import datetime

import pyotp

from backend.services.notification_service import add_notification
from backend.utils.json_storage import data_file, load_json, save_json


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

def find_user_by_id(user_id):
    """Return a user by ID, or None."""
    users = load_json(data_file("users"))

    for user in users:
        ensure_user_shape(user)
        if str(user.get("id")) == str(user_id):
            return user

    return None


def generate_2fa_secret():
    """Generate a new secret for authenticator apps."""
    return pyotp.random_base32()


def is_valid_2fa_code(code):
    """Check that the 2FA code is exactly 6 digits."""
    clean_code = normalize_text(code)
    return clean_code.isdigit() and len(clean_code) == 6


def verify_2fa_code(secret, code):
    """Verify a 6-digit TOTP code."""
    if not secret or not is_valid_2fa_code(code):
        return False

    totp = pyotp.TOTP(secret)
    return totp.verify(normalize_text(code))


def save_user_2fa_secret(user_id, secret):
    """Save the confirmed 2FA secret into users.json."""
    users = load_json(data_file("users"))

    for user in users:
        if str(user.get("id")) == str(user_id):
            user["two_factor_enabled"] = True
            user["two_factor_secret"] = secret
            save_json(data_file("users"), users)
            return True

    return False


def user_has_2fa_enabled(user):
    """Return True only if the user already has 2FA setup."""
    return (
        user.get("two_factor_enabled") is True
        and bool(normalize_text(user.get("two_factor_secret")))
    )

def create_admin():
    """Ensure the default admin account exists for demonstrations and marking."""
    users = load_json(data_file("users"))
    admin_exists = False

    for user in users:
        ensure_user_shape(user)
        if user.get("username") == "admin":
            admin_exists = True
            user["name"] = user.get("name") or "Admin"
            user["email"] = user.get("email") or "admin@rp.edu.sg"
            user["student_id"] = user.get("student_id") or "admin"
            user["role"] = "admin"
            user["blocked"] = user.get("blocked", False)
            user["school"] = user.get("school") or "N/A"
            user["created_at"] = user.get("created_at") or "N/A"
            user["last_login"] = user.get("last_login") or "N/A"

    if not admin_exists:
        users.append({
            "id": 1,
            "name": "Admin",
            "username": "admin",
            "email": "admin@rp.edu.sg",
            "student_id": "admin",
            "password": "admin123",
            "role": "admin",
            "blocked": False,
            "school": "N/A",
            "created_at": "N/A",
            "last_login": "N/A",
        })

    save_json(data_file("users"), users)


def log_success(user):
    logs = load_json(data_file("success_logs"))
    login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logs.append({
        "name": user.get("name") or user.get("username") or "Unknown",
        "username": user.get("username"),
        "role": user.get("role"),
        "time": login_time,
    })
    save_json(data_file("success_logs"), logs)

    users = load_json(data_file("users"))
    for saved_user in users:
        if saved_user.get("id") == user.get("id"):
            saved_user["last_login"] = login_time
            break
    save_json(data_file("users"), users)


def log_failed(username, reason):
    logs = load_json(data_file("failed_logs"))
    logs.append({
        "username": username,
        "reason": reason,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_json(data_file("failed_logs"), logs)


def log_password_reset_request(login_id):
    log_failed(login_id or "Unknown", "Password reset requested")
    add_notification(
        "Password reset requested",
        f"Password reset requested for {login_id or 'Unknown login ID'}.",
        "Info",
    )


def find_user_by_login_id(login_id):
    """Return a user matching the original login ID rules, or None."""
    users = load_json(data_file("users"))
    clean_login_id = normalize_text(login_id)
    lower_login_id = clean_login_id.lower()

    for user in users:
        username = normalize_text(user.get("username")).lower()
        email = normalize_email(user.get("email"))
        student_id = normalize_text(user.get("student_id"))
        name = normalize_text(user.get("name")).lower()

        if (
            lower_login_id == username
            or lower_login_id == email
            or clean_login_id == student_id
            or lower_login_id == name
        ):
            return user

    return None


def find_matching_user(login_id, password):
    """Return a user matching the original login rules, or None."""
    user = find_user_by_login_id(login_id)

    if not user:
        return None

    saved_password = str(user.get("password", "")).strip()

    if password == saved_password:
        return user

    return None


def register_user(form):
    """Validate and save a new student account using the original rules."""
    name = normalize_text(form.get("name"))
    username = normalize_text(form.get("username"))
    email = normalize_email(form.get("email"))
    student_id = normalize_text(form.get("student_id"))
    password = normalize_text(form.get("password"))
    school = normalize_text(form.get("school")) or "N/A"
    users = load_json(data_file("users"))

    if not name or not username or not email or not student_id or not password:
        return False, "Missing Registration Details", (
            "Name, username, email, student ID, and password are required."
        )

    if not email.endswith("@myrp.edu.sg"):
        return False, "Invalid RP Email", (
            "Only RP students using official RP emails are allowed to register."
        )

    new_username = username.lower()
    for user in users:
        saved_username = normalize_text(user.get("username")).lower()
        saved_email = normalize_email(user.get("email"))
        saved_student_id = normalize_text(user.get("student_id"))

        if (
            (saved_username and saved_username == new_username)
            or (saved_email and saved_email == email)
            or (saved_student_id and saved_student_id == student_id)
        ):
            return False, "Account Already Exists", (
                "Username, email, or student ID already exists."
            )

    users.append({
        "id": len(users) + 1,
        "name": name,
        "username": username,
        "email": email,
        "student_id": student_id,
        "school": school,
        "password": password,
        "role": "student",
        "blocked": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_login": "N/A",
    })
    save_json(data_file("users"), users)

    return True, None, None
