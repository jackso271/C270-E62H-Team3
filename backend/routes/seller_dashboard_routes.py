from flask import Blueprint, redirect, render_template, request, session

from backend.services.chat_service import get_unread_count

from backend.services.seller_dashboard_service import (
    add_product,
    count_products,
    delete_product,
    edit_product,
    get_seller_products,
)


seller_dashboard_bp = Blueprint("seller_dashboard", __name__)


def require_logged_in_user():
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
        back_url="/seller/dashboard",
    ), 403


@seller_dashboard_bp.route("/seller/dashboard")
def seller_dashboard():
    user = require_logged_in_user()
    if not user:
        return redirect("/")

    status_filter = request.args.get("status", "all")
    if status_filter not in ["all", "available", "sold"]:
        status_filter = "all"

    all_seller_products = get_seller_products(user)
    products = get_seller_products(user, status_filter)

    unread_count = get_unread_count(session["username"])

    return render_template(
        "seller_dashboard.html",
        products=products,
        stats=count_products(all_seller_products),
        status_filter=status_filter,
        unread_count=unread_count
    )


@seller_dashboard_bp.route("/seller/dashboard/add", methods=["POST"])
def add_seller_product():
    user = require_logged_in_user()
    if not user:
        return redirect("/")

    success, message = add_product(request.form, user)
    if not success:
        return access_denied(message)

    return redirect("/seller/dashboard")


@seller_dashboard_bp.route("/seller/dashboard/edit/<int:product_id>", methods=["POST"])
def edit_seller_product(product_id):
    user = require_logged_in_user()
    if not user:
        return redirect("/")

    success, message = edit_product(product_id, request.form, user)
    if not success:
        return access_denied(message)

    return redirect("/seller/dashboard")


@seller_dashboard_bp.route("/seller/dashboard/delete/<int:product_id>", methods=["POST"])
def delete_seller_product(product_id):
    user = require_logged_in_user()
    if not user:
        return redirect("/")

    success, message = delete_product(product_id, user)
    if not success:
        return access_denied(message)

    return redirect("/seller/dashboard")
