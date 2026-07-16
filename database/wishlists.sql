CREATE DATABASE IF NOT EXISTS rp_marketplace;

USE rp_marketplace;

CREATE TABLE IF NOT EXISTS wishlists (
    user_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, product_id),
    CONSTRAINT fk_wishlists_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_wishlists_product
        FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON DELETE CASCADE,
    INDEX idx_wishlists_added_at (added_at)
);

SHOW TABLES;
DESCRIBE wishlists;
SELECT COUNT(*) AS wishlist_count FROM wishlists;
