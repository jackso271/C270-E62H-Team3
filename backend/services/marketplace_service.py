from datetime import datetime

from backend.db import (
    execute_mysql_query,
    get_mysql_connection,
    mysql_requests_enabled,
    mysql_wishlists_enabled,
)
from backend.services.notification_service import add_notification
from backend.services.seller_dashboard_service import (
    clean_product,
    load_products,
    product_belongs_to_seller,
    seller_name,
    save_products,
)
from backend.utils.json_storage import data_file, load_json, save_json


ACTIVE_REQUEST_STATUSES = ["Pending", "Accepted", "Approved"]
SOLD_STATUSES = ["Sold"]
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_products():
    return [clean_product(product) for product in load_products()]


def get_requests():
    if mysql_requests_enabled():
        rows = execute_mysql_query(
            """
            SELECT pr.id, pr.product_id, pr.buyer_id, pr.buyer_identifier,
                   pr.status, pr.rejection_reason, pr.requested_at,
                   pr.reviewed_at, p.title AS product_title,
                   p.seller_id, p.seller_identifier, p.legacy_seller_name,
                   u.username AS buyer_username, u.name AS buyer_name,
                   seller.username AS seller_username,
                   seller.name AS seller_name
            FROM purchase_requests pr
            JOIN products p ON p.id = pr.product_id
            LEFT JOIN users u ON u.id = pr.buyer_id
            LEFT JOIN users seller ON seller.id = p.seller_id
            ORDER BY pr.requested_at DESC, pr.id DESC
            """,
            fetch=True,
        )
        return [request_from_mysql(row) for row in rows]

    return load_json(data_file("requests"))


def format_datetime(value):
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime(DATE_FORMAT)
    return str(value)


def request_from_mysql(row):
    buyer = (
        row.get("buyer_username")
        or row.get("buyer_name")
        or row.get("buyer_identifier")
        or "Unknown buyer"
    )
    seller = (
        row.get("legacy_seller_name")
        or row.get("seller_username")
        or row.get("seller_name")
        or row.get("seller_identifier")
        or "Unknown seller"
    )

    return {
        "id": row.get("id"),
        "product_id": row.get("product_id"),
        "product_title": row.get("product_title") or "Marketplace item",
        "buyer": buyer,
        "buyer_id": row.get("buyer_id"),
        "buyer_identifier": row.get("buyer_identifier"),
        "seller": seller,
        "seller_id": row.get("seller_id"),
        "status": row.get("status"),
        "rejection_reason": row.get("rejection_reason"),
        "time": format_datetime(row.get("requested_at")),
        "reviewed_at": format_datetime(row.get("reviewed_at")),
    }


def get_wishlists():
    wishlists = load_json(data_file("wishlists"))
    if isinstance(wishlists, dict):
        return wishlists
    return {}


def save_wishlists(wishlists):
    save_json(data_file("wishlists"), wishlists)


def wishlist_key(user):
    return str(user.get("user_id"))


def get_wishlist_ids(user):
    if not user:
        return []

    if mysql_wishlists_enabled():
        rows = execute_mysql_query(
            """
            SELECT product_id
            FROM wishlists
            WHERE user_id = %s
            ORDER BY added_at DESC, product_id
            """,
            (user.get("user_id"),),
            fetch=True,
        )
        return [row["product_id"] for row in rows]

    wishlist = get_wishlists().get(wishlist_key(user), [])
    return [
        product_id for product_id in wishlist
        if isinstance(product_id, int)
    ]


def get_wishlist_products(user):
    saved_ids = set(get_wishlist_ids(user))
    return [
        product for product in get_marketplace_products(user)
        if product.get("id") in saved_ids
    ]


def add_to_wishlist(product_id, user):
    if not user or get_product_by_id(product_id) is None:
        return False

    if mysql_wishlists_enabled():
        execute_mysql_query(
            """
            INSERT INTO wishlists (user_id, product_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE user_id = user_id
            """,
            (user.get("user_id"), product_id),
        )
        return True

    wishlists = get_wishlists()
    key = wishlist_key(user)
    saved_ids = wishlists.setdefault(key, [])

    if product_id not in saved_ids:
        saved_ids.append(product_id)
        save_wishlists(wishlists)

    return True


