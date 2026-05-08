from flask import Flask, render_template, request, redirect, session
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "rp_marketplace_secret_key"

# =========================
# FILE PATHS
# =========================

USERS_FILE = "data/users.json"
SUCCESS_LOG_FILE = "data/success_logins.json"
FAILED_LOG_FILE = "data/failed_logins.json"


# =========================
# CREATE DATA FILES
# =========================

def ensure_data_files():
    os.makedirs("data", exist_ok=True)

    files = [
        USERS_FILE,
        SUCCESS_LOG_FILE,
        FAILED_LOG_FILE
    ]

    for file in files:
        if not os.path.exists(file):
            with open(file, "w") as f:
                json.dump([], f, indent=4)


# =========================
# LOAD & SAVE JSON
# =========================

def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return []


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# CREATE ADMIN ACCOUNT
# =========================

def create_admin():
    users = load_json(USERS_FILE)

    admin_exists = False

    for user in users:
        if user.get("username") == "admin":
            admin_exists = True

            user["name"] = user.get("name") or "Admin"
            user["email"] = user.get("email") or "admin@rp.edu.sg"
            user["student_id"] = user.get("student_id") or "admin"
            user["role"] = "admin"
            user["blocked"] = user.get("blocked", False)

    if not admin_exists:
        users.append({
            "id": 1,
            "name": "Admin",
            "username": "admin",
            "email": "admin@rp.edu.sg",
            "student_id": "admin",
            "password": "admin123",
            "role": "admin",
            "blocked": False
        })

    save_json(USERS_FILE, users)


# =========================
# LOGIN LOGS
# =========================

