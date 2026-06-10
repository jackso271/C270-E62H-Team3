<<<<<<< HEAD
from backend.app import create_app


app = create_app()
=======
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import json
import time
import os
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)
app.secret_key = "rp_marketplace_secret_key"


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# Rate limiter settings
request_log = defaultdict(list)
RATE_LIMIT = 10
TIME_WINDOW = 60


def is_rate_limited(ip_address):
    current_time = time.time()

    request_log[ip_address] = [
        t for t in request_log[ip_address]
        if current_time - t < TIME_WINDOW
    ]

    if len(request_log[ip_address]) >= RATE_LIMIT:
        return True

    request_log[ip_address].append(current_time)
    return False


def load_users():
    with open("data/users.json", "r") as file:
        return json.load(file)


def load_products():
    with open("data/products.json", "r") as file:
        return json.load(file)


def load_wishlists():
    if not os.path.exists("data/wishlists.json"):
        return {}
    with open("data/wishlists.json", "r") as file:
        return json.load(file)


def save_wishlists(wishlists):
    with open("data/wishlists.json", "w") as file:
        json.dump(wishlists, file, indent=4)


def save_successful_login(name, login_input):
    with open("data/successful_logins.json", "r") as file:
        logs = json.load(file)

    logs.append({
        "name": name,
        "login_input": login_input,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    with open("data/successful_logins.json", "w") as file:
        json.dump(logs, file, indent=4)


def save_failed_login(login_input, reason):
    with open("data/failed_logins.json", "r") as file:
        logs = json.load(file)

    logs.append({
        "login_input": login_input,
        "reason": reason,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    with open("data/failed_logins.json", "w") as file:
        json.dump(logs, file, indent=4)


def is_rp_login(login_input):
    return login_input.endswith("@myrp.edu.sg") or login_input.isdigit()


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        ip_address = request.remote_addr

        if is_rate_limited(ip_address):
            error = "Too many login attempts. Please wait before trying again."
            return render_template("login.html", error=error)

        login_input = request.form["login_input"].strip()
        password = request.form["password"].strip()

        if not is_rp_login(login_input):
            error = "Only RP student email or student ID is allowed."
            save_failed_login(login_input, "Non-RP login blocked")
            return render_template("login.html", error=error)

        users = load_users()

        for user in users:
            valid_email = login_input == user["email"]
            valid_student_id = login_input == user["student_id"]
            valid_password = password == user["password"]

            if (valid_email or valid_student_id) and valid_password:
                session.clear()
                session["user_id"] = user["id"]
                session["name"] = user["name"]

                save_successful_login(user["name"], login_input)

                return redirect(url_for("home"))

        error = "Invalid RP student login details."
        save_failed_login(login_input, "Invalid credentials")

    return render_template("login.html", error=error)


@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    products = load_products()
    wishlists = load_wishlists()
    user_wishlist = wishlists.get(str(session["user_id"]), [])

    return render_template("home.html", name=session["name"], products=products, user_wishlist=user_wishlist)


@app.route("/wishlist")
def wishlist():
    if "user_id" not in session:
        return redirect(url_for("login"))

    products = load_products()
    wishlists = load_wishlists()
    user_wishlist_ids = wishlists.get(str(session["user_id"]), [])
    
    # Get full product details for wishlist items
    wishlist_items = [p for p in products if p["id"] in user_wishlist_ids]

    return render_template("wishlist.html", name=session["name"], wishlist_items=wishlist_items)


@app.route("/api/wishlist/add", methods=["POST"])
def add_to_wishlist():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    product_id = data.get("product_id")

    wishlists = load_wishlists()
    user_id = str(session["user_id"])

    if user_id not in wishlists:
        wishlists[user_id] = []

    if product_id not in wishlists[user_id]:
        wishlists[user_id].append(product_id)
        save_wishlists(wishlists)

    return jsonify({"success": True})


@app.route("/api/wishlist/remove", methods=["POST"])
def remove_from_wishlist():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    product_id = data.get("product_id")

    wishlists = load_wishlists()
    user_id = str(session["user_id"])

    if user_id in wishlists and product_id in wishlists[user_id]:
        wishlists[user_id].remove(product_id)
        save_wishlists(wishlists)

    return jsonify({"success": True})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
>>>>>>> origin/main


if __name__ == "__main__":
    app.run(debug=True)
