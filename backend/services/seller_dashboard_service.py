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


def load_products():
    return [clean_product(product) for product in load_json(data_file("products"))]


def save_products(products):
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
