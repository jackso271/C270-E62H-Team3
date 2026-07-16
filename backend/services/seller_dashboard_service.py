from decimal import Decimal

from backend.db import execute_mysql_query, mysql_products_enabled
from backend.utils.json_storage import data_file, load_json, save_json


VALID_STATUSES = ["Available", "Sold", "Reserved"]
VALID_CATEGORIES = ["Electronics", "Books", "Food", "Others"]


def normalize_text(value):
    return str(value or "").strip()


def normalize_key(value):
    return normalize_text(value).lower()


def seller_identifiers(user):
    """Build the set of values that can identify a seller in product JSON."""
    identifiers = set()

    for key in ["username", "name", "email", "student_id", "user_id"]:
        value = normalize_text(user.get(key))
        if value:
            identifiers.add(normalize_key(value))

    return identifiers


def seller_name(user):
    """Choose a stable seller name for new products."""
    return (
        normalize_text(user.get("username"))
        or normalize_text(user.get("name"))
        or normalize_text(user.get("email"))
        or normalize_text(user.get("student_id"))
        or str(user.get("user_id"))
    )


def product_belongs_to_seller(product, user):
    product_seller_id = product.get("seller_id")
    user_id = user.get("user_id") or user.get("id")

    if product_seller_id is not None and user_id is not None:
        try:
            return int(product_seller_id) == int(user_id)
        except (TypeError, ValueError):
            return False

    seller = normalize_key(product.get("seller"))
    return seller and seller in seller_identifiers(user)


def clean_product(product):
    """Keep product records compatible with the existing marketplace template."""
    title = normalize_text(product.get("title")) or normalize_text(product.get("name"))
    name = normalize_text(product.get("name")) or title
    status = normalize_text(product.get("status")) or "Available"
    category = normalize_text(product.get("category")) or "Others"

    return {
        **product,
        "title": title,
        "name": name,
        "description": normalize_text(product.get("description")),
        "price": product.get("price", 0),
        "seller": normalize_text(product.get("seller")),
        "status": status,
        "category": category,
    }


def product_from_mysql(row):
    price = row.get("price", 0)
    if isinstance(price, Decimal):
        price = float(price)

    linked_seller = (
        normalize_text(row.get("seller_username"))
        or normalize_text(row.get("seller_name"))
        or normalize_text(row.get("seller_identifier"))
    )
    display_seller = normalize_text(row.get("legacy_seller_name")) or linked_seller

    return clean_product({
        "id": row.get("id"),
        "title": row.get("title"),
        "name": row.get("title"),
        "description": row.get("description"),
        "price": price,
        "image_url": row.get("image_url") or "",
        "seller": display_seller,
        "seller_id": row.get("seller_id"),
        "seller_identifier": row.get("seller_identifier"),
        "legacy_seller_name": row.get("legacy_seller_name"),
        "status": row.get("status"),
        "category": row.get("category_name") or "Others",
    })


def category_id_for_name(category):
    execute_mysql_query(
        """
        INSERT INTO categories (name)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)
        """,
        (category,),
    )
    rows = execute_mysql_query(
        "SELECT id FROM categories WHERE name = %s LIMIT 1",
        (category,),
        fetch=True,
    )
    return rows[0]["id"] if rows else None


def load_products():
    if mysql_products_enabled():
        rows = execute_mysql_query(
            """
            SELECT p.id, p.seller_id, p.seller_identifier, p.legacy_seller_name,
                   p.title, p.description, p.price, p.image_url, p.status,
                   c.name AS category_name, u.name AS seller_name,
                   u.username AS seller_username
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN users u ON u.id = p.seller_id
            ORDER BY p.id
            """,
            fetch=True,
        )
        return [product_from_mysql(row) for row in rows]

    return [clean_product(product) for product in load_json(data_file("products"))]


def save_products(products):
    if mysql_products_enabled():
        for product in products:
            category = normalize_text(product.get("category")) or "Others"
            category_id = category_id_for_name(category)
            execute_mysql_query(
                """
                UPDATE products
                SET title = %s,
                    description = %s,
                    price = %s,
                    image_url = %s,
                    status = %s,
                    category_id = %s
                WHERE id = %s
                """,
                (
                    normalize_text(product.get("title")) or normalize_text(product.get("name")),
                    normalize_text(product.get("description")),
                    product.get("price", 0),
                    normalize_text(product.get("image_url")),
                    normalize_text(product.get("status")) or "Available",
                    category_id,
                    product.get("id"),
                ),
            )
        return

    save_json(data_file("products"), products)


