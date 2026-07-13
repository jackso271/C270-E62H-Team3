from flask import Blueprint, redirect, render_template, request, session

from backend.services.sell_items_service import (
    create_sell_item,
    delete_sell_item,
    get_my_sell_items,
    update_sell_item,
)


sell_items_bp = Blueprint("sell_items", __name__)

SELL_ITEMS_TEMPLATE = "user/sell_items.html"


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


@sell_items_bp.route("/sell-items")
def sell_items_page():
    user = current_user()

    if not user:
        return redirect("/")

    return render_template(
        SELL_ITEMS_TEMPLATE,
        items=get_my_sell_items(user),
    )


@sell_items_bp.route("/sell-items/create", methods=["POST"])
def create_sell_items_route():
    user = current_user()

    if not user:
        return redirect("/")

    success, message = create_sell_item(request.form, request.files, user)

    if not success:
        return render_template(
            SELL_ITEMS_TEMPLATE,
            items=get_my_sell_items(user),
            error=message,
        )

    return redirect("/sell-items")


@sell_items_bp.route("/sell-items/update/<int:product_id>", methods=["POST"])
def update_sell_items_route(product_id):
    user = current_user()

    if not user:
        return redirect("/")

    success, message = update_sell_item(
        product_id,
        request.form,
        request.files,
        user,
    )

    if not success:
        return render_template(
            SELL_ITEMS_TEMPLATE,
            items=get_my_sell_items(user),
            error=message,
        )

    return redirect("/sell-items")


@sell_items_bp.route("/sell-items/delete/<int:product_id>", methods=["POST"])
def delete_sell_items_route(product_id):
    user = current_user()

    if not user:
        return redirect("/")

    success, message = delete_sell_item(product_id, user)

    if not success:
        return render_template(
            SELL_ITEMS_TEMPLATE,
            items=get_my_sell_items(user),
            error=message,
        )

    return redirect("/sell-items")