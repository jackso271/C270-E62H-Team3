from datetime import datetime

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


def accept_request(request_id):
    requests_list = get_requests()
    products = get_products()

    for req in requests_list:
        if req.get("id") == request_id:
            req["status"] = "Accepted"

            for product in products:
                if product.get("id") == req.get("product_id"):
                    product["status"] = "Reserved"
                    break

            break

    save_json(data_file("requests"), requests_list)
    save_json(data_file("products"), products)


def reject_request(request_id):
    requests_list = get_requests()

    for req in requests_list:
        if req.get("id") == request_id:
            req["status"] = "Rejected"
            break

    save_json(data_file("requests"), requests_list)