def get_seller_products(user, status_filter="all"):
    products = [
        product for product in load_products()
        if product_belongs_to_seller(product, user)
    ]

    if status_filter in ["available", "sold"]:
        wanted_status = status_filter.capitalize()
        products = [
            product for product in products
            if normalize_text(product.get("status")) == wanted_status
        ]

    return products


def count_products(products):
    return {
        "total": len(products),
        "available": sum(
            1 for product in products
            if normalize_text(product.get("status")) == "Available"
        ),
        "sold": sum(
            1 for product in products
            if normalize_text(product.get("status")) == "Sold"
        ),
    }


def parse_price(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def next_product_id(products):
    if not products:
        return 1

    product_ids = []
    for product in products:
        try:
            product_ids.append(int(product.get("id", 0)))
        except (TypeError, ValueError):
            product_ids.append(0)

    return max(product_ids) + 1


def add_product(form, user):
    products = load_products()
    title = normalize_text(form.get("title")) or normalize_text(form.get("name"))
    description = normalize_text(form.get("description"))
    price = parse_price(form.get("price"))
    category = normalize_text(form.get("category")) or "Others"

    if not title or price is None:
        return False, "Product name and price are required."

    if category not in VALID_CATEGORIES:
        category = "Others"

    if mysql_products_enabled():
        category_id = category_id_for_name(category)
        execute_mysql_query(
            """
            INSERT INTO products (
                seller_id, seller_identifier, category_id, title,
                description, price, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user.get("user_id"),
                seller_name(user),
                category_id,
                title,
                description,
                price,
                "Available",
            ),
        )
        return True, None

    products.append({
        "id": next_product_id(products),
        "title": title,
        "name": title,
        "description": description,
        "price": price,
        "seller": seller_name(user),
        "status": "Available",
        "category": category,
    })
    save_products(products)
    return True, None


def edit_product(product_id, form, user):
    products = load_products()
    title = normalize_text(form.get("title")) or normalize_text(form.get("name"))
    price = parse_price(form.get("price"))
    status = normalize_text(form.get("status")) or "Available"
    category = normalize_text(form.get("category")) or "Others"

    if not title or price is None:
        return False, "Product name and price are required."

    if status not in VALID_STATUSES:
        return False, "Invalid product status."

    if category not in VALID_CATEGORIES:
        category = "Others"

    if mysql_products_enabled():
        product = next(
            (
                item for item in products
                if item.get("id") == product_id
                and product_belongs_to_seller(item, user)
            ),
            None,
        )
        if product is None:
            return False, "Product not found."

        category_id = category_id_for_name(category)
        execute_mysql_query(
            """
            UPDATE products
            SET title = %s,
                description = %s,
                price = %s,
                status = %s,
                category_id = %s
            WHERE id = %s
            """,
            (
                title,
                normalize_text(form.get("description")),
                price,
                status,
                category_id,
                product_id,
            ),
        )
        return True, None

    for product in products:
        if product.get("id") == product_id and product_belongs_to_seller(product, user):
            product["title"] = title
            product["name"] = title
            product["description"] = normalize_text(form.get("description"))
            product["price"] = price
            product["status"] = status
            product["category"] = category
            save_products(products)
            return True, None

    return False, "Product not found."


def delete_product(product_id, user):
    products = load_products()

    if mysql_products_enabled():
        product = next(
            (
                item for item in products
                if item.get("id") == product_id
                and product_belongs_to_seller(item, user)
            ),
            None,
        )
        if product is None:
            return False, "Product not found."

        execute_mysql_query("DELETE FROM products WHERE id = %s", (product_id,))
        return True, None

    kept_products = [
        product for product in products
        if not (
            product.get("id") == product_id
            and product_belongs_to_seller(product, user)
        )
    ]

    if len(kept_products) == len(products):
        return False, "Product not found."

    save_products(kept_products)
    return True, None
