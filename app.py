from flask import Flask, render_template, request, redirect
import json
import os

app = Flask(__name__)

USERS_FILE = 'data/users.json'


def load_users():
    if not os.path.exists(USERS_FILE):
        return []

    try:
        with open(USERS_FILE, 'r') as file:
            return json.load(file)
    except:
        return []


def save_users(users):
    with open(USERS_FILE, 'w') as file:
        json.dump(users, file, indent=4)


def create_admin():
    users = load_users()

    admin_exists = any(
        user.get('username') == 'admin'
        for user in users
    )

    if not admin_exists:
        users.append({
            "id": len(users) + 1,
            "username": "admin",
            "password": "admin123",
            "role": "admin",
            "blocked": False
        })

        save_users(users)


create_admin()


@app.route('/')
def login():
    return render_template('user/login.html')


@app.route('/login', methods=['POST'])
def login_post():
    login_id = request.form.get('login_id')
    password = request.form.get('password')

    users = load_users()

    for user in users:
        is_admin = (
            user.get('role') == 'admin' and
            user.get('username') == login_id and
            user.get('password') == password
        )

        is_student = (
            user.get('role') == 'user' and
            (
                user.get('student_id') == login_id or
                user.get('email') == login_id
            ) and
            user.get('password') == password
        )

        if is_admin or is_student:
            if user.get('blocked') == True:
                return "Your account has been blocked"

            if user.get('role') == 'admin':
                return redirect('/admin/dashboard')

            return redirect('/home')

    return "Invalid login details"


@app.route('/register')
def register():
    return render_template('user/register.html')


@app.route('/register', methods=['POST'])
def register_post():
    student_id = request.form.get('student_id')
    email = request.form.get('email')
    password = request.form.get('password')

    users = load_users()

    for user in users:
        if user.get('student_id') == student_id or user.get('email') == email:
            return "Account already exists"

    new_user = {
        "id": len(users) + 1,
        "student_id": student_id,
        "email": email,
        "password": password,
        "role": "user",
        "blocked": False
    }

    users.append(new_user)
    save_users(users)

    return redirect('/')


@app.route('/home')
def home():
    return render_template('user/home.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    users = load_users()
    return render_template('admin/admin_dashboard.html', users=users)


@app.route('/admin/delete/<int:user_id>')
def delete_user(user_id):
    users = load_users()

    users = [
        user for user in users
        if user.get('id') != user_id
    ]

    save_users(users)
    return redirect('/admin/dashboard')


@app.route('/admin/block/<int:user_id>')
def block_user(user_id):
    users = load_users()

    for user in users:
        if user.get('id') == user_id:
            user['blocked'] = not user.get('blocked', False)

    save_users(users)
    return redirect('/admin/dashboard')


@app.route('/logout')
def logout():
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
    