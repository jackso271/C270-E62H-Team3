import json
from datetime import datetime

import pytest

from backend.app import create_app
from backend.services import auth_service
from backend.services import marketplace_service
from backend.services import notification_service
from backend.services import report_service
from backend.services import seller_dashboard_service
from database.migrations import migrate_messages
from database.migrations import migrate_purchase_requests
from database.migrations import migrate_products
from database.migrations import migrate_wishlists


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_MYSQL_NOTIFICATIONS", "false")
    monkeypatch.setenv("USE_MYSQL_REPORTS", "false")
    monkeypatch.setenv("USE_MYSQL_USERS", "false")
    monkeypatch.setenv("USE_MYSQL_LOGIN_LOGS", "false")
    monkeypatch.setenv("USE_MYSQL_PRODUCTS", "false")
    monkeypatch.setenv("USE_MYSQL_REQUESTS", "false")
    monkeypatch.setenv("USE_MYSQL_WISHLISTS", "false")
    monkeypatch.setenv("USE_MYSQL_MESSAGES", "false")

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    seed_files = {
        "users.json": [
            {
                "id": 1,
                "name": "Student One",
                "username": "student1",
                "email": "student1@myrp.edu.sg",
                "student_id": "S12345",
                "password": "password123",
                "role": "student",
                "blocked": False,
            },
            {
                "id": 2,
                "name": "Admin",
                "username": "admin",
                "email": "admin@rp.edu.sg",
                "student_id": "admin",
                "password": "admin123",
                "role": "admin",
                "blocked": False,
            },
            {
                "id": 3,
                "name": "Student Two",
                "username": "student2",
                "email": "student2@myrp.edu.sg",
                "student_id": "S23456",
                "password": "password123",
                "role": "student",
                "blocked": False,
            },
            {
                "id": 4,
                "name": "Student Three",
                "username": "student3",
                "email": "student3@myrp.edu.sg",
                "student_id": "S34567",
                "password": "password123",
                "role": "student",
                "blocked": False,
            },
            {
                "id": 5,
                "student_id": "25044459",
                "email": "25044459@myrp.edu.sg",
                "password": "password123",
                "role": "user",
                "blocked": False,
            },
        ],
        "products.json": [
            {
                "id": 1,
                "title": "Keyboard",
                "name": "Keyboard",
                "price": 25,
                "seller": "student1",
                "status": "Available",
                "category": "Electronics",
                "description": "Compact keyboard",
            },
            {
                "id": 2,
                "title": "Mouse",
                "name": "Mouse",
                "price": 15,
                "seller": "student1",
                "status": "Sold",
                "category": "Electronics",
                "description": "Wireless mouse",
            },
            {
                "id": 3,
                "title": "Monitor",
                "name": "Monitor",
                "price": 80,
                "seller": "otherstudent",
                "status": "Available",
                "category": "Electronics",
                "description": "24 inch monitor",
            },
            {
                "id": 4,
                "title": "Tablet",
                "name": "Tablet",
                "price": 120,
                "seller": "student1",
                "status": "Sold",
                "category": "Electronics",
                "description": "Sold tablet",
            },
            {
                "id": 5,
                "title": "Math Textbook",
                "name": "Math Textbook",
                "price": 12,
                "seller": "otherstudent",
                "status": "Available",
                "category": "Books",
                "description": "Used textbook",
            },
            {
                "id": 6,
                "title": "Snack Pack",
                "name": "Snack Pack",
                "price": 5,
                "seller": "otherstudent",
                "status": "Available",
                "category": "Food",
                "description": "Sealed snacks",
            },
        ],
        "requests.json": [],
        "notifications.json": [],
        "reports.json": [],
        "wishlists.json": {},
        "messages.json": [],
        "success_logins.json": [],
        "failed_logins.json": [],
    }

    for filename, content in seed_files.items():
        (data_dir / filename).write_text(json.dumps(content), encoding="utf-8")

    return create_app({
        "TESTING": True,
        "DATA_DIR": str(data_dir),
        "SECRET_KEY": "test-secret",
    })


@pytest.fixture()
def client(app):
    return app.test_client()


def read_users(app):
    users_path = app.config["DATA_DIR"] + "/users.json"
    with open(users_path, "r", encoding="utf-8") as file:
        return json.load(file)


def read_products(app):
    products_path = app.config["DATA_DIR"] + "/products.json"
    with open(products_path, "r", encoding="utf-8") as file:
        return json.load(file)


def read_requests(app):
    requests_path = app.config["DATA_DIR"] + "/requests.json"
    with open(requests_path, "r", encoding="utf-8") as file:
        return json.load(file)


