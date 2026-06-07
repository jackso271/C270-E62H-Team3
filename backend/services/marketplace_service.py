from datetime import datetime

from backend.services.notification_service import add_notification
from backend.utils.json_storage import data_file, load_json, save_json


def get_products():
    return load_json(data_file("products"))


def get_requests():
    return load_json(data_file("requests"))


def request_buy(product_id):
    products = get_products()
    requests_list = get_requests()
    product = None

    for item in products:
        if item.get("id") == product_id:
            product = item
            break

    if product is None or product.get("status") != "Available":
        return

    requests_list.append({
        "id": len(requests_list) + 1,
        "product_id": product["id"],
        "product_title": product["title"],
        "buyer": "buyer_demo",
        "seller": product["seller"],
        "status": "Pending",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    save_json(data_file("requests"), requests_list)
    add_notification(
        "Product request submitted",
        f"New request submitted for {product['title']}.",
        "Pending",
    )


def accept_request(request_id):
    requests_list = get_requests()
    products = get_products()
    reviewed_title = None

    for req in requests_list:
        if req.get("id") == request_id:
            req["status"] = "Accepted"
            req["reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reviewed_title = req.get("product_title", "Product request")

            for product in products:
                if product.get("id") == req.get("product_id"):
                    product["status"] = "Reserved"
                    break

            break

    save_json(data_file("requests"), requests_list)
    save_json(data_file("products"), products)
    if reviewed_title:
        add_notification(
            "Product request approved",
            f"{reviewed_title} was approved.",
            "Approved",
        )


def reject_request(request_id, reason=None):
    requests_list = get_requests()
    reviewed_title = None

    for req in requests_list:
        if req.get("id") == request_id:
            req["status"] = "Rejected"
            req["rejection_reason"] = reason or "Request rejected after review."
            req["reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reviewed_title = req.get("product_title", "Product request")
            break

    save_json(data_file("requests"), requests_list)
    if reviewed_title:
        add_notification(
            "Product request rejected",
            f"{reviewed_title} was rejected.",
            "Rejected",
        )
