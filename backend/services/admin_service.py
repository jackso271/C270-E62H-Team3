from backend.utils.json_storage import data_file, load_json, save_json


def list_users(search="", page=1, per_page=10):
    """Search and paginate users for the admin user table."""
    users = load_json(data_file("users"))
    search = search.lower()

    if search:
        users = [
            user for user in users
            if (
                search in str(user.get("name", "")).lower()
                or search in str(user.get("student_id", "")).lower()
                or search in str(user.get("email", "")).lower()
                or search in str(user.get("username", "")).lower()
            )
        ]

    total_users = len(users)
    total_pages = (total_users + per_page - 1) // per_page

    if total_pages == 0:
        total_pages = 1

    start = (page - 1) * per_page
    end = start + per_page

    return users[start:end], total_pages


def get_user(user_id):
    for user in load_json(data_file("users")):
        if user.get("id") == user_id:
            return user
    return None


def update_user(user_id, form):
    users = load_json(data_file("users"))

    for user in users:
        if user.get("id") == user_id:
            user["name"] = form.get("name")
            user["username"] = form.get("username")
            user["student_id"] = form.get("student_id")
            user["role"] = form.get("role")
            break

    save_json(data_file("users"), users)


def delete_user_by_id(user_id):
    users = [
        user for user in load_json(data_file("users"))
        if user.get("id") != user_id
    ]
    save_json(data_file("users"), users)


def toggle_user_block(user_id):
    users = load_json(data_file("users"))

    for user in users:
        if user.get("id") == user_id:
            user["blocked"] = not user.get("blocked", False)
            break

    save_json(data_file("users"), users)


def delete_logs(log_type, selected_times):
    logs = [
        log for log in load_json(data_file(log_type))
        if log.get("time") not in selected_times
    ]
    save_json(data_file(log_type), logs)
