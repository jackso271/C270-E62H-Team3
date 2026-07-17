from datetime import datetime
from pathlib import Path
import logging
import time

import pyotp
import pytest
from werkzeug.security import generate_password_hash

from backend.db import MySQLDatabaseError
from backend.app import create_app
from backend.routes import auth_routes
from backend.services import auth_service
from backend.services import chat_service
from backend.services import marketplace_service
from backend.services import notification_service
from backend.services import report_service
from backend.services import seller_dashboard_service
from database.migrations import migrate_messages
from database.migrations import migrate_purchase_requests
from database.migrations import migrate_wishlists


def test_application_startup_uses_mysql_admin_setup(monkeypatch):
    calls = []

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append((query, params, fetch))
        if fetch:
            return []
        return 1

    monkeypatch.setattr(auth_service, "execute_mysql_query", fake_execute)

    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})

    assert app.name == "backend.app"
    assert any("INSERT INTO users" in query for query, _, _ in calls)


def test_notifications_use_mysql(monkeypatch):
    calls = []

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append((query, params, fetch))
        if fetch:
            return [
                {
                    "id": 1,
                    "title": "Request",
                    "message": "Submitted",
                    "status": "Pending",
                    "created_at": datetime(2026, 7, 16, 12, 0, 0),
                }
            ]
        return 1

    monkeypatch.setattr(notification_service, "execute_mysql_query", fake_execute)

    notification_service.add_notification("Request", "Submitted", "Pending")
    rows = notification_service.get_notifications()

    assert calls[0][1] == ("Request", "Submitted", "Pending")
    assert rows[0]["time"] == "2026-07-16 12:00:00"


def test_report_submission_uses_mysql(monkeypatch):
    captured = []

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        captured.append(params)
        return [] if fetch else 1

    monkeypatch.setattr(report_service, "execute_mysql_query", fake_execute)

    ok = report_service.submit_report(
        {"id": 7, "title": "Keyboard", "seller": "student1"},
        {"username": "student2"},
        "Wrong category",
        "Looks suspicious",
    )

    assert ok is True
    assert captured[0] == (
        7,
        "Keyboard",
        "student1",
        "student2",
        "Wrong category",
        "Looks suspicious",
        "Pending",
    )


def test_user_login_verifies_hashed_mysql_password(monkeypatch):
    password_hash = generate_password_hash("password123")

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        assert fetch is True
        return [
            {
                "id": 2,
                "name": "Student One",
                "username": "student1",
                "email": "student1@myrp.edu.sg",
                "student_id": "S12345",
                "school": "SOI",
                "password_hash": password_hash,
                "role": "student",
                "is_blocked": False,
                "created_at": datetime(2026, 7, 1, 9, 0, 0),
                "last_login_at": None,
                "status_updated_at": None,
            }
        ]

    monkeypatch.setattr(auth_service, "execute_mysql_query", fake_execute)

    user = auth_service.find_matching_user("student1", "password123")

    assert user["username"] == "student1"
    assert "password" not in user


def test_registration_hashes_password_before_mysql_insert(monkeypatch):
    calls = []

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append((query, params, fetch))
        return [] if fetch else 42

    monkeypatch.setattr(auth_service, "execute_mysql_query", fake_execute)

    ok, title, message = auth_service.register_user(
        {
            "name": "New Student",
            "username": "newstudent",
            "email": "newstudent@myrp.edu.sg",
            "student_id": "S98765",
            "password": "plain-password",
            "school": "SOI",
        }
    )

    insert_params = calls[1][1]
    assert (ok, title, message) == (True, None, None)
    assert insert_params[5] != "plain-password"
    assert insert_params[5].startswith(("scrypt:", "pbkdf2:"))


def test_setup_2fa_redirects_when_unauthenticated(monkeypatch):
    monkeypatch.setattr("backend.app.create_admin", lambda: None)
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})

    response = app.test_client().get("/setup-2fa")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_setup_2fa_renders_for_pending_user_without_existing_2fa(monkeypatch):
    monkeypatch.setattr("backend.app.create_admin", lambda: None)
    monkeypatch.setattr(
        auth_routes,
        "find_user_by_id",
        lambda user_id: {
            "id": user_id,
            "name": "Student One",
            "username": "student1",
            "email": "student1@myrp.edu.sg",
            "student_id": "S12345",
            "role": "student",
            "two_factor_enabled": False,
            "two_factor_secret": None,
        },
    )
    monkeypatch.setattr(
        auth_routes,
        "generate_2fa_secret",
        lambda: "JBSWY3DPEHPK3PXP",
    )
    monkeypatch.setattr(
        auth_routes,
        "generate_2fa_qr_code",
        lambda username, secret: "data:image/png;base64,test-qr",
    )
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
    client = app.test_client()

    with client.session_transaction() as flask_session:
        flask_session["pending_2fa_user_id"] = 2

    response = client.get("/setup-2fa")

    assert response.status_code == 200
    assert b"Set Up 2FA" in response.data
    assert b"data:image/png;base64,test-qr" in response.data


