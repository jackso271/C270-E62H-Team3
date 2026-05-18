from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import json
import time
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

request_log = defaultdict(list)
RATE_LIMIT = 10
TIME_WINDOW = 60

def is_rate_limited(ip_address):
    current_time = time.time()
    request_log[ip_address] = [t for t in request_log[ip_address] if current_time - t < TIME_WINDOW]
    if len(request_log[ip_address]) >= RATE_LIMIT:
        return True
    request_log[ip_address].append(current_time)
    return False

def load_users():
    with open("data/users.json", "r") as file:
        return json.load(file)

def save_successful_login(name, login_input):
    with open("data/successful_logins.json", "r") as file:
        logs = json.load(file)
    logs.append({"name": name, "login_input": login_input, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    with open("data/successful_logins.json", "w") as file:
        json.dump(logs, file, indent=4)

def save_failed_login(login_input, reason):
    with open("data/failed_logins.json", "r") as file:
        logs = json.load(file)
    logs.append({"login_input": login_input, "reason": reason, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    with open("data/failed_logins.json", "w") as file:
        json.dump(logs, file, indent=4)

def is_rp_login(login_input):
    return login_input.endswith("@myrp.edu.sg") or login_input.isdigit()

products = [
    {"id": 1, "name": "iPhone 12", "seller": "Alex Tan", "price": 450, "description": "Good condition, 128GB"},
    {"id": 2, "name": "Laptop Stand", "seller": "Sarah Lim", "price": 25, "description": "Adjustable aluminium stand"},
    {"id": 3, "name": "Sony Headphones", "seller": "Wei Ming", "price": 80, "description": "WH-1000XM4, noise cancelling"},
    {"id": 4, "name": "Samsung A52", "seller": "Priya S", "price": 200, "description": "6 months old, like new"},
    {"id": 5, "name": "Apple Watch SE", "seller": "Jason Ng", "price": 180, "description": "Series SE, 40mm"},
    {"id": 6, "name": "PS4 Controller", "seller": "Hafiz R", "price": 40, "description": "Slightly used, works perfectly"},
    {"id": 7, "name": "Mechanical Keyboard", "seller": "Chloe W", "price": 65, "description": "Blue switches, TKL layout"},
    {"id": 8, "name": "Webcam 1080p", "seller": "Daniel K", "price": 55, "description": "Logitech C920, great for calls"},
]

wishlists = {}

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
            if (login_input == user["email"] or login_input == user["student_id"]) and password == user["password"]:
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
    user_id = session["user_id"]
    user_wishlist = wishlists.get(user_id, [])
    return render_template("home.html", name=session["name"], products=products, user_wishlist=user_wishlist)

@app.route("/wishlist")
def wishlist():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    saved_ids = wishlists.get(user_id, [])
    saved_products = [p for p in products if p["id"] in saved_ids]
    return render_template("wishlist.html", name=session["name"], wishlist_items=saved_products)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/api/wishlist/add", methods=["POST"])
def wishlist_add():
    if "user_id" not in session:
        return jsonify({"success": False}), 401
    data = request.get_json()
    user_id = session["user_id"]
    if user_id not in wishlists:
        wishlists[user_id] = []
    if data["product_id"] not in wishlists[user_id]:
        wishlists[user_id].append(data["product_id"])
    return jsonify({"success": True})

@app.route("/api/wishlist/remove", methods=["POST"])
def wishlist_remove():
    if "user_id" not in session:
        return jsonify({"success": False}), 401
    data = request.get_json()
    user_id = session["user_id"]
    if user_id in wishlists and data["product_id"] in wishlists[user_id]:
        wishlists[user_id].remove(data["product_id"])
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)
