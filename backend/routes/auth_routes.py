import base64
from io import BytesIO

import pyotp
import qrcode
from flask import Blueprint, current_app, redirect, render_template, request, session

from backend.db import MySQLDatabaseError
from backend.services.auth_service import (
    find_user_by_id,
    find_user_by_login_id,
    find_matching_user,
    generate_2fa_secret,
    log_failed,
    log_password_reset_request,
    log_success,
    register_user,
    save_user_2fa_secret,
    user_has_2fa_enabled,
    verify_2fa_code,
)


auth_bp = Blueprint("auth", __name__)

def store_pending_2fa_user(user):
    session.clear()
    session["pending_2fa_user_id"] = user.get("id")


def get_pending_2fa_user():
    user_id = session.get("pending_2fa_user_id")

    if not user_id:
        return None

    return find_user_by_id(user_id)


def complete_login(user):
    session.pop("pending_2fa_user_id", None)
    session.pop("pending_2fa_secret", None)

    session.permanent = True
    session["user_id"] = user.get("id")
    session["name"] = user.get("name")
    session["username"] = user.get("username")
    session["email"] = user.get("email")
    session["student_id"] = user.get("student_id")
    session["role"] = user.get("role")

    log_success(user)

    if user.get("role") == "admin":
        return redirect("/admin/dashboard")

    return redirect("/homepage")


def generate_2fa_qr_code(username, secret):
    totp = pyotp.TOTP(secret)

    setup_uri = totp.provisioning_uri(
        name=username or "RP Marketplace User",
        issuer_name="RP Marketplace",
    )

    qr_image = qrcode.make(setup_uri)
    buffer = BytesIO()
    qr_image.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{qr_base64}"

@auth_bp.route("/")
def login_page():
    return render_template("user/login.html")


@auth_bp.route("/register")
def register_page():
    return render_template("user/register.html")


@auth_bp.route("/register", methods=["POST"])
def register():
    success, title, message = register_user(request.form)

    if not success:
        return redirect(
            f"/error?title={title}"
            f"&message={message}"
            "&back_url=/register"
        )

    return redirect("/")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return redirect("/")

    login_id = request.form.get("login_id", "").strip().lower()
    password = request.form.get("password", "").strip()

    if not login_id or not password:
        return redirect(
            "/error?title=Missing Login Details"
            "&message=Please enter your login ID and password."
            "&back_url=/"
        )

    user = find_matching_user(login_id, password)

    if user:
        if user.get("blocked") is True:
            log_failed(login_id, "Blocked account")
            return redirect(
                "/error?title=Account Blocked"
                "&message=Your account has been blocked. Please contact the administrator."
                "&back_url=/"
            )

        store_pending_2fa_user(user)

        if user_has_2fa_enabled(user):
            return redirect("/verify-2fa")

        return redirect("/setup-2fa")

    existing_user = find_user_by_login_id(login_id)
    if existing_user:
        log_failed(login_id, "Wrong password")
    else:
        log_failed(login_id, "Account not found")

    return render_template("user/login_error.html")

@auth_bp.route("/setup-2fa", methods=["GET", "POST"])
def setup_2fa():
    try:
        user = get_pending_2fa_user()
    except MySQLDatabaseError as error:
        current_app.logger.warning(
            "2FA setup user lookup failed: %s",
            type(error).__name__,
        )
        return redirect(
            "/error?title=2FA Setup Unavailable"
            "&message=Two-factor authentication setup is temporarily unavailable."
            "&back_url=/"
        )

    if not user:
        return redirect("/")

    if user_has_2fa_enabled(user):
        return redirect("/verify-2fa")

    setup_error = session.pop("setup_2fa_error", None)

    if "pending_2fa_secret" not in session:
        session["pending_2fa_secret"] = generate_2fa_secret()

    secret = session["pending_2fa_secret"]
    qr_code = generate_2fa_qr_code(user.get("username"), secret)

    if request.method == "POST":
        code = request.form.get("code", "").strip()

        if verify_2fa_code(secret, code):
            try:
                save_user_2fa_secret(user.get("id"), secret)
                updated_user = find_user_by_id(user.get("id"))
            except MySQLDatabaseError as error:
                current_app.logger.warning(
                    "2FA setup save failed: %s",
                    type(error).__name__,
                )
                session.pop("pending_2fa_secret", None)
                session["setup_2fa_error"] = (
                    "Two-factor authentication setup is temporarily unavailable."
                )
                return redirect("/setup-2fa")
            return complete_login(updated_user)

        return render_template(
            "user/setup_2fa.html",
            secret=secret,
            qr_code=qr_code,
            error="Invalid authentication code. Please try again.",
        )

    return render_template(
        "user/setup_2fa.html",
        secret=secret,
        qr_code=qr_code,
        error=setup_error,
    )


@auth_bp.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    try:
        user = get_pending_2fa_user()
    except MySQLDatabaseError as error:
        current_app.logger.warning(
            "2FA verification user lookup failed: %s",
            type(error).__name__,
        )
        return redirect(
            "/error?title=2FA Verification Unavailable"
            "&message=Two-factor authentication verification is temporarily unavailable."
            "&back_url=/"
        )

    if not user:
        return redirect("/")

    if not user_has_2fa_enabled(user):
        return redirect("/setup-2fa")

    if request.method == "POST":
        code = request.form.get("code", "").strip()

        if verify_2fa_code(user.get("two_factor_secret"), code):
            return complete_login(user)

        return render_template(
            "user/verify_2fa.html",
            error="Invalid authentication code. Please try again.",
        )

    return render_template("user/verify_2fa.html", error=None)

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    login_id = request.form.get("login_id", "").strip()
    log_password_reset_request(login_id)

    return redirect(
        "/error?title=Password Reset Request Logged"
        "&message=Your password reset request has been recorded for admin review."
        "&back_url=/"
    )


@auth_bp.route("/homepage")
def homepage():
    if "user_id" not in session:
        return redirect("/")

    return render_template("user/homepage.html", name=session.get("name"))


@auth_bp.route("/error")
def error_page():
    title = request.args.get("title", "Error")
    message = request.args.get("message", "Something went wrong.")
    back_url = request.args.get("back_url", "/")

    return render_template(
        "user/error.html",
        title=title,
        message=message,
        back_url=back_url,
    )


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")