def test_setup_2fa_generates_secret_when_missing_pending_secret(monkeypatch):
    monkeypatch.setattr("backend.app.create_admin", lambda: None)
    monkeypatch.setattr(
        auth_routes,
        "find_user_by_id",
        lambda user_id: {
            "id": user_id,
            "username": "student1",
            "two_factor_enabled": False,
            "two_factor_secret": None,
        },
    )
    monkeypatch.setattr(
        auth_routes,
        "generate_2fa_secret",
        lambda: "JBSWY3DPEHPK3PXP",
    )
    monkeypatch.setattr(
        auth_routes,
        "generate_2fa_qr_code",
        lambda username, secret: "data:image/png;base64,test-qr",
    )
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
    client = app.test_client()

    with client.session_transaction() as flask_session:
        flask_session["pending_2fa_user_id"] = 2

    response = client.get("/setup-2fa")

    assert response.status_code == 200
    with client.session_transaction() as flask_session:
        assert flask_session["pending_2fa_secret"] == "JBSWY3DPEHPK3PXP"


def test_setup_2fa_redirects_to_verify_for_existing_2fa(monkeypatch):
    monkeypatch.setattr("backend.app.create_admin", lambda: None)
    monkeypatch.setattr(
        auth_routes,
        "find_user_by_id",
        lambda user_id: {
            "id": user_id,
            "username": "student1",
            "two_factor_enabled": True,
            "two_factor_secret": "JBSWY3DPEHPK3PXP",
        },
    )
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
    client = app.test_client()

    with client.session_transaction() as flask_session:
        flask_session["pending_2fa_user_id"] = 2

    response = client.get("/setup-2fa")

    assert response.status_code == 302
    assert response.headers["Location"] == "/verify-2fa"


def test_setup_2fa_valid_code_persists_and_completes_login(monkeypatch):
    saved = {}
    secret = pyotp.random_base32()
    code = pyotp.TOTP(secret).now()

    monkeypatch.setattr("backend.app.create_admin", lambda: None)
    monkeypatch.setattr(auth_routes, "log_success", lambda user: None)
    monkeypatch.setattr(
        auth_routes,
        "find_user_by_id",
        lambda user_id: {
            "id": user_id,
            "name": "Student One",
            "username": "student1",
            "email": "student1@myrp.edu.sg",
            "student_id": "S12345",
            "role": "student",
            "two_factor_enabled": False,
            "two_factor_secret": None,
        },
    )

    def fake_save_user_2fa_secret(user_id, stored_secret):
        saved["user_id"] = user_id
        saved["secret"] = stored_secret
        return True

    monkeypatch.setattr(auth_routes, "save_user_2fa_secret", fake_save_user_2fa_secret)
    monkeypatch.setattr(auth_routes, "generate_2fa_qr_code", lambda username, value: "qr")
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
    client = app.test_client()

    with client.session_transaction() as flask_session:
        flask_session["pending_2fa_user_id"] = 2
        flask_session["pending_2fa_secret"] = secret

    response = client.post("/setup-2fa", data={"code": code})

    assert response.status_code == 302
    assert response.headers["Location"] == "/homepage"
    assert saved == {"user_id": 2, "secret": secret}
    with client.session_transaction() as flask_session:
        assert "pending_2fa_secret" not in flask_session
        assert flask_session["user_id"] == 2


def test_setup_2fa_invalid_code_does_not_persist(monkeypatch):
    saved = []
    secret = pyotp.random_base32()

    monkeypatch.setattr("backend.app.create_admin", lambda: None)
    monkeypatch.setattr(
        auth_routes,
        "find_user_by_id",
        lambda user_id: {
            "id": user_id,
            "username": "student1",
            "two_factor_enabled": False,
            "two_factor_secret": None,
        },
    )
    monkeypatch.setattr(auth_routes, "save_user_2fa_secret", lambda *args: saved.append(args))
    monkeypatch.setattr(auth_routes, "generate_2fa_qr_code", lambda username, value: "qr")
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
    client = app.test_client()

    with client.session_transaction() as flask_session:
        flask_session["pending_2fa_user_id"] = 2
        flask_session["pending_2fa_secret"] = secret

    response = client.post("/setup-2fa", data={"code": "123456"})

    assert response.status_code == 200
    assert b"Invalid authentication code" in response.data
    assert saved == []


