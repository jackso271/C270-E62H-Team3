from datetime import datetime

from flask import Blueprint, render_template, request, redirect, session

from backend.services.chat_service import (
    get_messages,
    save_messages,
    get_product,
    get_seller_conversations,
    get_unread_count
)

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat/<int:product_id>", methods=["GET", "POST"])
def chat(product_id):

    all_messages = get_messages()

    product = get_product(product_id)

    if "username" not in session:
        return redirect("/")

    username = session.get("username")

    messages = [
        msg
        for msg in all_messages
        if (
            msg.get("product_id") == product_id
            and (
                (
                    msg.get("sender") == session.get("username")
                    and msg.get("receiver") == product["seller"]
                )
                or
                (
                    msg.get("sender") == product["seller"]
                    and msg.get("receiver") == session.get("username")
                )
            )
        )
    ]

    if request.method == "POST":

        text = request.form.get("message")

        if text:

            all_messages.append({
                "product_id": product_id,
                "sender": session.get("username"),
                "receiver": product["seller"],
                "text": text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "read": False
            })

            save_messages(all_messages)

        return redirect(f"/chat/{product_id}")

    return render_template(
        "user/chat.html",
        messages=messages,
        product=product,
        chat_with=product["seller"],
        back_url="/marketplace"
    )

@chat_bp.route("/seller/chats")
def seller_chats():

    if "username" not in session:
        return redirect("/")

    conversations = get_seller_conversations(
        session["username"]
    )

    count = get_unread_count(session["username"])

    print("Unread from route:", count)

    return render_template(
        "user/seller_chats.html",
        conversations=conversations,
        unread_count=count
    )


@chat_bp.route("/seller/chat/<int:product_id>/<buyer>", methods=["GET", "POST"])
def seller_chat(product_id, buyer):

    all_messages = get_messages()

    product = get_product(product_id)

    print("Logged in:", session.get("username"))
    print("Product seller:", product["seller"])
    print("Buyer:", buyer)

    if "username" not in session:
        return redirect("/")

    if product["seller"] != session.get("username"):
        return redirect("/seller/chats")

    messages = [
        msg
        for msg in all_messages
        if (
            msg.get("product_id") == product_id
            and (
                (
                    msg.get("sender") == buyer
                    and msg.get("receiver") == session.get("username")
                )
                or
                (
                    msg.get("sender") == session.get("username")
                    and msg.get("receiver") == buyer
                )
            )
        )
    ]

    for message in messages:
        if (
            message["receiver"] == session.get("username")
            and not message.get("read", False)
        ):
            message["read"] = True

    save_messages(all_messages)

    if request.method == "POST":

        text = request.form.get("message")

        if text:

            all_messages.append({
                "product_id": product_id,
                "sender": session.get("username"),
                "receiver": buyer,
                "text": text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "read": False
            })

            save_messages(all_messages)

        return redirect(f"/seller/chat/{product_id}/{buyer}")

    return render_template(
        "user/chat.html",
        messages=messages,
        product=product,
        chat_with=buyer,
        back_url="/seller/chats"
    )