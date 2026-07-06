from flask import Blueprint, render_template, request, redirect

from backend.services.chat_service import (
    get_messages,
    save_messages,
    get_product
)

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat/<int:product_id>", methods=["GET", "POST"])
def chat(product_id):

    all_messages = get_messages()

    product = get_product(product_id)

    messages = [
        msg
        for msg in all_messages
        if msg.get("product_id") == product_id
    ]

    if request.method == "POST":

        text = request.form.get("message")

        if text:

            all_messages.append({
                "product_id": product_id,
                "sender": "buyer",
                "text": text
            })

            save_messages(all_messages)

        return redirect(f"/chat/{product_id}")

    return render_template(
        "user/chat.html",
        messages=messages,
        product=product
    )