def remove_from_wishlist(product_id, user):
    if not user:
        return False

    if mysql_wishlists_enabled():
        execute_mysql_query(
            """
            DELETE FROM wishlists
            WHERE user_id = %s AND product_id = %s
            """,
            (user.get("user_id"), product_id),
        )
        return True

    wishlists = get_wishlists()
    key = wishlist_key(user)
    saved_ids = wishlists.get(key, [])

    if product_id in saved_ids:
        saved_ids.remove(product_id)
        save_wishlists(wishlists)

    return True


def get_request_buyer(user):
    return seller_name(user)


def request_belongs_to_buyer(request_item, user):
    request_buyer_id = request_item.get("buyer_id")
    user_id = user.get("user_id") or user.get("id")

    if request_buyer_id is not None and user_id is not None:
        try:
            return int(request_buyer_id) == int(user_id)
        except (TypeError, ValueError):
            return False

    return request_item.get("buyer") == get_request_buyer(user)


def request_is_active(request_item):
    return request_item.get("status") in ACTIVE_REQUEST_STATUSES


def user_has_active_request(product_id, user):
    for request_item in get_requests():
        if (
            request_item.get("product_id") == product_id
            and request_belongs_to_buyer(request_item, user)
            and request_is_active(request_item)
        ):
            return True

    return False


def get_product_by_id(product_id):
    for product in get_products():
        if product.get("id") == product_id:
            return product

    return None


def get_marketplace_products(user=None):
    products = get_products()
    wishlist_ids = set(get_wishlist_ids(user))

    if not user:
        for product in products:
            product["request_state"] = "login_required"
            product["wishlist_saved"] = False
        return products

    for product in products:
        product["wishlist_saved"] = product.get("id") in wishlist_ids

        if product_belongs_to_seller(product, user):
            product["request_state"] = "own_listing"
        elif product.get("status") in SOLD_STATUSES:
            product["request_state"] = "sold"
        elif product.get("status") != "Available":
            product["request_state"] = "not_available"
        elif user_has_active_request(product.get("id"), user):
            product["request_state"] = "already_requested"
        else:
            product["request_state"] = "requestable"

    return products


def get_seller_requests(user, status_filter="all"):
    products = get_products()
    owned_product_ids = [
        product.get("id") for product in products
        if product_belongs_to_seller(product, user)
    ]

    requests_list = [
        request_item for request_item in get_requests()
        if request_item.get("product_id") in owned_product_ids
    ]

    def status_rank(item):
        status = item.get("status")
        if status == "Pending":
            return 0
        if status in ["Accepted", "Approved"]:
            return 1
        if status == "Rejected":
            return 2
        return 3

    requests_list = sorted(requests_list, key=status_rank)

    if status_filter == "pending":
        requests_list = [
            item for item in requests_list
            if item.get("status") == "Pending"
        ]
    elif status_filter == "approved":
        requests_list = [
            item for item in requests_list
            if item.get("status") in ["Accepted", "Approved"]
        ]
    elif status_filter == "rejected":
        requests_list = [
            item for item in requests_list
            if item.get("status") == "Rejected"
        ]

    return requests_list


def request_counts(requests_list):
    return {
        "pending": sum(
            1 for item in requests_list
            if item.get("status") == "Pending"
        ),
        "approved": sum(
            1 for item in requests_list
            if item.get("status") in ["Accepted", "Approved"]
        ),
        "rejected": sum(
            1 for item in requests_list
            if item.get("status") == "Rejected"
        ),
    }


