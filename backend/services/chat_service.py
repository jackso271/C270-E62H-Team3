from datetime import datetime

from backend.utils.json_storage import (
    data_file,
    load_json,
    save_json,
)


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

from backend.utils.json_storage import data_file, load_json


def get_product(product_id):
    products = load_json(data_file("products"))

    for product in products:
        if product["id"] == product_id:
            return product

    return None

def get_seller_conversations(username):

    messages = get_messages()

    products = load_json(data_file("products"))

    conversations = []

    seen = set()

    for message in messages:

        if message.get("receiver") != username:
            continue

        key = (
            message["product_id"],
            message["sender"]
        )

        if key in seen:
            continue

        seen.add(key)

        product_name = "Unknown Product"

        for product in products:

            if product["id"] == message["product_id"]:

                product_name = product["title"]

                break

        conversations.append({

            "product_id": message["product_id"],

            "product_name": product_name,

            "sender": message["sender"],

            "text": message["text"],

            "timestamp": message.get("timestamp", "")

        })

    return conversations