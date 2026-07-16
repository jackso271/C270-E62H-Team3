from datetime import datetime

from backend.db import execute_mysql_query, mysql_messages_enabled
from backend.services.seller_dashboard_service import (
    load_products,
    product_belongs_to_seller,
    seller_name,
)
from backend.utils.json_storage import data_file, load_json, save_json


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def clean_text(value):
    return str(value or "").strip()


def clean_key(value):
    return clean_text(value).lower()


def user_identity(user):
    return (
        clean_text(user.get("username"))
        or clean_text(user.get("name"))
        or clean_text(user.get("email"))
        or clean_text(user.get("student_id"))
        or str(user.get("user_id"))
    )


def user_keys(user):
    keys = set()
    for key in ["username", "name", "email", "student_id", "user_id", "id"]:
        value = clean_text(user.get(key))
        if value:
            keys.add(clean_key(value))
    return keys


def identifier_matches_user(identifier, user):
    return clean_key(identifier) in user_keys(user)


def format_datetime(value):
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime(DATE_FORMAT)
    return str(value)


def message_from_mysql(row):
    sender = (
        clean_text(row.get("sender_username"))
        or clean_text(row.get("sender_name"))
        or clean_text(row.get("sender_identifier"))
    )
    receiver = (
        clean_text(row.get("receiver_username"))
        or clean_text(row.get("receiver_name"))
        or clean_text(row.get("receiver_identifier"))
    )
    return {
        "id": row.get("id"),
        "product_id": row.get("product_id"),
        "sender_id": row.get("sender_id"),
        "receiver_id": row.get("receiver_id"),
        "sender": sender,
        "receiver": receiver,
        "text": row.get("message_text"),
        "message": row.get("message_text"),
        "timestamp": format_datetime(row.get("sent_at")),
        "read": row.get("read_at") is not None,
    }


def get_messages():
    if mysql_messages_enabled():
        rows = execute_mysql_query(
            """
            SELECT m.id, m.product_id, m.sender_id, m.receiver_id,
                   m.sender_identifier, m.receiver_identifier,
                   m.message_text, m.sent_at, m.read_at,
                   sender.username AS sender_username,
                   sender.name AS sender_name,
                   receiver.username AS receiver_username,
                   receiver.name AS receiver_name
            FROM messages m
            LEFT JOIN users sender ON sender.id = m.sender_id
            LEFT JOIN users receiver ON receiver.id = m.receiver_id
            ORDER BY m.sent_at, m.id
            """,
            fetch=True,
        )
        return [message_from_mysql(row) for row in rows]

    return load_json(data_file("messages"))


def save_messages(messages):
    if mysql_messages_enabled():
        return
    save_json(data_file("messages"), messages)


def get_product(product_id):
    products = load_products()

    for product in products:
        if product["id"] == product_id:
            return product

    return None


def mysql_user_for_identifier(identifier):
    rows = execute_mysql_query(
        """
        SELECT id
        FROM users
        WHERE LOWER(username) = %s
           OR LOWER(email) = %s
           OR student_id = %s
           OR LOWER(name) = %s
        LIMIT 1
        """,
        (
            clean_key(identifier),
            clean_key(identifier),
            clean_text(identifier),
            clean_key(identifier),
        ),
        fetch=True,
    )
    return rows[0]["id"] if rows else None