def test_setup_2fa_expired_code_does_not_persist(monkeypatch):
    saved = []
    secret = pyotp.random_base32()
    expired_code = pyotp.TOTP(secret).at(int(time.time()) - 90)

    monkeypatch.setattr("backend.app.create_admin", lambda: None)
    monkeypatch.setattr(
        auth_routes,
        "find_user_by_id",
        lambda user_id: {
            "id": user_id,
            "username": "student1",
            "two_factor_enabled": False,
            "two_factor_secret": None,
        },
    )
    monkeypatch.setattr(auth_routes, "save_user_2fa_secret", lambda *args: saved.append(args))
    monkeypatch.setattr(auth_routes, "generate_2fa_qr_code", lambda username, value: "qr")
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
    client = app.test_client()

    with client.session_transaction() as flask_session:
        flask_session["pending_2fa_user_id"] = 2
        flask_session["pending_2fa_secret"] = secret

    response = client.post("/setup-2fa", data={"code": expired_code})

    assert response.status_code == 200
    assert b"Invalid authentication code" in response.data
    assert saved == []


def test_setup_2fa_handles_user_lookup_database_error(monkeypatch):
    monkeypatch.setattr("backend.app.create_admin", lambda: None)

    def raise_database_error(user_id):
        raise MySQLDatabaseError("MySQL runtime query failed.")

    monkeypatch.setattr(auth_routes, "find_user_by_id", raise_database_error)
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
    client = app.test_client()

    with client.session_transaction() as flask_session:
        flask_session["pending_2fa_user_id"] = 2

    response = client.get("/setup-2fa")

    assert response.status_code == 302
    assert "/error?title=2FA%20Setup%20Unavailable" in response.headers["Location"]


def test_setup_2fa_database_update_failure_clears_pending_secret(monkeypatch, caplog):
    secret = pyotp.random_base32()
    code = pyotp.TOTP(secret).now()

    monkeypatch.setattr("backend.app.create_admin", lambda: None)
    monkeypatch.setattr(
        auth_routes,
        "find_user_by_id",
        lambda user_id: {
            "id": user_id,
            "username": "student1",
            "two_factor_enabled": False,
            "two_factor_secret": None,
        },
    )

    def raise_database_error(user_id, stored_secret):
        raise MySQLDatabaseError("Two-factor authentication database columns are missing.")

    monkeypatch.setattr(auth_routes, "save_user_2fa_secret", raise_database_error)
    monkeypatch.setattr(auth_routes, "generate_2fa_qr_code", lambda username, value: "qr")
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
    client = app.test_client()

    with client.session_transaction() as flask_session:
        flask_session["pending_2fa_user_id"] = 2
        flask_session["pending_2fa_secret"] = secret

    with caplog.at_level(logging.WARNING):
        response = client.post("/setup-2fa", data={"code": code})

    assert response.status_code == 302
    assert response.headers["Location"] == "/setup-2fa"
    with client.session_transaction() as flask_session:
        assert "pending_2fa_secret" not in flask_session
        assert flask_session["setup_2fa_error"] == (
            "Two-factor authentication setup is temporarily unavailable."
        )
    assert secret not in caplog.text
    assert code not in caplog.text
    assert "MySQLDatabaseError" in caplog.text


def test_find_user_by_id_tolerates_missing_2fa_columns(monkeypatch):
    calls = []

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append(query)
        if "SELECT two_factor_enabled, two_factor_secret" in query:
            missing_column = Exception("Unknown column 'two_factor_enabled' in 'field list'")
            raise MySQLDatabaseError("MySQL runtime query failed.") from missing_column
        return [
            {
                "id": 2,
                "name": "Student One",
                "username": "student1",
                "email": "student1@myrp.edu.sg",
                "student_id": "S12345",
                "school": "SOI",
                "password_hash": "hash",
                "role": "student",
                "is_blocked": False,
                "created_at": datetime(2026, 7, 1, 9, 0, 0),
                "last_login_at": None,
                "status_updated_at": None,
            }
        ]

    monkeypatch.setattr(auth_service, "execute_mysql_query", fake_execute)

    user = auth_service.find_user_by_id(2)

    assert user["two_factor_enabled"] is False
    assert user["two_factor_secret"] is None
    assert len(calls) == 2


