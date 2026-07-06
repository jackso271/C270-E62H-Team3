from flask import Blueprint, redirect, render_template, request, session

from backend.services.marketplace_service import (
    accept_request,
    add_to_wishlist,
    get_marketplace_products,
    get_seller_requests,
    get_wishlist_products,
    get_wishlist_statistics,
    request_counts,
    reject_request,
    remove_from_wishlist,
    request_buy,
)
from backend.services.notification_service import get_notifications


marketplace_bp = Blueprint("marketplace", __name__)


def current_user():
    if "user_id" not in session:
        return None

    return {
        "user_id": session.get("user_id"),
        "name": session.get("name"),
        "username": session.get("username"),
        "email": session.get("email"),
        "student_id": session.get("student_id"),
        "role": session.get("role"),
    }


def access_denied(message="Access denied."):
    return render_template(
        "user/error.html",
        title="Access Denied",
        message=message,
        back_url="/marketplace",
    ), 403


@marketplace_bp.route("/marketplace")
def marketplace():
    user = current_user()

    search = request.args.get("search", "").lower()
    category = request.args.get("category", "")

    products = get_marketplace_products(user)

    # SEARCH
    if search:
        products = [
            p for p in products
            if search in p.get("title", "").lower()
        ]

    # FILTER
    if category:
        products = [
            p for p in products
            if p.get("category", "").lower() == category.lower()
        ]

    return render_template(
        "user/marketplace.html",
        products=products,
        search=search,
        category=category
    )


@marketplace_bp.route("/wishlist")
def wishlist():
    user = current_user()
    if not user:
        return redirect("/")

    sort_by = request.args.get("sort", "date_added")
    if sort_by not in ["date_added", "price_low", "price_high"]:
        sort_by = "date_added"

    wishlist_items = get_wishlist_products(user, sort_by)
    stats = get_wishlist_statistics(user)

    return render_template(
        "user/wishlist.html",
        wishlist_items=wishlist_items,
        sort_by=sort_by,
        stats=stats,
    )


@marketplace_bp.route("/wishlist/add/<int:product_id>", methods=["POST"])
def add_wishlist_route(product_id):
    user = current_user()
    if not user:
        return redirect("/")

    add_to_wishlist(product_id, user)
    return redirect(request.referrer or "/marketplace")


@marketplace_bp.route("/wishlist/remove/<int:product_id>", methods=["POST"])
def remove_wishlist_route(product_id):
    user = current_user()
    if not user:
        return redirect("/")

    remove_from_wishlist(product_id, user)
    return redirect(request.referrer or "/wishlist")


@marketplace_bp.route("/request_buy/<int:product_id>", methods=["POST"])
def request_buy_route(product_id):
    user = current_user()
    if not user:
        return redirect("/")

    request_buy(product_id, user)
    return redirect("/marketplace")


@marketplace_bp.route("/seller_requests")
def seller_requests():
    user = current_user()
    if not user:
        return redirect("/")

    status_filter = request.args.get("status", "all")
    if status_filter not in ["all", "pending", "approved", "rejected"]:
        status_filter = "all"

    all_requests = get_seller_requests(user)
    requests_list = get_seller_requests(user, status_filter)
    counts = request_counts(all_requests)

    if status_filter == "pending":
        empty_message = "No pending product requests."
    elif status_filter == "approved":
        empty_message = "No approved product requests."
    elif status_filter == "rejected":
        empty_message = "No rejected product requests."
    else:
        empty_message = "No product requests yet."

    return render_template(
        "user/seller_requests.html",
        requests_list=requests_list,
        status_filter=status_filter,
        empty_message=empty_message,
        pending_count=counts["pending"],
        approved_count=counts["approved"],
        rejected_count=counts["rejected"],
    )


@marketplace_bp.route("/notifications")
def notifications():
    return render_template(
        "user/notifications.html",
        notifications=get_notifications(),
    )


@marketplace_bp.route("/accept_request/<int:request_id>", methods=["POST"])
def accept_request_route(request_id):
    user = current_user()
    if not user:
        return redirect("/")

    success, message = accept_request(request_id, user)
    if not success:
        return access_denied(message)

    return redirect("/seller_requests")


@marketplace_bp.route("/reject_request/<int:request_id>", methods=["POST"])
def reject_request_route(request_id):
    user = current_user()
    if not user:
        return redirect("/")

    success, message = reject_request(
        request_id,
        user,
        request.form.get("rejection_reason"),
    )
    if not success:
        return access_denied(message)

    return redirect("/seller_requests")

@marketplace_bp.route("/product/<int:product_id>")
def product_details(product_id):
    user = current_user()

    products = get_marketplace_products(user)

    product = next(
        (p for p in products if p["id"] == product_id),
        None
    )

    if not product:
        return access_denied("Product not found.")

    return render_template(
        "user/product_details.html",
        product=product
    )
