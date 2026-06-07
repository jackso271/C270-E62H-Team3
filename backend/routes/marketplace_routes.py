from flask import Blueprint, redirect, render_template, request

from backend.services.marketplace_service import (
    accept_request,
    get_products,
    get_requests,
    reject_request,
    request_buy,
)
from backend.services.notification_service import get_notifications


marketplace_bp = Blueprint("marketplace", __name__)


@marketplace_bp.route("/marketplace")
def marketplace():
    return render_template("user/marketplace.html", products=get_products())


@marketplace_bp.route("/request_buy/<int:product_id>", methods=["POST"])
def request_buy_route(product_id):
    request_buy(product_id)
    return redirect("/marketplace")


@marketplace_bp.route("/seller_requests")
def seller_requests():
    requests_list = get_requests()
    status_filter = request.args.get("status", "all")
    pending_count = 0
    approved_count = 0
    rejected_count = 0

    for item in requests_list:
        status = item.get("status")
        if status == "Pending":
            pending_count += 1
        elif status in ["Accepted", "Approved"]:
            approved_count += 1
        elif status == "Rejected":
            rejected_count += 1

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
        requests_list = [item for item in requests_list if item.get("status") == "Pending"]
        empty_message = "No pending product requests."
    elif status_filter == "approved":
        requests_list = [
            item for item in requests_list
            if item.get("status") in ["Accepted", "Approved"]
        ]
        empty_message = "No approved product requests."
    elif status_filter == "rejected":
        requests_list = [item for item in requests_list if item.get("status") == "Rejected"]
        empty_message = "No rejected product requests."
    else:
        empty_message = "No product requests yet."

    return render_template(
        "user/seller_requests.html",
        requests_list=requests_list,
        status_filter=status_filter,
        empty_message=empty_message,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
    )


@marketplace_bp.route("/notifications")
def notifications():
    return render_template(
        "user/notifications.html",
        notifications=get_notifications(),
    )


@marketplace_bp.route("/accept_request/<int:request_id>", methods=["POST"])
def accept_request_route(request_id):
    accept_request(request_id)
    return redirect("/seller_requests")


@marketplace_bp.route("/reject_request/<int:request_id>", methods=["POST"])
def reject_request_route(request_id):
    reject_request(request_id, request.form.get("rejection_reason"))
    return redirect("/seller_requests")