def read_wishlists(app):
    wishlists_path = app.config["DATA_DIR"] + "/wishlists.json"
    with open(wishlists_path, "r", encoding="utf-8") as file:
        return json.load(file)


def read_messages(app):
    messages_path = app.config["DATA_DIR"] + "/messages.json"
    with open(messages_path, "r", encoding="utf-8") as file:
        return json.load(file)


def login_student(client):
    return login_user(client, "student1")


def login_user(client, login_id):
    return client.post(
        "/login",
        data={"login_id": login_id, "password": "password123"},
    )


def test_application_startup(app):
    assert app is not None
    assert app.name == "backend.app"


def test_main_routes_render(client):
    assert client.get("/").status_code == 200
    assert client.get("/register").status_code == 200
    assert client.get("/marketplace").status_code == 200
    assert client.get("/notifications").status_code == 200

    login_student(client)
    assert client.get("/seller_requests").status_code == 200


def test_student_login_redirects_to_homepage(client):
    response = client.post(
        "/login",
        data={"login_id": "student1", "password": "password123"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/homepage")


def test_admin_login_redirects_to_dashboard(client):
    response = client.post(
        "/login",
        data={"login_id": "admin", "password": "admin123"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")


def test_seller_dashboard_route_loads_for_logged_in_user(client):
    login_student(client)

    response = client.get("/seller/dashboard")

    assert response.status_code == 200
    assert b"Seller Dashboard" in response.data
    assert b"Keyboard" in response.data
    assert b"Monitor" not in response.data


def test_seller_dashboard_add_product_works(client, app):
    login_student(client)

    response = client.post(
        "/seller/dashboard/add",
        data={
            "title": "Notebook",
            "description": "Unused lined notebook",
            "price": "4.50",
            "category": "Books",
        },
    )
    products = read_products(app)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/seller/dashboard")
    assert any(
        product["title"] == "Notebook"
        and product["seller"] == "student1"
        and product["status"] == "Available"
        and product["category"] == "Books"
        for product in products
    )


def test_seller_dashboard_edit_product_works(client, app):
    login_student(client)

    response = client.post(
        "/seller/dashboard/edit/1",
        data={
            "title": "Mechanical Keyboard",
            "description": "Blue switches",
            "price": "35",
            "status": "Sold",
            "category": "Electronics",
        },
    )
    products = read_products(app)
    product = next(item for item in products if item["id"] == 1)

    assert response.status_code == 302
    assert product["title"] == "Mechanical Keyboard"
    assert product["name"] == "Mechanical Keyboard"
    assert product["description"] == "Blue switches"
    assert product["price"] == 35.0
    assert product["status"] == "Sold"
    assert product["category"] == "Electronics"


def test_seller_dashboard_delete_product_works(client, app):
    login_student(client)

    response = client.post("/seller/dashboard/delete/1")
    products = read_products(app)

    assert response.status_code == 302
    assert all(product["id"] != 1 for product in products)
    assert any(product["id"] == 3 for product in products)


def test_seller_dashboard_filtering_works(client):
    login_student(client)

    response = client.get("/seller/dashboard?status=sold")

    assert response.status_code == 200
    assert b"Mouse" in response.data
    assert b"Keyboard" not in response.data
    assert b"Monitor" not in response.data


def test_marketplace_category_filters_show_matching_products(client):
    electronics_response = client.get("/marketplace?category=Electronics")
    books_response = client.get("/marketplace?category=Books")
    food_response = client.get("/marketplace?category=Food")

    assert electronics_response.status_code == 200
    assert b"Keyboard" in electronics_response.data
    assert b"Math Textbook" not in electronics_response.data

    assert books_response.status_code == 200
    assert b"Math Textbook" in books_response.data
    assert b"Keyboard" not in books_response.data

    assert food_response.status_code == 200
    assert b"Snack Pack" in food_response.data
    assert b"Keyboard" not in food_response.data


def test_marketplace_search_and_category_filter_work_together(client):
    search_response = client.get("/marketplace?search=keyboard")
    matching_response = client.get(
        "/marketplace?search=keyboard&category=electronics"
    )
    empty_response = client.get("/marketplace?search=keyboard&category=Books")

    assert search_response.status_code == 200
    assert b"Keyboard" in search_response.data

    assert matching_response.status_code == 200
    assert b"Keyboard" in matching_response.data

    assert empty_response.status_code == 200
    assert b"No products match this search or category." in empty_response.data
    assert b"Keyboard" not in empty_response.data


def test_wishlist_add_remove_still_works(client, app):
    login_user(client, "student2")

    add_response = client.post("/wishlist/add/1")
    wishlist_response = client.get("/wishlist")
    wishlists = read_wishlists(app)

    assert add_response.status_code == 302
    assert wishlists["3"] == [1]
    assert b"Keyboard" in wishlist_response.data

    remove_response = client.post("/wishlist/remove/1")
    wishlists = read_wishlists(app)
    wishlist_response = client.get("/wishlist")

    assert remove_response.status_code == 302
    assert wishlists["3"] == []
    assert b"Keyboard" not in wishlist_response.data


def test_mysql_wishlist_add_remove_does_not_write_json(monkeypatch, app):
    monkeypatch.setenv("USE_MYSQL_WISHLISTS", "true")
    calls = []
    original_wishlists = read_wishlists(app)

    monkeypatch.setattr(
        marketplace_service,
        "get_product_by_id",
        lambda product_id: {"id": product_id, "title": "Keyboard"},
    )
    monkeypatch.setattr(
        marketplace_service,
        "execute_mysql_query",
        lambda query, params=None, **kwargs: calls.append((query, params)),
    )

    user = {"user_id": 3, "username": "student2"}

    with app.app_context():
        assert marketplace_service.add_to_wishlist(1, user) is True
        assert marketplace_service.remove_from_wishlist(1, user) is True

    assert "INSERT INTO wishlists" in calls[0][0]
    assert calls[0][1] == (3, 1)
    assert "DELETE FROM wishlists" in calls[1][0]
    assert calls[1][1] == (3, 1)
    assert read_wishlists(app) == original_wishlists


def test_wishlist_migration_reports_missing_products(monkeypatch):
    monkeypatch.setattr(
        migrate_wishlists,
        "load_source_records",
        lambda: {"3": [1, 99, 1], "999": [1]},
    )
    monkeypatch.setattr(
        migrate_wishlists,
        "load_json_rows",
        lambda filename: (
            [{"id": 3, "username": "student2"}]
            if filename == "users.json"
            else [{"id": 1, "title": "Keyboard"}]
        ),
    )

    summary, missing_users, missing_products = migrate_wishlists.migrate(
        dry_run=True
    )

    assert summary["source"] == 4
    assert summary["missing_users"] == 1
    assert summary["missing_products"] == 1
    assert missing_users == [999]
    assert missing_products == [99]


def test_seller_chat_blocks_non_seller(client):
    login_user(client, "student2")

    response = client.get("/seller/chat/1/student3")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/seller/chats")


def test_mysql_message_send_does_not_write_json(monkeypatch, app):
    monkeypatch.setenv("USE_MYSQL_MESSAGES", "true")
    calls = []
    original_messages = read_messages(app)

    monkeypatch.setattr(
        marketplace_service,
        "execute_mysql_query",
        lambda query, params=None, **kwargs: [],
    )

    from backend.services import chat_service

    def fake_execute(query, params=None, fetch=False, **kwargs):
        if fetch:
            return [{"id": 1}] if "FROM users" in query else []
        calls.append((query, params))
        return 1

    monkeypatch.setattr(chat_service, "execute_mysql_query", fake_execute)

    with app.app_context():
        message = chat_service.send_chat_message(
            1,
            {"user_id": 3, "username": "student2"},
            "student1",
            "Is this available?",
        )

    assert message["sender"] == "student2"
    assert message["receiver"] == "student1"
    assert "INSERT INTO messages" in calls[0][0]
    assert calls[0][1][0] == 1
    assert calls[0][1][1] == 3
    assert calls[0][1][2] == 1
    assert read_messages(app) == original_messages


def test_message_migration_reports_unresolved_participants(monkeypatch):
    monkeypatch.setattr(
        migrate_messages,
        "load_source_records",
        lambda: [
            {
                "product_id": 1,
                "sender": "missing_sender",
                "receiver": "missing_receiver",
                "text": "Hello",
                "timestamp": "2026-07-16 10:30:00",
            }
        ],
    )
    monkeypatch.setattr(
        migrate_messages,
        "load_json_rows",
        lambda filename: (
            [{"id": 1, "title": "Keyboard"}]
            if filename == "products.json"
            else [{"id": 2, "username": "student2"}]
        ),
    )

    summary, senders, receivers, products = migrate_messages.migrate(dry_run=True)

    assert summary["source"] == 1
    assert summary["unresolved_senders"] == 1
    assert summary["unresolved_receivers"] == 1
    assert senders == ["missing_sender"]
    assert receivers == ["missing_receiver"]
    assert products == []


def test_duplicate_product_request_is_blocked(client, app):
    login_user(client, "student2")

    first_response = client.post("/request_buy/1")
    second_response = client.post("/request_buy/1")
    requests = read_requests(app)

    assert first_response.status_code == 302
    assert second_response.status_code == 302
    assert len([
        request for request in requests
        if request["product_id"] == 1 and request["buyer"] == "student2"
    ]) == 1


def test_requested_product_button_is_disabled_for_buyer(client):
    login_user(client, "student2")
    client.post("/request_buy/1")

    response = client.get("/marketplace")

    assert response.status_code == 200
    assert b"Request Pending" in response.data


def test_rejected_request_allows_buyer_to_request_again(client, app):
    login_user(client, "student2")
    client.post("/request_buy/1")

    login_user(client, "student1")
    client.post(
        "/reject_request/1",
        data={"rejection_reason": "Not available for pickup."},
    )

    login_user(client, "student2")
    client.post("/request_buy/1")
    requests = read_requests(app)

    assert len([
        request for request in requests
        if request["product_id"] == 1 and request["buyer"] == "student2"
    ]) == 2
    assert requests[0]["status"] == "Rejected"
    assert requests[1]["status"] == "Pending"


def test_non_owner_cannot_view_other_seller_requests(client):
    login_user(client, "student2")
    client.post("/request_buy/1")

    response = client.get("/seller_requests")

    assert response.status_code == 200
    assert b"Keyboard" not in response.data
    assert b"approve-btn" not in response.data
    assert b"reject-btn" not in response.data


def test_non_owner_cannot_accept_request_directly(client, app):
    login_user(client, "student2")
    client.post("/request_buy/1")

    response = client.post("/accept_request/1")
    requests = read_requests(app)
    products = read_products(app)
    product = next(item for item in products if item["id"] == 1)

    assert response.status_code == 403
    assert b"Access Denied" in response.data
    assert requests[0]["status"] == "Pending"
    assert product["status"] == "Available"


def test_owner_accept_marks_product_sold_and_blocks_new_requests(client, app):
    login_user(client, "student2")
    client.post("/request_buy/1")

    login_user(client, "student1")
    response = client.post("/accept_request/1")

    login_user(client, "student3")
    duplicate_response = client.post("/request_buy/1")
    marketplace_response = client.get("/marketplace")
    requests = read_requests(app)
    products = read_products(app)
    product = next(item for item in products if item["id"] == 1)

    assert response.status_code == 302
    assert duplicate_response.status_code == 302
    assert product["status"] == "Sold"
    assert len([request for request in requests if request["product_id"] == 1]) == 1
    assert b"Sold" in marketplace_response.data


def test_sold_item_cannot_be_requested_directly(client, app):
    login_user(client, "student3")

    response = client.post("/request_buy/4")
    requests = read_requests(app)

    assert response.status_code == 302
    assert requests == []


def test_non_owner_cannot_edit_or_delete_seller_dashboard_listing(client, app):
    login_user(client, "student2")

    edit_response = client.post(
        "/seller/dashboard/edit/1",
        data={
            "title": "Hijacked Keyboard",
            "description": "Nope",
            "price": "1",
            "status": "Sold",
        },
    )
    delete_response = client.post("/seller/dashboard/delete/1")
    products = read_products(app)
    product = next(item for item in products if item["id"] == 1)

    assert edit_response.status_code == 403
    assert delete_response.status_code == 403
    assert product["title"] == "Keyboard"
    assert any(item["id"] == 1 for item in products)


def test_legacy_user_without_username_can_login_using_email(client):
    response = client.post(
        "/login",
        data={"login_id": "25044459@myrp.edu.sg", "password": "password123"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/homepage")


def test_legacy_user_without_username_can_login_using_student_id(client):
    response = client.post(
        "/login",
        data={"login_id": "25044459", "password": "password123"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/homepage")


def test_registering_new_account_works(client, app):
    response = client.post(
        "/register",
        data={
            "name": "New Student",
            "username": "newstudent",
            "email": "newstudent@myrp.edu.sg",
            "student_id": "S99999",
            "school": "School of Infocomm",
            "password": "password123",
        },
    )

    users = read_users(app)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert any(user["username"] == "newstudent" for user in users)


def test_duplicate_email_is_blocked(client):
    response = client.post(
        "/register",
        data={
            "name": "Other Student",
            "username": "otherstudent",
            "email": " STUDENT1@MYRP.EDU.SG ",
            "student_id": "S54321",
            "school": "School of Infocomm",
            "password": "password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Username, email, or student ID already exists." in response.data


def test_duplicate_username_is_blocked(client):
    response = client.post(
        "/register",
        data={
            "name": "Other Student",
            "username": " STUDENT1 ",
            "email": "otherstudent@myrp.edu.sg",
            "student_id": "S54321",
            "school": "School of Infocomm",
            "password": "password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Username, email, or student ID already exists." in response.data


def test_duplicate_student_id_is_blocked(client):
    response = client.post(
        "/register",
        data={
            "name": "Other Student",
            "username": "otherstudent",
            "email": "otherstudent@myrp.edu.sg",
            "student_id": " S12345 ",
            "school": "School of Infocomm",
            "password": "password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Username, email, or student ID already exists." in response.data


def test_blank_registration_fields_are_rejected_clearly(client):
    response = client.post(
        "/register",
        data={
            "name": "",
            "username": "blankstudent",
            "email": "blankstudent@myrp.edu.sg",
            "student_id": "S77777",
            "school": "School of Infocomm",
            "password": "password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Name, username, email, student ID, and password are required." in response.data


def test_invalid_login_shows_error_page(client):
    response = client.post(
        "/login",
        data={"login_id": "student1", "password": "wrong"},
    )

    assert response.status_code == 200
    assert b"Login Failed" in response.data or b"Invalid" in response.data


def test_wrong_password_logs_clear_reason(client, app):
    response = client.post(
        "/login",
        data={"login_id": "student1", "password": "wrong"},
    )

    failed_logs_path = app.config["DATA_DIR"] + "/failed_logins.json"
    with open(failed_logs_path, "r", encoding="utf-8") as file:
        logs = json.load(file)

    assert response.status_code == 200
    assert logs[-1]["reason"] == "Wrong password"


def test_unknown_account_logs_clear_reason(client, app):
    client.post(
        "/login",
        data={"login_id": "missing-user", "password": "password123"},
    )

    failed_logs_path = app.config["DATA_DIR"] + "/failed_logins.json"
    with open(failed_logs_path, "r", encoding="utf-8") as file:
        logs = json.load(file)

    assert logs[-1]["reason"] == "Account not found"


def test_forgot_password_logs_reset_request(client, app):
    response = client.post(
        "/forgot-password",
        data={"login_id": "student1"},
    )

    failed_logs_path = app.config["DATA_DIR"] + "/failed_logins.json"
    with open(failed_logs_path, "r", encoding="utf-8") as file:
        logs = json.load(file)

    assert response.status_code == 302
    assert logs[-1]["reason"] == "Password reset requested"

    notifications_path = app.config["DATA_DIR"] + "/notifications.json"
    with open(notifications_path, "r", encoding="utf-8") as file:
        notifications = json.load(file)

    assert notifications[-1]["status"] == "Info"


def test_notifications_can_use_mysql_when_enabled(monkeypatch):
    calls = []

    def fake_enabled():
        return True

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append({
            "query": " ".join(query.split()),
            "params": params,
            "fetch": fetch,
            "dictionary": dictionary,
        })
        if fetch:
            return [{
                "id": 7,
                "title": "MySQL notification",
                "message": "Stored in MySQL",
                "status": "Info",
                "created_at": datetime(2026, 7, 15, 12, 30, 0),
            }]
        return 7

    monkeypatch.setattr(
        notification_service,
        "mysql_notifications_enabled",
        fake_enabled,
    )
    monkeypatch.setattr(notification_service, "execute_mysql_query", fake_execute)

    notification_service.add_notification("Created", "From test", "Pending")
    notifications = notification_service.get_notifications()

    assert calls[0]["query"].startswith("INSERT INTO notifications")
    assert calls[0]["params"] == ("Created", "From test", "Pending")
    assert calls[1]["query"].startswith("SELECT id, title, message, status")
    assert calls[1]["fetch"] is True
    assert notifications == [{
        "id": 7,
        "title": "MySQL notification",
        "message": "Stored in MySQL",
        "status": "Info",
        "time": "2026-07-15 12:30:00",
    }]


def test_report_submission_uses_json_fallback(client, app):
    login_user(client, "student2")

    response = client.post(
        "/submit_report/1",
        data={
            "reason": "Spam",
            "comments": "Looks suspicious.",
        },
    )

    reports_path = app.config["DATA_DIR"] + "/reports.json"
    with open(reports_path, "r", encoding="utf-8") as file:
        reports = json.load(file)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/product/1")
    assert reports[-1]["product_id"] == 1
    assert reports[-1]["reported_by"] == "student2"
    assert reports[-1]["reason"] == "Spam"
    assert reports[-1]["status"] == "Pending"


def test_reports_can_use_mysql_when_enabled(monkeypatch):
    calls = []

    def fake_enabled():
        return True

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append({
            "query": " ".join(query.split()),
            "params": params,
            "fetch": fetch,
            "dictionary": dictionary,
        })
        if fetch:
            return [{
                "id": 12,
                "product_id": 3,
                "product_title": "Monitor",
                "seller_identifier": "student1",
                "reported_by": "student2",
                "reason": "Spam",
                "comments": "Looks suspicious.",
                "status": "Pending",
                "created_at": datetime(2026, 7, 15, 13, 45, 0),
            }]
        return 12

    monkeypatch.setattr(report_service, "mysql_reports_enabled", fake_enabled)
    monkeypatch.setattr(report_service, "execute_mysql_query", fake_execute)

    created = report_service.submit_report(
        {"id": 3, "title": "Monitor", "seller": "student1"},
        {"username": "student2"},
        "Spam",
        "Looks suspicious.",
    )
    reports = report_service.get_reports()

    assert created is True
    assert calls[0]["query"].startswith("INSERT INTO reports")
    assert calls[0]["params"] == (
        3,
        "Monitor",
        "student1",
        "student2",
        "Spam",
        "Looks suspicious.",
        "Pending",
    )
    assert calls[1]["query"].startswith("SELECT id, product_id")
    assert calls[1]["fetch"] is True
    assert reports == [{
        "id": 12,
        "product_id": 3,
        "product_title": "Monitor",
        "seller": "student1",
        "reported_by": "student2",
        "reason": "Spam",
        "comments": "Looks suspicious.",
        "status": "Pending",
        "reported_at": "2026-07-15 13:45:00",
    }]


def test_mysql_user_login_verifies_hashed_password(monkeypatch):
    password_hash = auth_service.generate_password_hash("password123")

    def fake_enabled():
        return True

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        assert fetch is True
        return [{
            "id": 3,
            "name": "Student Two",
            "username": "student2",
            "email": "student2@myrp.edu.sg",
            "student_id": "S23456",
            "school": "School of Infocomm",
            "password_hash": password_hash,
            "role": "student",
            "is_blocked": False,
            "created_at": datetime(2026, 7, 15, 9, 0, 0),
            "last_login_at": None,
            "status_updated_at": None,
        }]

    monkeypatch.setattr(auth_service, "mysql_users_enabled", fake_enabled)
    monkeypatch.setattr(auth_service, "execute_mysql_query", fake_execute)

    user = auth_service.find_matching_user("student2", "password123")

    assert user["id"] == 3
    assert user["username"] == "student2"
    assert "password" not in user


def test_mysql_registration_hashes_password(monkeypatch):
    calls = []

    def fake_enabled():
        return True

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append({
            "query": " ".join(query.split()),
            "params": params,
            "fetch": fetch,
        })
        if fetch:
            return []
        return 9

    monkeypatch.setattr(auth_service, "mysql_users_enabled", fake_enabled)
    monkeypatch.setattr(auth_service, "execute_mysql_query", fake_execute)

    success, title, message = auth_service.register_user({
        "name": "New Student",
        "username": "newstudent",
        "email": "newstudent@myrp.edu.sg",
        "student_id": "S99999",
        "school": "School of Infocomm",
        "password": "password123",
    })

    assert success is True
    assert title is None
    assert message is None
    assert calls[0]["query"].startswith("SELECT id FROM users")
    assert calls[1]["query"].startswith("INSERT INTO users")
    inserted_password = calls[1]["params"][5]
    assert inserted_password != "password123"
    assert auth_service.check_password_hash(inserted_password, "password123")


def test_mysql_login_logs_write_attempts(monkeypatch):
    calls = []

    def fake_logs_enabled():
        return True

    def fake_users_enabled():
        return False

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append({
            "query": " ".join(query.split()),
            "params": params,
            "fetch": fetch,
        })
        return []

    monkeypatch.setattr(auth_service, "mysql_login_logs_enabled", fake_logs_enabled)
    monkeypatch.setattr(auth_service, "mysql_users_enabled", fake_users_enabled)
    monkeypatch.setattr(auth_service, "execute_mysql_query", fake_execute)

    auth_service.log_success({"id": 3, "username": "student2"})
    auth_service.log_failed("missing-user", "Account not found")

    assert calls[0]["query"].startswith("INSERT INTO login_attempts")
    assert calls[0]["params"] == (3, "student2", True, None)
    assert calls[-1]["query"].startswith("INSERT INTO login_attempts")
    assert calls[-1]["params"] == (None, "missing-user", False, "Account not found")


def test_products_can_load_from_mysql(monkeypatch):
    def fake_enabled():
        return True

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        assert fetch is True
        return [{
            "id": 1,
            "seller_id": 3,
            "seller_identifier": "student1",
            "legacy_seller_name": "Jane Smith",
            "seller_name": "Student One",
            "seller_username": "student1",
            "title": "Keyboard",
            "description": "Compact keyboard",
            "price": 25,
            "image_url": "",
            "status": "Available",
            "category_name": "Electronics",
        }]

    monkeypatch.setattr(
        seller_dashboard_service,
        "mysql_products_enabled",
        fake_enabled,
    )
    monkeypatch.setattr(seller_dashboard_service, "execute_mysql_query", fake_execute)

    products = seller_dashboard_service.load_products()

    assert products == [{
        "id": 1,
        "seller_id": 3,
        "seller": "Jane Smith",
        "seller_identifier": "student1",
        "legacy_seller_name": "Jane Smith",
        "title": "Keyboard",
        "name": "Keyboard",
        "description": "Compact keyboard",
        "price": 25,
        "image_url": "",
        "status": "Available",
        "category": "Electronics",
    }]


def test_product_creation_uses_mysql(monkeypatch):
    calls = []

    def fake_enabled():
        return True

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append({
            "query": " ".join(query.split()),
            "params": params,
            "fetch": fetch,
        })
        if fetch:
            return [{"id": 4}]
        return 4

    monkeypatch.setattr(
        seller_dashboard_service,
        "mysql_products_enabled",
        fake_enabled,
    )
    monkeypatch.setattr(seller_dashboard_service, "execute_mysql_query", fake_execute)

    success, message = seller_dashboard_service.add_product(
        {
            "title": "Notebook",
            "description": "Unused lined notebook",
            "price": "4.50",
            "category": "Books",
        },
        {"user_id": 3, "username": "student1"},
    )

    assert success is True
    assert message is None
    assert calls[0]["query"].startswith("SELECT p.id")
    assert calls[1]["query"].startswith("INSERT INTO categories")
    assert calls[2]["query"].startswith("SELECT id FROM categories")
    assert calls[3]["query"].startswith("INSERT INTO products")
    assert calls[3]["params"] == (
        3,
        "student1",
        4,
        "Notebook",
        "Unused lined notebook",
        4.5,
        "Available",
    )


def test_mysql_product_ownership_uses_seller_id_not_legacy_display():
    product = {
        "id": 1,
        "seller_id": 3,
        "seller": "Jane Smith",
        "legacy_seller_name": "Jane Smith",
    }

    assert seller_dashboard_service.product_belongs_to_seller(
        product,
        {"user_id": 3, "username": "student1"},
    )
    assert not seller_dashboard_service.product_belongs_to_seller(
        product,
        {"user_id": 9, "username": "Jane Smith"},
    )


def test_product_migration_maps_legacy_sellers_to_configured_fallback(monkeypatch):
    monkeypatch.setenv("LEGACY_PRODUCT_OWNER_USERNAME", "DEMO")
    monkeypatch.setattr(
        migrate_products,
        "load_source_records",
        lambda: [
            {
                "id": 1,
                "title": "Matched Book",
                "description": "Matched seller",
                "price": 5,
                "seller": "student1",
                "category": "Books",
                "status": "Available",
            },
            {
                "id": 2,
                "title": "Legacy Laptop",
                "description": "Legacy seller",
                "price": 50,
                "seller": "Jane Smith",
                "category": "Electronics",
                "status": "Available",
            },
        ],
    )
    monkeypatch.setattr(
        migrate_products,
        "user_rows_from_json",
        lambda: [
            {
                "id": 1,
                "username": "admin",
                "name": "Admin",
                "email": "admin@rp.edu.sg",
                "student_id": "admin",
                "role": "admin",
            },
            {
                "id": 2,
                "username": "demo",
                "name": "Demo User",
                "email": "demo@myrp.edu.sg",
                "student_id": "S22222",
                "role": "student",
            },
            {
                "id": 3,
                "username": "student1",
                "name": "Student One",
                "email": "student1@myrp.edu.sg",
                "student_id": "S11111",
                "role": "student",
            },
        ],
    )

    summary, mappings = migrate_products.migrate(dry_run=True)

    assert summary["source"] == 2
    assert summary["normal_matches"] == 1
    assert summary["fallback_mapped"] == 1
    assert summary["invalid"] == 0
    assert mappings == {"Jane Smith": "demo"}


def test_product_migration_stops_when_fallback_config_missing(monkeypatch):
    monkeypatch.delenv("LEGACY_PRODUCT_OWNER_USERNAME", raising=False)
    monkeypatch.setattr(migrate_products, "load_source_records", lambda: [])
    monkeypatch.setattr(
        migrate_products,
        "user_rows_from_json",
        lambda: [
            {
                "id": 2,
                "username": "jason",
                "name": "Jason Tan",
                "email": "25044459@myrp.edu.sg",
                "student_id": "25044459",
                "role": "student",
            }
        ],
    )

    with pytest.raises(ValueError) as error:
        migrate_products.migrate(dry_run=True)

    assert "LEGACY_PRODUCT_OWNER_USERNAME is required" in str(error.value)
    assert "jason" in str(error.value)


def test_product_migration_rejects_admin_fallback(monkeypatch):
    monkeypatch.setenv("LEGACY_PRODUCT_OWNER_USERNAME", "admin")
    monkeypatch.setattr(migrate_products, "load_source_records", lambda: [])
    monkeypatch.setattr(
        migrate_products,
        "user_rows_from_json",
        lambda: [
            {
                "id": 1,
                "username": "admin",
                "name": "Admin",
                "email": "admin@rp.edu.sg",
                "student_id": "admin",
                "role": "admin",
            },
            {
                "id": 2,
                "username": "jason",
                "name": "Jason Tan",
                "email": "25044459@myrp.edu.sg",
                "student_id": "25044459",
                "role": "student",
            },
        ],
    )

    with pytest.raises(ValueError) as error:
        migrate_products.migrate(dry_run=True)

    assert "admin" in str(error.value)
    assert "non-admin user" in str(error.value)
    assert "jason" in str(error.value)


def test_product_request_filter_empty_state(client):
    login_student(client)

    response = client.get("/seller_requests?status=pending")

    assert response.status_code == 200
    assert b"No pending product requests." in response.data


def test_product_request_route_still_creates_request(client, app):
    login_user(client, "student2")

    response = client.post("/request_buy/1")

    requests_path = app.config["DATA_DIR"] + "/requests.json"
    notifications_path = app.config["DATA_DIR"] + "/notifications.json"

    with open(requests_path, "r", encoding="utf-8") as file:
        requests = json.load(file)

    with open(notifications_path, "r", encoding="utf-8") as file:
        notifications = json.load(file)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/marketplace")
    assert requests[-1]["status"] == "Pending"
    assert requests[-1]["buyer"] == "student2"
    assert notifications[-1]["status"] == "Pending"


def test_mysql_request_row_keeps_template_shape():
    row = {
        "id": 7,
        "product_id": 3,
        "product_title": "Monitor",
        "buyer_id": 4,
        "buyer_identifier": "legacy_buyer",
        "buyer_username": "student4",
        "buyer_name": "Student Four",
        "seller_id": 9,
        "seller_identifier": "seller9",
        "legacy_seller_name": None,
        "seller_username": "seller_user",
        "seller_name": "Seller User",
        "status": "Pending",
        "rejection_reason": None,
        "requested_at": datetime(2026, 7, 16, 10, 30, 0),
        "reviewed_at": None,
    }

    request_item = marketplace_service.request_from_mysql(row)

    assert request_item["id"] == 7
    assert request_item["product_title"] == "Monitor"
    assert request_item["buyer"] == "student4"
    assert request_item["buyer_id"] == 4
    assert request_item["seller"] == "seller_user"
    assert request_item["seller_id"] == 9
    assert request_item["time"] == "2026-07-16 10:30:00"


def test_mysql_request_submission_does_not_write_requests_json(monkeypatch, app):
    monkeypatch.setenv("USE_MYSQL_REQUESTS", "true")
    inserted = []
    notifications = []
    original_requests = read_requests(app)

    monkeypatch.setattr(marketplace_service, "get_requests", lambda: [])
    monkeypatch.setattr(
        marketplace_service,
        "execute_mysql_query",
        lambda query, params=None, **kwargs: inserted.append((query, params)),
    )
    monkeypatch.setattr(
        marketplace_service,
        "add_notification",
        lambda title, message, status="Info": notifications.append(
            {"title": title, "message": message, "status": status}
        ),
    )

    with app.app_context():
        success, message = marketplace_service.request_buy(
            1,
            {
                "user_id": 3,
                "username": "student2",
                "name": "Student Two",
                "email": "student2@myrp.edu.sg",
                "student_id": "S23456",
            },
        )

    assert success is True
    assert message is None
    assert "INSERT INTO purchase_requests" in inserted[0][0]
    assert inserted[0][1][0] == 1
    assert inserted[0][1][1] == 3
    assert inserted[0][1][2] == "student2"
    assert notifications[-1]["status"] == "Pending"
    assert read_requests(app) == original_requests


def test_purchase_request_migration_reports_unresolved_buyer(monkeypatch):
    monkeypatch.setattr(
        migrate_purchase_requests,
        "load_source_records",
        lambda: [
            {
                "id": 1,
                "product_id": 1,
                "buyer": "missing_buyer",
                "status": "Pending",
                "time": "2026-07-16 10:30:00",
            }
        ],
    )
    monkeypatch.setattr(
        migrate_purchase_requests,
        "load_json_rows",
        lambda filename: (
            [{"id": 1, "title": "Keyboard"}]
            if filename == "products.json"
            else [{"id": 2, "username": "student2"}]
        ),
    )

    summary, unresolved_buyers, missing_products = (
        migrate_purchase_requests.migrate(dry_run=True)
    )

    assert summary["source"] == 1
    assert summary["unresolved_buyers"] == 1
    assert unresolved_buyers == ["missing_buyer"]
    assert missing_products == []
