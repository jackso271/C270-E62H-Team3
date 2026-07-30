from datetime import datetime

from backend.services import chat_service

# test clean_text()
def test_clean_text():
    assert chat_service.clean_text("  hello  ") == "hello"
    assert chat_service.clean_text("") == ""
    assert chat_service.clean_text(None) == ""


# test clean_key()
def test_clean_key():
    assert chat_service.clean_key("  Jason  ") == "jason"
    assert chat_service.clean_key("SELLER") == "seller"


# test get_product()
def test_get_product_found(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "load_products",
        lambda: [
            {"id": 1, "title": "Keyboard"},
            {"id": 2, "title": "Mouse"},
        ],
    )

    product = chat_service.get_product(2)

    assert product["title"] == "Mouse"


# test product not found
def test_get_product_not_found(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "load_products",
        lambda: [
            {"id": 1, "title": "Keyboard"},
        ],
    )

    assert chat_service.get_product(999) is None


# test message_from_mysql()
def test_message_from_mysql():
    row = {
        "id": 1,
        "product_id": 10,
        "sender_id": 5,
        "receiver_id": 6,
        "sender_username": "buyer",
        "receiver_username": "seller",
        "sender_name": "",
        "receiver_name": "",
        "sender_identifier": "",
        "receiver_identifier": "",
        "message_text": "Hello",
        "sent_at": datetime(2026, 7, 26, 12, 0, 0),
        "read_at": None,
    }

    message = chat_service.message_from_mysql(row)

    assert message["sender"] == "buyer"
    assert message["receiver"] == "seller"
    assert message["text"] == "Hello"
    assert message["read"] is False
    assert message["timestamp"] == "2026-07-26 12:00:00"


# test identifier_matches_user()
def test_identifier_matches_user():
    user = {
        "username": "Jason",
        "email": "jason@test.com",
    }

    assert chat_service.identifier_matches_user("Jason", user)
    assert chat_service.identifier_matches_user("jason@test.com", user)
    assert not chat_service.identifier_matches_user("someoneelse", user)


# test chat_receiver_for_product()
def test_chat_receiver_for_product():
    product = {
        "seller_identifier": "seller123",
        "seller": "Seller",
    }

    assert chat_service.chat_receiver_for_product(product) == "seller123"


# test chat_receiver_for_product() fallback
def test_chat_receiver_for_product_fallback(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "seller_name",
        lambda product: "Fallback Seller",
    )

    product = {}

    assert chat_service.chat_receiver_for_product(product) == "Fallback Seller"


# test user_can_open_seller_chat()
def test_user_can_open_seller_chat(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "product_belongs_to_seller",
        lambda product, user: True,
    )

    assert chat_service.user_can_open_seller_chat(
        {"id": 1},
        {"user_id": 2},
    )


# test user cannot open seller chat
def test_user_cannot_open_seller_chat(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "product_belongs_to_seller",
        lambda product, user: False,
    )

    assert not chat_service.user_can_open_seller_chat(
        {"id": 1},
        {"user_id": 2},
    )


# test get_unread_count()
def test_get_unread_count(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "mysql_user_for_identifier",
        lambda username: 6,
    )

    monkeypatch.setattr(
        chat_service,
        "execute_mysql_query",
        lambda *args, **kwargs: [{"unread": 4}],
    )

    assert chat_service.get_unread_count("seller") == 4


# test no unread messages 
def test_get_unread_count_no_messages(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "mysql_user_for_identifier",
        lambda username: None,
    )

    assert chat_service.get_unread_count("seller") == 0