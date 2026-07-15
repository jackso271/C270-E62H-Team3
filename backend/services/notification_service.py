from datetime import datetime

from backend.db import execute_mysql_query, mysql_notifications_enabled
from backend.utils.json_storage import data_file, load_json, save_json


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def notification_from_mysql(row):
    created_at = row.get("created_at")
    if isinstance(created_at, datetime):
        time_text = created_at.strftime(DATE_FORMAT)
    else:
        time_text = str(created_at or "")

    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "message": row.get("message"),
        "status": row.get("status"),
        "time": time_text,
    }


def add_notification(title, message, status="Info"):
    """Store a simple notification for users and admins to review."""
    if mysql_notifications_enabled():
        execute_mysql_query(
            """
            INSERT INTO notifications (title, message, status)
            VALUES (%s, %s, %s)
            """,
            (title, message, status),
        )
        return

    notifications = load_json(data_file("notifications"))

    notifications.append({
        "id": len(notifications) + 1,
        "title": title,
        "message": message,
        "status": status,
        "time": datetime.now().strftime(DATE_FORMAT),
    })

    save_json(data_file("notifications"), notifications)


def get_notifications():
    if mysql_notifications_enabled():
        rows = execute_mysql_query(
            """
            SELECT id, title, message, status, created_at
            FROM notifications
            ORDER BY created_at DESC, id DESC
            """,
            fetch=True,
        )
        return [notification_from_mysql(row) for row in rows]

    notifications = load_json(data_file("notifications"))
    return list(reversed(notifications))
