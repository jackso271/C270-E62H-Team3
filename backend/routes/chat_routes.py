from flask import Blueprint, redirect, render_template, request, session

from backend.services.chat_service import (
    chat_receiver_for_product,
    get_chat_messages,
    get_product,
    get_seller_conversations,
    get_unread_count,
    mark_conversation_read,
    send_chat_message,
    user_can_open_seller_chat,
)


chat_bp = Blueprint("chat", __name__)


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


@chat_bp.route("/chat/<int:product_id>", methods=["GET", "POST"])
def chat(product_id):
    user = current_user()
    if not user:
        return redirect("/")

    product = get_product(product_id)
    if product is None:
        return redirect("/marketplace")

    chat_with = chat_receiver_for_product(product)

    if request.method == "POST":
        send_chat_message(
            product_id,
            user,
            chat_with,
            request.form.get("message"),
        )
        return redirect(f"/chat/{product_id}")

    return render_template(
        "user/chat.html",
        messages=get_chat_messages(product_id, user, chat_with),
        product=product,
        chat_with=chat_with,
        back_url="/marketplace",
    )


@chat_bp.route("/seller/chats")
def seller_chats():
    user = current_user()
    if not user:
        return redirect("/")

    return render_template(
        "user/seller_chats.html",
        conversations=get_seller_conversations(user),
        unread_count=get_unread_count(user["username"]),
    )


@chat_bp.route("/seller/chat/<int:product_id>/<buyer>", methods=["GET", "POST"])
def seller_chat(product_id, buyer):
    user = current_user()
    if not user:
        return redirect("/")

    product = get_product(product_id)
    if not user_can_open_seller_chat(product, user):
        return redirect("/seller/chats")

    mark_conversation_read(product_id, user, buyer)

    for message in messages:
        if (
            message["receiver"] == session.get("username")
            and not message.get("read", False)
        ):
            message["read"] = True

    save_messages(all_messages)

    if request.method == "POST":
        send_chat_message(
            product_id,
            user,
            buyer,
            request.form.get("message"),
        )
        return redirect(f"/seller/chat/{product_id}/{buyer}")

    return render_template(
        "user/chat.html",
        messages=get_chat_messages(product_id, user, buyer),
        product=product,
        chat_with=buyer,
        back_url="/seller/chats",
    )