def log_success(user):
    logs = load_json(SUCCESS_LOG_FILE)

    logs.append({
        "name": user.get("name") or user.get("username") or "Unknown",
        "username": user.get("username"),
        "role": user.get("role"),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    save_json(SUCCESS_LOG_FILE, logs)


def log_failed(username, reason):
    logs = load_json(FAILED_LOG_FILE)

    logs.append({
        "username": username,
        "reason": reason,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    save_json(FAILED_LOG_FILE, logs)

def filter_logs_by_date(logs, day, month, year):
    filtered_logs = []

    for log in logs:
        log_time = log.get("time", "")

        try:
            log_date = datetime.strptime(log_time, "%Y-%m-%d %H:%M:%S")
        except:
            continue

        if day and log_date.day != int(day):
            continue

        if month and log_date.month != int(month):
            continue

        if year and log_date.year != int(year):
            continue

        filtered_logs.append(log)

    return filtered_logs


# =========================
# INITIAL SETUP
# =========================

ensure_data_files()
create_admin()


# =========================
# LOGIN PAGE
# =========================

@app.route("/")
def login_page():
    return render_template("user/login.html")


# =========================
# REGISTER PAGE
# =========================

@app.route("/register")
def register_page():
    return render_template("user/register.html")


# =========================
# REGISTER ACCOUNT
# =========================

@app.route("/register", methods=["POST"])
def register():

    name = request.form.get("name")
    username = request.form.get("username")
    email = request.form.get("email")
    student_id = request.form.get("student_id")
    school = request.form.get("school")
    password = request.form.get("password")

    users = load_json(USERS_FILE)

    # RP student verification
    if not email.endswith("@myrp.edu.sg"):
        return redirect(
            "/error?title=Invalid RP Email"
            "&message=Only RP students using official RP emails are allowed to register."
            "&back_url=/register"
        )
    
    if not email.endswith("@myrp.edu.sg"):
        return redirect(
            "/error?title=Invalid RP Email"
            "&message=Please register using your RP school email ending with @myrp.edu.sg."
            "&back_url=/register"
        )

    # Check duplicate account
    for user in users:
        if (
            user.get("username") == username
            or user.get("student_id") == student_id
        ):
            return redirect(
                "/error?title=Account Already Exists"
                "&message=This username, student ID, or email is already registered."
                "&back_url=/register"
            )

    new_user = {
    "id": len(users) + 1,
    "name": name,
    "username": username,
    "email": email,
    "student_id": student_id,
    "school": school,
    "password": password,
    "role": "student",
    "blocked": False,
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

    users.append(new_user)

    save_json(USERS_FILE, users)

    return redirect("/")


# =========================
# LOGIN SYSTEM
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return redirect("/")

    login_id = (
        request.form.get("login_id", "").strip().lower()
    )

    password = request.form.get("password", "").strip()

    if not login_id or not password:
        return redirect(
            "/error?title=Missing Login Details"
            "&message=Please enter your login ID and password."
            "&back_url=/"
        )

    users = load_json(USERS_FILE)

    for user in users:

        username = str(user.get("username", "")).strip().lower()
        email = str(user.get("email", "")).strip().lower()
        student_id = str(user.get("student_id", "")).strip().lower()
        saved_password = str(user.get("password", "")).strip()
        name = str(user.get("name", "")).strip().lower()

        if (
            login_id == username
            or login_id == email
            or login_id == student_id
            or login_id == name
        ) and password == saved_password:

            if user.get("blocked") == True:
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

# =========================
# HOMEPAGE
# =========================

@app.route("/homepage")
def homepage():

    if "user_id" not in session:
        return redirect("/")

    return render_template(
        "user/homepage.html",
        name=session.get("name")
    )


# =========================
# ADMIN DASHBOARD
# =========================

@app.route("/admin/dashboard")
def admin_dashboard():

    if session.get("role") != "admin":
        return redirect("/")

    users = load_json(USERS_FILE)

    success_logs = load_json(SUCCESS_LOG_FILE)

    failed_logs = load_json(FAILED_LOG_FILE)

    return render_template(
        "admin/dashboard.html",
        users=users,
        success_logs=success_logs,
        failed_logs=failed_logs
    )


@app.route('/admin/users')
def admin_users():

    if session.get("role") != "admin":
        return redirect("/")

    users = load_json(USERS_FILE)

    search = request.args.get('search', '').lower()

    page = int(request.args.get('page', 1))

    per_page = 10

    # =========================
    # SEARCH FILTER
    # =========================

    if search:

        users = [

            user for user in users

            if (

                search in str(user.get('name', '')).lower()

                or search in str(user.get('student_id', '')).lower()

                or search in str(user.get('email', '')).lower()

                or search in str(user.get('username', '')).lower()

            )

        ]

    # =========================
    # PAGINATION
    # =========================

    total_users = len(users)

    total_pages = (total_users + per_page - 1) // per_page

    if total_pages == 0:
        total_pages = 1

    start = (page - 1) * per_page

    end = start + per_page

    users = users[start:end]

    # =========================
    # RENDER PAGE
    # =========================

    return render_template(

        'admin/users.html',

        users=users,

        search=search,

        page=page,

        total_pages=total_pages

    )


@app.route("/admin/success-logs")
def admin_success_logs():
    if session.get("role") != "admin":
        return redirect("/")

    day = request.args.get("day")
    month = request.args.get("month")
    year = request.args.get("year")

    success_logs = load_json(SUCCESS_LOG_FILE)

    if day or month or year:
        success_logs = filter_logs_by_date(success_logs, day, month, year)

    return render_template(
        "admin/success_logs.html",
        success_logs=success_logs,
        day=day,
        month=month,
        year=year
    )

@app.route("/admin/failed-logs")
def admin_failed_logs():
    if session.get("role") != "admin":
        return redirect("/")

    day = request.args.get("day")
    month = request.args.get("month")
    year = request.args.get("year")

    failed_logs = load_json(FAILED_LOG_FILE)

    if day or month or year:
        failed_logs = filter_logs_by_date(failed_logs, day, month, year)

    return render_template(
        "admin/failed_logs.html",
        failed_logs=failed_logs,
        day=day,
        month=month,
        year=year
    )

@app.route("/admin/delete-success-logs", methods=["POST"])
def delete_success_logs():
    if session.get("role") != "admin":
        return redirect("/")

    selected_times = request.form.getlist("selected_logs")

    logs = load_json(SUCCESS_LOG_FILE)

    logs = [
        log for log in logs
        if log.get("time") not in selected_times
    ]

    save_json(SUCCESS_LOG_FILE, logs)

    return redirect("/admin/success-logs")

# =========================
# DELETE ROUTES IN app.py
# =========================

@app.route("/admin/delete-failed-logs", methods=["POST"])
def delete_failed_logs():
    if session.get("role") != "admin":
        return redirect("/")

    selected_times = request.form.getlist("selected_logs")

    logs = load_json(FAILED_LOG_FILE)

    logs = [
        log for log in logs
        if log.get("time") not in selected_times
    ]

    save_json(FAILED_LOG_FILE, logs)

    return redirect("/admin/failed-logs")



# =========================
# EDIT USER PAGE
# =========================

@app.route("/admin/edit/<int:user_id>")
def edit_user_page(user_id):

    if session.get("role") != "admin":
        return redirect("/")

    users = load_json(USERS_FILE)

    for user in users:
        if user.get("id") == user_id:
            return render_template(
                "admin/edit_user.html",
                user=user
            )

    return "User not found."


# =========================
# UPDATE USER
# =========================

@app.route("/admin/edit/<int:user_id>", methods=["POST"])
def edit_user(user_id):

    if session.get("role") != "admin":
        return redirect("/")

    users = load_json(USERS_FILE)

    for user in users:

        if user.get("id") == user_id:

            user["name"] = request.form.get("name")
            user["username"] = request.form.get("username")
            user["student_id"] = request.form.get("student_id")
            user["role"] = request.form.get("role")

            break

    save_json(USERS_FILE, users)

    return redirect("/admin/users")


# =========================
# DELETE USER
# =========================

@app.route("/admin/delete/<int:user_id>")
def delete_user(user_id):

    if session.get("role") != "admin":
        return redirect("/")

    users = load_json(USERS_FILE)

    users = [
        user for user in users
        if user.get("id") != user_id
    ]

    save_json(USERS_FILE, users)

    return redirect("/admin/users")


# =========================
# BLOCK / UNBLOCK USER
# =========================

@app.route("/admin/block/<int:user_id>")
def block_user(user_id):

    if session.get("role") != "admin":
        return redirect("/")

    users = load_json(USERS_FILE)

    for user in users:

        if user.get("id") == user_id:

            user["blocked"] = not user.get("blocked", False)

            break

    save_json(USERS_FILE, users)

    return redirect("/admin/users")


@app.route("/error")
def error_page():
    title = request.args.get("title", "Error")
    message = request.args.get("message", "Something went wrong.")
    back_url = request.args.get("back_url", "/")

    return render_template(
        "user/error.html",
        title=title,
        message=message,
        back_url=back_url
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")



# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(debug=True)