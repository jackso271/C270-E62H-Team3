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
        ],
        "products.json": [
            {
                "id": 1,
                "title": "Keyboard",
                "price": 25,
                "seller": "seller1",
                "status": "Available",
            }
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
