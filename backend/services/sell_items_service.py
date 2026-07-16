from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename

from backend.db import execute_mysql_query
from backend.services.seller_dashboard_service import (
    category_id_for_name,
    delete_product as delete_dashboard_product,
    load_products,
    save_products as save_dashboard_products,
)


VALID_CATEGORIES = [
    "Electronics",
    "Books",
    "Food",
    "Clothing",
    "School Supplies",
    "Others",
]

VALID_STATUSES = [
    "Available",
    "Reserved",
    "Sold",
]

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def clean_text(value):
    return str(value or "").strip()


def get_seller_name(user):
    return (
        clean_text(user.get("username"))
        or clean_text(user.get("name"))
        or clean_text(user.get("email"))
        or clean_text(user.get("student_id"))
        or str(user.get("user_id"))
    )


def seller_keys(user):
    keys = set()

    for key in ["username", "name", "email", "student_id", "user_id"]:
        value = clean_text(user.get(key))

        if value:
            keys.add(value.lower())

    return keys


def product_belongs_to_user(product, user):
    seller = clean_text(product.get("seller")).lower()
    return seller in seller_keys(user)


def same_product_id(product, product_id):
    try:
        return int(product.get("id")) == int(product_id)
    except (TypeError, ValueError):
        return False


def get_products():
    return load_products()


def save_products(products):
    save_dashboard_products(products)


def get_next_product_id(products):
    if not products:
        return 1

    product_ids = []

    for product in products:
        try:
            product_ids.append(int(product.get("id", 0)))
        except (TypeError, ValueError):
            product_ids.append(0)

    return max(product_ids) + 1


def parse_price(value):
    try:
        price = float(value)

        if price < 0:
            return None

        return price
    except (TypeError, ValueError):
        return None


def allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def save_uploaded_image(files):
    if not files:
        return ""

    image = files.get("image")

    if not image or image.filename == "":
        return ""

    if not allowed_image(image.filename):
        return ""

    original_filename = secure_filename(image.filename)
    extension = original_filename.rsplit(".", 1)[1].lower()
    new_filename = f"{uuid4().hex}.{extension}"

    upload_folder = Path(current_app.static_folder) / "uploads"
    upload_folder.mkdir(parents=True, exist_ok=True)

    image.save(upload_folder / new_filename)

    return f"uploads/{new_filename}"


def get_my_sell_items(user):
    products = get_products()

    return [
        product for product in products
        if product_belongs_to_user(product, user)
    ]


def create_sell_item(form, files, user):
    title = clean_text(form.get("title"))
    description = clean_text(form.get("description"))
    category = clean_text(form.get("category")) or "Others"
    price = parse_price(form.get("price"))
    image_url = save_uploaded_image(files)

    if not title:
        return False, "Product title is required."

    if not description:
        return False, "Product description is required."

    if price is None:
        return False, "Please enter a valid price."

    if category not in VALID_CATEGORIES:
        category = "Others"

    category_id = category_id_for_name(category)
    execute_mysql_query(
        """
        INSERT INTO products (
            seller_id, seller_identifier, category_id, title,
            description, price, image_url, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user.get("user_id"),
            get_seller_name(user),
            category_id,
            title,
            description,
            price,
            image_url,
            "Available",
        ),
    )

    return True, None


def update_sell_item(product_id, form, files, user):
    products = get_products()

    title = clean_text(form.get("title"))
    description = clean_text(form.get("description"))
    category = clean_text(form.get("category")) or "Others"
    price = parse_price(form.get("price"))
    status = clean_text(form.get("status")) or "Available"
    new_image_url = save_uploaded_image(files)

    if not title:
        return False, "Product title is required."

    if not description:
        return False, "Product description is required."

    if price is None:
        return False, "Please enter a valid price."

    if category not in VALID_CATEGORIES:
        category = "Others"

    if status not in VALID_STATUSES:
        status = "Available"

    for product in products:
        if same_product_id(product, product_id) and product_belongs_to_user(product, user):
            product["title"] = title
            product["name"] = title
            product["description"] = description
            product["category"] = category
            product["price"] = price
            product["status"] = status

            if new_image_url:
                product["image_url"] = new_image_url

            save_products(products)
            return True, None

    return False, "Product not found or you do not own this listing."


def delete_sell_item(product_id, user):
    return delete_dashboard_product(product_id, user)
