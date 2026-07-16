from datetime import datetime

from backend.db import execute_mysql_query, mysql_reports_enabled
from backend.utils.json_storage import (
    data_file,
    load_json,
    save_json,
)


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def report_from_mysql(row):
    created_at = row.get("created_at")
    if isinstance(created_at, datetime):
        reported_at = created_at.strftime(DATE_FORMAT)
    else:
        reported_at = str(created_at or "")

    return {
        "id": row.get("id"),
        "product_id": row.get("product_id"),
        "product_title": row.get("product_title"),
        "seller": row.get("seller_identifier"),
        "reported_by": row.get("reported_by"),
        "reason": row.get("reason"),
        "comments": row.get("comments"),
        "status": row.get("status"),
        "reported_at": reported_at,
    }


def get_reports():
    if mysql_reports_enabled():
        rows = execute_mysql_query(
            """
            SELECT id, product_id, product_title, seller_identifier,
                   reported_by, reason, comments, status, created_at
            FROM reports
            ORDER BY created_at DESC, id DESC
            """,
            fetch=True,
        )
        return [report_from_mysql(row) for row in rows]

    return load_json(data_file("reports"))


def submit_report(product, user, reason, comments):
    if mysql_reports_enabled():
        execute_mysql_query(
            """
            INSERT INTO reports (
                product_id, product_title, seller_identifier, reported_by,
                reason, comments, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                product.get("id"),
                product.get("title"),
                product.get("seller"),
                user.get("username"),
                reason,
                comments,
                "Pending",
            ),
        )
        return True

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
        "reported_at": datetime.now().strftime(DATE_FORMAT),
    }

    reports.append(report)

    save_json(data_file("reports"), reports)

    return True
