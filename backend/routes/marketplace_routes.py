from flask import Blueprint, redirect, render_template

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
    return render_template(
        "user/seller_requests.html",
        requests_list=get_requests(),
    )


@marketplace_bp.route("/accept_request/<int:request_id>", methods=["POST"])
def accept_request_route(request_id):
    accept_request(request_id)
    return redirect("/seller_requests")


@marketplace_bp.route("/reject_request/<int:request_id>", methods=["POST"])
def reject_request_route(request_id):
    reject_request(request_id)
    return redirect("/seller_requests")
