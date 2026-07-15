from datetime import datetime

from backend.utils.json_storage import (
    data_file,
    load_json,
    save_json,
)
from backend.services.seller_dashboard_service import load_products


def get_messages():
    return load_json(data_file("messages"))


def save_messages(messages):
    save_json(data_file("messages"), messages)

def send_message(sender_id, receiver_id, product_id, message):
    messages = get_messages()

    new_message = {
        "id": len(messages) + 1,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "product_id": product_id,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    messages.append(new_message)

    save_messages(messages)

    return new_message

def get_conversation(user1, user2, product_id):
    messages = get_messages()

    conversation = []

    for msg in messages:
        if (
            msg["product_id"] == product_id
            and (
                (
                    msg["sender_id"] == user1
                    and msg["receiver_id"] == user2
                )
                or
                (
                    msg["sender_id"] == user2
                    and msg["receiver_id"] == user1
                )
            )
        ):
            conversation.append(msg)

    conversation.sort(key=lambda x: x["timestamp"])

    return conversation

def get_product(product_id):
    products = load_products()

    for product in products:
        if product["id"] == product_id:
            return product

    return None

def get_seller_conversations(username):

    messages = get_messages()

    print("Seller =", username)

    for message in messages:
        print(message)

    products = load_products()

    conversations = []

    seen = set()

    for message in messages:

        if message.get("receiver") != username:
            continue

        key = (
            message.get("product_id"),
            message.get("sender")
        )

        if key in seen:
            continue

        seen.add(key)

        product_name = "Unknown Product"

        for product in products:
            if product["id"] == message.get("product_id"):
                product_name = product["title"]
                break

        conversations.append({
            "product_id": message.get("product_id"),
            "product_name": product_name,
            "sender": message.get("sender"),
            "text": message.get("text"),
            "timestamp": message.get("timestamp", "")
        })

    print("Conversations:", conversations)

    return conversations

def get_unread_count(username):
    messages = get_messages()

    print("========== ALL MESSAGES ==========")

    for message in messages:
        print(message)

    print("========== USER ==========")
    print(username)

    count = 0

    for message in messages:
        if (
            message.get("receiver") == username
            and not message.get("read", False)
        ):
            count += 1

    print("Unread =", count)

    return count
