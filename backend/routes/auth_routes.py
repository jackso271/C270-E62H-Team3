from flask import Blueprint, redirect, render_template, request, session

from backend.services.auth_service import (
    find_matching_user,
    log_failed,
    log_success,
    register_user,
)


auth_bp = Blueprint("auth", __name__)


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

        session["user_id"] = user.get("id")
        session["name"] = user.get("name")
        session["role"] = user.get("role")

        log_success(user)

        if user.get("role") == "admin":
            return redirect("/admin/dashboard")

        return redirect("/homepage")

    log_failed(login_id, "Invalid login")
    return render_template("user/login_error.html")


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
