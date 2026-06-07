from datetime import datetime, timedelta

from backend.utils.json_storage import data_file, load_json, save_json


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_time(value):
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except Exception:
        return None


def latest_login_by_user():
    latest_logins = {}

    for log in load_json(data_file("success_logs")):
        username = log.get("username")
        log_time = parse_time(log.get("time", ""))

        if not username or not log_time:
            continue

        current_time = latest_logins.get(username)
        if current_time is None or log_time > current_time:
            latest_logins[username] = log_time

    return latest_logins


def is_admin_role(user):
    return user.get("role") == "admin"


def is_user_role(user):
    return user.get("role") != "admin"


def account_is_inactive(user, latest_logins=None):
    if latest_logins is None:
        latest_logins = latest_login_by_user()

    username = user.get("username")
    last_login = latest_logins.get(username)

    if not username or not last_login:
        return True

    return last_login < datetime.now() - timedelta(days=7)


def list_users(search="", page=1, per_page=10, status_filter="", role_filter=""):
    """Search and paginate users for the admin user table."""
    users = load_json(data_file("users"))
    search = search.lower()
    latest_logins = latest_login_by_user()

    if search:
        users = [
            user for user in users
            if (
                search in str(user.get("name", "")).lower()
                or search in str(user.get("student_id", "")).lower()
                or search in str(user.get("email", "")).lower()
                or search in str(user.get("username", "")).lower()
            )
        ]

    if status_filter == "active":
        users = [user for user in users if not user.get("blocked", False)]
    elif status_filter == "blocked":
        users = [user for user in users if user.get("blocked", False)]
    elif status_filter == "inactive":
        users = [user for user in users if account_is_inactive(user, latest_logins)]

    if role_filter == "admin":
        users = [user for user in users if is_admin_role(user)]
    elif role_filter == "user":
        users = [user for user in users if is_user_role(user)]

    total_users = len(users)
    total_pages = (total_users + per_page - 1) // per_page

    if total_pages == 0:
        total_pages = 1

    start = (page - 1) * per_page
    end = start + per_page

    return users[start:end], total_pages


def account_summary():
    users = load_json(data_file("users"))
    latest_logins = latest_login_by_user()
    seven_days_ago = datetime.now() - timedelta(days=7)

    new_accounts = 0
    blocked_accounts = 0
    inactive_accounts = 0

    for user in users:
        created_at = parse_time(user.get("created_at", ""))

        if created_at and created_at >= seven_days_ago:
            new_accounts += 1

        if user.get("blocked", False):
            blocked_accounts += 1

        if account_is_inactive(user, latest_logins):
            inactive_accounts += 1

    return {
        "total": len(users),
        "new_last_7_days": new_accounts,
        "inactive_last_7_days": inactive_accounts,
        "blocked": blocked_accounts,
    }


def recent_activity(limit=8):
    """Build a simple recent activity feed from available JSON data."""
    activities = []

    for user in load_json(data_file("users")):
        created_at = parse_time(user.get("created_at", ""))
        if created_at:
            activities.append({
                "time": created_at,
                "label": "New account created",
                "detail": user.get("username") or user.get("email") or "Unknown user",
            })

    for log in load_json(data_file("failed_logs")):
        log_time = parse_time(log.get("time", ""))
        if log_time:
            activities.append({
                "time": log_time,
                "label": log.get("reason") or "Failed login",
                "detail": log.get("username") or "Unknown login ID",
            })

    for request_item in load_json(data_file("requests")):
        request_time = parse_time(request_item.get("time", ""))
        if request_time:
            status = request_item.get("status", "Submitted")
            activities.append({
                "time": request_time,
                "label": f"Product request {status.lower()}",
                "detail": request_item.get("product_title") or "Marketplace item",
            })

    activities.sort(key=lambda item: item["time"], reverse=True)

    for item in activities:
        item["time_text"] = item["time"].strftime(DATE_FORMAT)

    return activities[:limit]


def get_user(user_id):
    for user in load_json(data_file("users")):
        if user.get("id") == user_id:
            return user
    return None


def update_user(user_id, form):
    users = load_json(data_file("users"))

    for user in users:
        if user.get("id") == user_id:
            user["name"] = form.get("name")
            user["username"] = form.get("username")
            user["student_id"] = form.get("student_id")
            user["role"] = form.get("role")
            break

    save_json(data_file("users"), users)


def delete_user_by_id(user_id):
    users = [
        user for user in load_json(data_file("users"))
        if user.get("id") != user_id
    ]
    save_json(data_file("users"), users)


def toggle_user_block(user_id):
    users = load_json(data_file("users"))

    for user in users:
        if user.get("id") == user_id:
            user["blocked"] = not user.get("blocked", False)
            user["status_updated_at"] = datetime.now().strftime(DATE_FORMAT)
            break

    save_json(data_file("users"), users)


def delete_logs(log_type, selected_times):
    logs = [
        log for log in load_json(data_file(log_type))
        if log.get("time") not in selected_times
    ]
    save_json(data_file(log_type), logs)
