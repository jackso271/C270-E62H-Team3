from flask import Blueprint, redirect, render_template, request, session

from backend.services.admin_service import (
    delete_logs,
    delete_user_by_id,
    get_user,
    list_users,
    toggle_user_block,
    update_user,
)
from backend.utils.date_filters import filter_logs_by_date
from backend.utils.json_storage import data_file, load_json


admin_bp = Blueprint("admin", __name__)


def require_admin():
    """Return True when the logged-in user is allowed to access admin pages."""
    return session.get("role") == "admin"


@admin_bp.route("/admin/dashboard")
def admin_dashboard():
    if not require_admin():
        return redirect("/")

    return render_template(
        "admin/dashboard.html",
        users=load_json(data_file("users")),
        success_logs=load_json(data_file("success_logs")),
        failed_logs=load_json(data_file("failed_logs")),
    )


@admin_bp.route("/admin/users")
def admin_users():
    if not require_admin():
        return redirect("/")

    search = request.args.get("search", "").lower()
    page = int(request.args.get("page", 1))
    users, total_pages = list_users(search=search, page=page)

    return render_template(
        "admin/users.html",
        users=users,
        search=search,
        page=page,
        total_pages=total_pages,
    )


@admin_bp.route("/admin/success-logs")
def admin_success_logs():
    if not require_admin():
        return redirect("/")

    day = request.args.get("day")
    month = request.args.get("month")
    year = request.args.get("year")
    success_logs = load_json(data_file("success_logs"))

    if day or month or year:
        success_logs = filter_logs_by_date(success_logs, day, month, year)

    return render_template(
        "admin/success_logs.html",
        success_logs=success_logs,
        day=day,
        month=month,
        year=year,
    )


@admin_bp.route("/admin/failed-logs")
def admin_failed_logs():
    if not require_admin():
        return redirect("/")

    day = request.args.get("day")
    month = request.args.get("month")
    year = request.args.get("year")
    failed_logs = load_json(data_file("failed_logs"))

    if day or month or year:
        failed_logs = filter_logs_by_date(failed_logs, day, month, year)

    return render_template(
        "admin/failed_logs.html",
        failed_logs=failed_logs,
        day=day,
        month=month,
        year=year,
    )


@admin_bp.route("/admin/delete-success-logs", methods=["POST"])
def delete_success_logs():
    if not require_admin():
        return redirect("/")

    delete_logs("success_logs", request.form.getlist("selected_logs"))
    return redirect("/admin/success-logs")


@admin_bp.route("/admin/delete-failed-logs", methods=["POST"])
def delete_failed_logs():
    if not require_admin():
        return redirect("/")

    delete_logs("failed_logs", request.form.getlist("selected_logs"))
    return redirect("/admin/failed-logs")


@admin_bp.route("/admin/edit/<int:user_id>")
def edit_user_page(user_id):
    if not require_admin():
        return redirect("/")

    user = get_user(user_id)

    if user:
        return render_template("admin/edit_user.html", user=user)

    return "User not found."


@admin_bp.route("/admin/edit/<int:user_id>", methods=["POST"])
def edit_user(user_id):
    if not require_admin():
        return redirect("/")

    update_user(user_id, request.form)
    return redirect("/admin/users")


@admin_bp.route("/admin/delete/<int:user_id>")
def delete_user(user_id):
    if not require_admin():
        return redirect("/")

    delete_user_by_id(user_id)
    return redirect("/admin/users")


@admin_bp.route("/admin/block/<int:user_id>")
def block_user(user_id):
    if not require_admin():
        return redirect("/")

    toggle_user_block(user_id)
    return redirect("/admin/users")