def request_buy(product_id, user):
    products = get_products()
    requests_list = get_requests()
    product = None

    for item in products:
        if item.get("id") == product_id:
            product = item
            break

    if product is None:
        return False, "Product not found."

    if product_belongs_to_seller(product, user):
        return False, "You cannot request your own listing."

    if product.get("status") != "Available":
        return False, "This product is not available."

    if user_has_active_request(product_id, user):
        return False, "You already have an active request for this item."

    if mysql_requests_enabled():
        requested_at = datetime.now().strftime(DATE_FORMAT)
        execute_mysql_query(
            """
            INSERT INTO purchase_requests (
                product_id, buyer_id, buyer_identifier, status, requested_at
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                product["id"],
                user.get("user_id"),
                get_request_buyer(user),
                "Pending",
                requested_at,
            ),
        )
        add_notification(
            "Product request submitted",
            f"New request submitted for {product['title']}.",
            "Pending",
        )
        return True, None

    requests_list.append({
        "id": len(requests_list) + 1,
        "product_id": product["id"],
        "product_title": product["title"],
        "buyer": get_request_buyer(user),
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
    return True, None


def accept_request(request_id, user):
    if mysql_requests_enabled():
        return accept_mysql_request(request_id, user)

    requests_list = get_requests()
    products = get_products()
    reviewed_title = None

    for req in requests_list:
        if req.get("id") == request_id:
            product = get_product_by_id(req.get("product_id"))
            if product is None or not product_belongs_to_seller(product, user):
                return False, "Access denied."

            if req.get("status") != "Pending":
                return False, "Request has already been reviewed."

            req["status"] = "Accepted"
            req["reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reviewed_title = req.get("product_title", "Product request")

            for product in products:
                if product.get("id") == req.get("product_id"):
                    product["status"] = "Sold"
                    break

            break

    save_json(data_file("requests"), requests_list)
    save_products(products)
    if reviewed_title:
        add_notification(
            "Product request approved",
            f"{reviewed_title} was approved.",
            "Approved",
        )
        return True, None

    return False, "Request not found."


def reject_request(request_id, user, reason=None):
    if mysql_requests_enabled():
        return reject_mysql_request(request_id, user, reason)

    requests_list = get_requests()
    reviewed_title = None

    for req in requests_list:
        if req.get("id") == request_id:
            product = get_product_by_id(req.get("product_id"))
            if product is None or not product_belongs_to_seller(product, user):
                return False, "Access denied."

            if req.get("status") != "Pending":
                return False, "Request has already been reviewed."

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
        return True, None

    return False, "Request not found."


def request_row_for_review(cursor, request_id):
    cursor.execute(
        """
        SELECT pr.id, pr.product_id, pr.status, p.title AS product_title,
               p.seller_id, p.seller_identifier, p.legacy_seller_name,
               seller.username AS seller_username, seller.name AS seller_name
        FROM purchase_requests pr
        JOIN products p ON p.id = pr.product_id
        LEFT JOIN users seller ON seller.id = p.seller_id
        WHERE pr.id = %s
        LIMIT 1
        """,
        (request_id,),
    )
    return cursor.fetchone()


def review_product_from_row(row):
    seller = (
        row.get("legacy_seller_name")
        or row.get("seller_username")
        or row.get("seller_name")
        or row.get("seller_identifier")
    )
    return {
        "id": row.get("product_id"),
        "title": row.get("product_title"),
        "seller": seller,
        "seller_id": row.get("seller_id"),
    }


def accept_mysql_request(request_id, user):
    connection = None
    cursor = None
    reviewed_title = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()
        row = request_row_for_review(cursor, request_id)

        if row is None:
            connection.rollback()
            return False, "Request not found."

        product = review_product_from_row(row)
        if not product_belongs_to_seller(product, user):
            connection.rollback()
            return False, "Access denied."

        if row.get("status") != "Pending":
            connection.rollback()
            return False, "Request has already been reviewed."

        reviewed_at = datetime.now().strftime(DATE_FORMAT)
        reviewed_title = row.get("product_title", "Product request")
        cursor.execute(
            """
            UPDATE purchase_requests
            SET status = %s, reviewed_at = %s
            WHERE id = %s
            """,
            ("Accepted", reviewed_at, request_id),
        )
        cursor.execute(
            "UPDATE products SET status = %s WHERE id = %s",
            ("Sold", row.get("product_id")),
        )
        connection.commit()
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

    add_notification(
        "Product request approved",
        f"{reviewed_title} was approved.",
        "Approved",
    )
    return True, None


def reject_mysql_request(request_id, user, reason=None):
    connection = None
    cursor = None
    reviewed_title = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()
        row = request_row_for_review(cursor, request_id)

        if row is None:
            connection.rollback()
            return False, "Request not found."

        product = review_product_from_row(row)
        if not product_belongs_to_seller(product, user):
            connection.rollback()
            return False, "Access denied."

        if row.get("status") != "Pending":
            connection.rollback()
            return False, "Request has already been reviewed."

        reviewed_at = datetime.now().strftime(DATE_FORMAT)
        reviewed_title = row.get("product_title", "Product request")
        cursor.execute(
            """
            UPDATE purchase_requests
            SET status = %s, rejection_reason = %s, reviewed_at = %s
            WHERE id = %s
            """,
            (
                "Rejected",
                reason or "Request rejected after review.",
                reviewed_at,
                request_id,
            ),
        )
        connection.commit()
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

    add_notification(
        "Product request rejected",
        f"{reviewed_title} was rejected.",
        "Rejected",
    )
    return True, None