def send_chat_message(product_id, sender_user, receiver_identifier, text):
    if not text:
        return None

    timestamp = datetime.now().strftime(DATE_FORMAT)

    if mysql_messages_enabled():
        execute_mysql_query(
            """
            INSERT INTO messages (
                product_id, sender_id, receiver_id, sender_identifier,
                receiver_identifier, message_text, sent_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                product_id,
                sender_user.get("user_id"),
                mysql_user_for_identifier(receiver_identifier),
                user_identity(sender_user),
                receiver_identifier,
                text,
                timestamp,
            ),
        )
        return {
            "product_id": product_id,
            "sender": user_identity(sender_user),
            "receiver": receiver_identifier,
            "text": text,
            "timestamp": timestamp,
            "read": False,
        }

    messages = get_messages()
    new_message = {
        "id": len(messages) + 1,
        "product_id": product_id,
        "sender": user_identity(sender_user),
        "receiver": receiver_identifier,
        "text": text,
        "timestamp": timestamp,
        "read": False,
    }
    messages.append(new_message)
    save_messages(messages)
    return new_message


def send_message(sender_id, receiver_id, product_id, message):
    return send_chat_message(
        product_id,
        {"user_id": sender_id, "username": str(sender_id)},
        str(receiver_id),
        message,
    )


def message_in_conversation(message, product_id, user, other_identifier):
    if message.get("product_id") != product_id:
        return False

    user_id = user.get("user_id") or user.get("id")
    other_key = clean_key(other_identifier)
    sender_id = message.get("sender_id")
    receiver_id = message.get("receiver_id")

    sent_by_user = (
        user_id is not None
        and sender_id is not None
        and str(sender_id) == str(user_id)
    ) or identifier_matches_user(message.get("sender"), user)
    received_by_user = (
        user_id is not None
        and receiver_id is not None
        and str(receiver_id) == str(user_id)
    ) or identifier_matches_user(message.get("receiver"), user)
    sent_by_other = clean_key(message.get("sender")) == other_key
    received_by_other = clean_key(message.get("receiver")) == other_key

    return (
        (sent_by_user and received_by_other)
        or (sent_by_other and received_by_user)
    )


def get_chat_messages(product_id, user, other_identifier):
    messages = [
        message for message in get_messages()
        if message_in_conversation(message, product_id, user, other_identifier)
    ]
    return sorted(messages, key=lambda item: item.get("timestamp", ""))


def get_conversation(user1, user2, product_id):
    messages = get_messages()
    conversation = []

    for msg in messages:
        if (
            msg.get("product_id") == product_id
            and (
                (msg.get("sender_id") == user1 and msg.get("receiver_id") == user2)
                or (msg.get("sender_id") == user2 and msg.get("receiver_id") == user1)
            )
        ):
            conversation.append(msg)

    return sorted(conversation, key=lambda item: item.get("timestamp", ""))


def get_seller_conversations(user):
    if isinstance(user, str):
        user = {"username": user}

    conversations = []
    seen = set()
    products = load_products()

    for message in get_messages():
        receiver_matches = identifier_matches_user(message.get("receiver"), user)
        user_id = user.get("user_id") or user.get("id")
        if (
            user_id is not None
            and message.get("receiver_id") is not None
            and str(message.get("receiver_id")) == str(user_id)
        ):
            receiver_matches = True

        if not receiver_matches:
            continue

        key = (message.get("product_id"), message.get("sender"))
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
            "timestamp": message.get("timestamp", ""),
        })

    return conversations


def get_unread_count(username):
    user_id = None
    if mysql_messages_enabled():
        user_id = mysql_user_for_identifier(username)

    count = 0
    for message in get_messages():
        receiver_matches = clean_key(message.get("receiver")) == clean_key(username)
        if (
            user_id is not None
            and message.get("receiver_id") is not None
            and str(message.get("receiver_id")) == str(user_id)
        ):
            receiver_matches = True

        if receiver_matches and not message.get("read", False):
            count += 1

    return count


def mark_conversation_read(product_id, user, other_identifier):
    if mysql_messages_enabled():
        execute_mysql_query(
            """
            UPDATE messages
            SET read_at = COALESCE(read_at, %s)
            WHERE product_id = %s
              AND receiver_id = %s
              AND (
                  LOWER(sender_identifier) = %s
                  OR sender_id = %s
              )
            """,
            (
                datetime.now().strftime(DATE_FORMAT),
                product_id,
                user.get("user_id"),
                clean_key(other_identifier),
                mysql_user_for_identifier(other_identifier),
            ),
        )
        return

    messages = get_messages()
    for message in messages:
        if (
            message_in_conversation(message, product_id, user, other_identifier)
            and identifier_matches_user(message.get("receiver"), user)
            and not message.get("read", False)
        ):
            message["read"] = True
    save_messages(messages)


def user_can_open_seller_chat(product, user):
    return product is not None and product_belongs_to_seller(product, user)


def chat_receiver_for_product(product):
    return (
        clean_text(product.get("seller_identifier"))
        or clean_text(product.get("seller"))
        or seller_name(product)
    )
