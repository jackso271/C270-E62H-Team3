from backend.routes.sell_items_routes import sell_items_bp
from backend.services.sell_items_service import clean_text, parse_price


def test_sell_items_blueprint_exists():
    assert sell_items_bp.name == "sell_items"


def test_clean_text_removes_spaces():
    assert clean_text("  Laptop Bag  ") == "Laptop Bag"


def test_parse_price_accepts_valid_price():
    assert parse_price("12.50") == 12.50


def test_parse_price_rejects_negative_price():
    assert parse_price("-5") is None