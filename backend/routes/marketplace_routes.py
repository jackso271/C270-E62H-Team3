from flask import Blueprint, redirect, render_template, request

from backend.services.marketplace_service import (
    accept_request,
    get_products,
    get_requests,
    reject_request,
    request_buy,
)


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

    return render_template(
        "user/seller_requests.html",
        requests_list=requests_list,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
    )


@marketplace_bp.route("/accept_request/<int:request_id>", methods=["POST"])
def accept_request_route(request_id):
    accept_request(request_id)
    return redirect("/seller_requests")


@marketplace_bp.route("/reject_request/<int:request_id>", methods=["POST"])
def reject_request_route(request_id):
    reject_request(request_id, request.form.get("rejection_reason"))
    return redirect("/seller_requests")
