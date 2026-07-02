from datetime import datetime

from backend.utils.json_storage import data_file, load_json, save_json


def add_notification(title, message, status="Info"):
    """Store a simple notification for users and admins to review."""
    notifications = load_json(data_file("notifications"))

    notifications.append({
        "id": len(notifications) + 1,
        "title": title,
        "message": message,
        "status": status,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    save_json(data_file("notifications"), notifications)


def get_notifications():
    notifications = load_json(data_file("notifications"))
    return list(reversed(notifications))
