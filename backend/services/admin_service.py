from datetime import datetime, timedelta

from backend.db import execute_mysql_query
from backend.services.auth_service import get_all_users, get_failed_logs, get_success_logs
from backend.services.notification_service import get_notifications


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_time(value):
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except Exception:
        return None


def latest_login_by_user():
    latest_logins = {}

    for log in get_success_logs():
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
    users = get_all_users()
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
    users = get_all_users()
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
    """Build a simple recent activity feed from MySQL-backed services."""
    activities = []

    for user in get_all_users():
        created_at = parse_time(user.get("created_at", ""))
        if created_at:
            activities.append({
                "time": created_at,
                "label": "New account created",
                "detail": user.get("username") or user.get("email") or "Unknown user",
            })

        status_updated_at = parse_time(user.get("status_updated_at", ""))
        if status_updated_at:
            status = "blocked" if user.get("blocked", False) else "unblocked"
            activities.append({
                "time": status_updated_at,
                "label": f"User {status}",
                "detail": user.get("username") or user.get("email") or "Unknown user",
            })

    for log in get_failed_logs():
        log_time = parse_time(log.get("time", ""))
        if log_time:
            activities.append({
                "time": log_time,
                "label": log.get("reason") or "Failed login",
                "detail": log.get("username") or "Unknown login ID",
            })

    from backend.services.marketplace_service import get_requests

    for request_item in get_requests():
        request_time = parse_time(request_item.get("time", ""))
        if request_time:
            status = request_item.get("status", "Submitted")
            activities.append({
                "time": request_time,
                "label": f"Product request {status.lower()}",
                "detail": request_item.get("product_title") or "Marketplace item",
            })

    for notification in get_notifications():
        notification_time = parse_time(notification.get("time", ""))
        if notification_time:
            activities.append({
                "time": notification_time,
                "label": notification.get("title") or "Notification",
                "detail": notification.get("message") or notification.get("status") or "Info",
            })

    activities.sort(key=lambda item: item["time"], reverse=True)

    for item in activities:
        item["time_text"] = item["time"].strftime(DATE_FORMAT)

    return activities[:limit]


def get_user(user_id):
    for user in get_all_users():
        if user.get("id") == user_id:
            return user
    return None


def update_user(user_id, form):
    execute_mysql_query(
        """
        UPDATE users
        SET name = %s, username = %s, student_id = %s, role = %s
        WHERE id = %s
        """,
        (
            form.get("name"),
            form.get("username"),
            form.get("student_id"),
            form.get("role"),
            user_id,
        ),
    )


def delete_user_by_id(user_id):
    execute_mysql_query("DELETE FROM users WHERE id = %s", (user_id,))


def toggle_user_block(user_id):
    execute_mysql_query(
        """
        UPDATE users
        SET is_blocked = NOT is_blocked,
            status_updated_at = %s
        WHERE id = %s
        """,
        (datetime.now().strftime(DATE_FORMAT), user_id),
    )


def delete_logs(log_type, selected_times):
    if log_type not in ["success_logs", "failed_logs"] or not selected_times:
        return

    was_successful = log_type == "success_logs"
    for selected_time in selected_times:
        execute_mysql_query(
            """
            DELETE FROM login_attempts
            WHERE was_successful = %s
              AND DATE_FORMAT(attempted_at, '%%Y-%%m-%%d %%H:%%i:%%s') = %s
            """,
            (was_successful, selected_time),
        )
