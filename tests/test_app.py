import json

import pytest

from backend.app import create_app


@pytest.fixture()
def app(tmp_path):
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
                "description": "Compact keyboard",
            },
            {
                "id": 2,
                "title": "Mouse",
                "name": "Mouse",
                "price": 15,
                "seller": "student1",
                "status": "Sold",
                "description": "Wireless mouse",
            },
            {
                "id": 3,
                "title": "Monitor",
                "name": "Monitor",
                "price": 80,
                "seller": "otherstudent",
                "status": "Available",
                "description": "24 inch monitor",
            },
        ],
        "requests.json": [],
        "notifications.json": [],
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


def login_student(client):
    return client.post(
        "/login",
        data={"login_id": "student1", "password": "password123"},
    )


def test_application_startup(app):
    assert app is not None
    assert app.name == "backend.app"


def test_main_routes_render(client):
    assert client.get("/").status_code == 200
    assert client.get("/register").status_code == 200
    assert client.get("/marketplace").status_code == 200
    assert client.get("/seller_requests").status_code == 200
    assert client.get("/notifications").status_code == 200


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
        },
    )
    products = read_products(app)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/seller/dashboard")
    assert any(
        product["title"] == "Notebook"
        and product["seller"] == "student1"
        and product["status"] == "Available"
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


def test_product_request_filter_empty_state(client):
    response = client.get("/seller_requests?status=pending")

    assert response.status_code == 200
    assert b"No pending product requests." in response.data


def test_product_request_route_still_creates_request(client, app):
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
    assert notifications[-1]["status"] == "Pending"
