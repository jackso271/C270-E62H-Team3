from datetime import datetime

from backend.utils.json_storage import data_file, load_json, save_json


def create_admin():
    """Ensure the default admin account exists for demonstrations and marking."""
    users = load_json(data_file("users"))
    admin_exists = False

    for user in users:
        if user.get("username") == "admin":
            admin_exists = True
            user["name"] = user.get("name") or "Admin"
            user["email"] = user.get("email") or "admin@rp.edu.sg"
            user["student_id"] = user.get("student_id") or "admin"
            user["role"] = "admin"
            user["blocked"] = user.get("blocked", False)

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
        })

    save_json(data_file("users"), users)


def log_success(user):
    logs = load_json(data_file("success_logs"))
    logs.append({
        "name": user.get("name") or user.get("username") or "Unknown",
        "username": user.get("username"),
        "role": user.get("role"),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_json(data_file("success_logs"), logs)


def log_failed(username, reason):
    logs = load_json(data_file("failed_logs"))
    logs.append({
        "username": username,
        "reason": reason,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_json(data_file("failed_logs"), logs)


def find_matching_user(login_id, password):
    """Return a user matching the original login rules, or None."""
    users = load_json(data_file("users"))

    for user in users:
        username = str(user.get("username", "")).strip().lower()
        email = str(user.get("email", "")).strip().lower()
        student_id = str(user.get("student_id", "")).strip().lower()
        saved_password = str(user.get("password", "")).strip()
        name = str(user.get("name", "")).strip().lower()

        if (
            login_id == username
            or login_id == email
            or login_id == student_id
            or login_id == name
        ) and password == saved_password:
            return user

    return None


def register_user(form):
    """Validate and save a new student account using the original rules."""
    email = form.get("email")
    username = form.get("username")
    student_id = form.get("student_id")
    users = load_json(data_file("users"))

    if not email.endswith("@myrp.edu.sg"):
        return False, "Invalid RP Email", (
            "Only RP students using official RP emails are allowed to register."
        )

    for user in users:
        if user.get("username") == username or user.get("student_id") == student_id:
            return False, "Account Already Exists", (
                "This username, student ID, or email is already registered."
            )

    users.append({
        "id": len(users) + 1,
        "name": form.get("name"),
        "username": username,
        "email": email,
        "student_id": student_id,
        "school": form.get("school"),
        "password": form.get("password"),
        "role": "student",
        "blocked": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_json(data_file("users"), users)

    return True, None, None