def test_products_load_from_mysql_preserves_template_shape(monkeypatch):
    def fake_execute(query, params=None, fetch=False, dictionary=True):
        assert fetch is True
        return [
            {
                "id": 1,
                "seller_id": 2,
                "seller_identifier": "student1",
                "legacy_seller_name": "Legacy Seller",
                "title": "Keyboard",
                "description": "Compact",
                "price": 25,
                "image_url": "",
                "status": "Available",
                "category_name": "Electronics",
                "seller_name": "Student One",
                "seller_username": "student1",
            }
        ]

    monkeypatch.setattr(seller_dashboard_service, "execute_mysql_query", fake_execute)

    product = seller_dashboard_service.load_products()[0]

    assert product["title"] == "Keyboard"
    assert product["name"] == "Keyboard"
    assert product["seller"] == "Legacy Seller"
    assert product["seller_id"] == 2


def test_wishlist_add_remove_use_mysql(monkeypatch):
    calls = []

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append((query, params, fetch))
        return [] if fetch else 1

    monkeypatch.setattr(marketplace_service, "get_product_by_id", lambda product_id: {"id": product_id})
    monkeypatch.setattr(marketplace_service, "execute_mysql_query", fake_execute)

    user = {"user_id": 5}
    assert marketplace_service.add_to_wishlist(10, user) is True
    assert marketplace_service.remove_from_wishlist(10, user) is True

    assert "INSERT INTO wishlists" in calls[0][0]
    assert calls[0][1] == (5, 10)
    assert "DELETE FROM wishlists" in calls[1][0]
    assert calls[1][1] == (5, 10)


def test_request_submission_uses_mysql(monkeypatch):
    calls = []

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append((query, params, fetch))
        return [] if fetch else 1

    product = {
        "id": 10,
        "title": "Keyboard",
        "seller_id": 99,
        "seller": "seller",
        "status": "Available",
    }
    monkeypatch.setattr(marketplace_service, "get_products", lambda: [product])
    monkeypatch.setattr(marketplace_service, "get_requests", lambda: [])
    monkeypatch.setattr(marketplace_service, "execute_mysql_query", fake_execute)
    monkeypatch.setattr(marketplace_service, "add_notification", lambda *args: None)

    ok, error = marketplace_service.request_buy(10, {"user_id": 5, "username": "buyer"})

    assert (ok, error) == (True, None)
    assert "INSERT INTO purchase_requests" in calls[0][0]
    assert calls[0][1][:4] == (10, 5, "buyer", "Pending")


def test_chat_send_and_read_use_mysql(monkeypatch):
    calls = []

    def fake_execute(query, params=None, fetch=False, dictionary=True):
        calls.append((query, params, fetch))
        if fetch:
            return [{"id": 8}]
        return 1

    monkeypatch.setattr(chat_service, "execute_mysql_query", fake_execute)

    message = chat_service.send_chat_message(
        10,
        {"user_id": 5, "username": "buyer"},
        "seller",
        "Hi",
    )
    chat_service.mark_conversation_read(10, {"user_id": 6}, "buyer")

    assert message["text"] == "Hi"
    assert "INSERT INTO messages" in calls[1][0]
    assert "UPDATE messages" in calls[3][0]


def test_migrations_read_archived_seed_data(monkeypatch, tmp_path):
    legacy_dir = tmp_path / "legacy_seed_data"
    legacy_dir.mkdir()
    (legacy_dir / "users.json").write_text('[{"id": 1}]', encoding="utf-8")
    (legacy_dir / "products.json").write_text('[{"id": 2}]', encoding="utf-8")

    monkeypatch.setattr(migrate_wishlists, "LEGACY_DATA_DIR", legacy_dir)
    monkeypatch.setattr(migrate_purchase_requests, "LEGACY_DATA_DIR", legacy_dir)
    monkeypatch.setattr(migrate_messages, "LEGACY_DATA_DIR", legacy_dir)

    assert migrate_wishlists.load_json_rows("users.json") == [{"id": 1}]
    assert migrate_purchase_requests.load_json_rows("products.json") == [{"id": 2}]
    assert migrate_messages.load_json_rows("users.json") == [{"id": 1}]


def test_runtime_source_does_not_import_json_storage():
    backend_files = [
        path for path in Path("backend").rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    offenders = [
        str(path)
        for path in backend_files
        if "json_storage" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
