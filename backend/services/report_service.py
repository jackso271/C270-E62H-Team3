from datetime import datetime

from backend.utils.json_storage import (
    data_file,
    load_json,
    save_json,
)


def submit_report(product, user, reason, comments):
    reports = load_json(data_file("reports"))

    report = {
        "id": len(reports) + 1,
        "product_id": product["id"],
        "product_title": product["title"],
        "seller": product["seller"],
        "reported_by": user["username"],
        "reason": reason,
        "comments": comments,
        "status": "Pending",
        "reported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    reports.append(report)

    save_json(data_file("reports"), reports)

    return True