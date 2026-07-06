import pytest
from backend.services.marketplace_service import (
    add_to_wishlist,
    get_wishlist_ids,
    get_wishlist_products,
    get_wishlist_statistics,
    remove_from_wishlist,
)


@pytest.fixture
def test_user():
    """Create a test user."""
    return {
        "user_id": 999,
        "name": "Test User",
        "username": "testuser",
        "email": "test@myrp.edu.sg",
        "student_id": "2401234",
        "role": "student",
    }


class TestWishlistFunctionality:
    """Test wishlist add, remove, and retrieval operations."""

    def test_add_to_wishlist(self, test_user):
        """Test adding an item to wishlist."""
        # Assuming product ID 1 exists
        result = add_to_wishlist(1, test_user)
        assert result is True

    def test_get_wishlist_ids(self, test_user):
        """Test retrieving wishlist IDs for a user."""
        # Add items first
        add_to_wishlist(1, test_user)
        add_to_wishlist(2, test_user)
        
        wishlist_ids = get_wishlist_ids(test_user)
        assert 1 in wishlist_ids
        assert 2 in wishlist_ids

    def test_remove_from_wishlist(self, test_user):
        """Test removing an item from wishlist."""
        add_to_wishlist(1, test_user)
        result = remove_from_wishlist(1, test_user)
        assert result is True
        
        wishlist_ids = get_wishlist_ids(test_user)
        assert 1 not in wishlist_ids

    def test_cannot_add_nonexistent_product(self, test_user):
        """Test that adding nonexistent product returns False."""
        result = add_to_wishlist(9999, test_user)
        assert result is False

    def test_cannot_remove_from_empty_wishlist(self, test_user):
        """Test removing from empty wishlist returns False."""
        result = remove_from_wishlist(1, test_user)
        assert result is False

    def test_add_duplicate_item(self, test_user):
        """Test that adding duplicate item doesn't create duplicate."""
        add_to_wishlist(1, test_user)
        add_to_wishlist(1, test_user)
        
        wishlist_ids = get_wishlist_ids(test_user)
        count = sum(1 for id in wishlist_ids if id == 1)
        assert count == 1


class TestWishlistSorting:
    """Test wishlist sorting functionality."""

    def test_sort_by_date_added(self, test_user):
        """Test sorting wishlist by date added (default)."""
        add_to_wishlist(1, test_user)
        add_to_wishlist(2, test_user)
        add_to_wishlist(3, test_user)
        
        products = get_wishlist_products(test_user, sort_by="date_added")
        assert len(products) == 3

    def test_sort_by_price_low_to_high(self, test_user):
        """Test sorting wishlist by price (low to high)."""
        add_to_wishlist(1, test_user)
        add_to_wishlist(2, test_user)
        
        products = get_wishlist_products(test_user, sort_by="price_low")
        assert len(products) > 0
        
        # Verify sorted correctly (if multiple items)
        if len(products) > 1:
            for i in range(len(products) - 1):
                assert float(products[i].get("price", 0)) <= float(products[i + 1].get("price", 0))

    def test_sort_by_price_high_to_low(self, test_user):
        """Test sorting wishlist by price (high to low)."""
        add_to_wishlist(1, test_user)
        add_to_wishlist(2, test_user)
        
        products = get_wishlist_products(test_user, sort_by="price_high")
        assert len(products) > 0
        
        # Verify sorted correctly (if multiple items)
        if len(products) > 1:
            for i in range(len(products) - 1):
                assert float(products[i].get("price", 0)) >= float(products[i + 1].get("price", 0))


class TestWishlistStatistics:
    """Test wishlist statistics calculation."""

    def test_empty_wishlist_statistics(self, test_user):
        """Test statistics for empty wishlist."""
        stats = get_wishlist_statistics(test_user)
        
        assert stats["total_items"] == 0
        assert stats["total_value"] == 0.0
        assert stats["available_items"] == 0
        assert stats["sold_items"] == 0

    def test_wishlist_statistics_with_items(self, test_user):
        """Test statistics with items in wishlist."""
        add_to_wishlist(1, test_user)
        add_to_wishlist(2, test_user)
        
        stats = get_wishlist_statistics(test_user)
        
        assert stats["total_items"] == 2
        assert stats["total_value"] > 0
        assert isinstance(stats["available_items"], int)
        assert isinstance(stats["sold_items"], int)

    def test_statistics_total_value_format(self, test_user):
        """Test that total value is formatted to 2 decimal places."""
        add_to_wishlist(1, test_user)
        
        stats = get_wishlist_statistics(test_user)
        
        # Verify it's a float with at most 2 decimal places
        assert isinstance(stats["total_value"], float)
        assert len(str(stats["total_value"]).split('.')[-1]) <= 2

    def test_statistics_with_none_user(self):
        """Test that statistics with None user returns defaults."""
        stats = get_wishlist_statistics(None)
        
        assert stats["total_items"] == 0
        assert stats["total_value"] == 0.0
        assert stats["available_items"] == 0
        assert stats["sold_items"] == 0


class TestWishlistEdgeCases:
    """Test edge cases and error handling."""

    def test_get_wishlist_ids_none_user(self):
        """Test getting wishlist IDs for None user."""
        result = get_wishlist_ids(None)
        assert result == []

    def test_add_to_wishlist_none_user(self):
        """Test adding to wishlist with None user."""
        result = add_to_wishlist(1, None)
        assert result is False

    def test_remove_from_wishlist_none_user(self):
        """Test removing from wishlist with None user."""
        result = remove_from_wishlist(1, None)
        assert result is False

    def test_sort_with_invalid_sort_option(self, test_user):
        """Test that invalid sort option defaults gracefully."""
        add_to_wishlist(1, test_user)
        
        # Default behavior when sort_by is invalid
        products = get_wishlist_products(test_user, sort_by="invalid_sort")
        assert len(products) > 0
