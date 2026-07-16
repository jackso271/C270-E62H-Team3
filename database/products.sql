USE rp_marketplace;

CREATE TABLE IF NOT EXISTS categories (
    id SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(80) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_categories_name (name)
);

CREATE TABLE IF NOT EXISTS products (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    seller_id BIGINT UNSIGNED NULL,
    seller_identifier VARCHAR(255) NOT NULL,
    legacy_seller_name VARCHAR(150) NULL,
    category_id SMALLINT UNSIGNED NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    image_url VARCHAR(500) NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Available',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_products_seller
        FOREIGN KEY (seller_id)
        REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE SET NULL,
    INDEX idx_products_seller (seller_id),
    INDEX idx_products_seller_identifier (seller_identifier),
    INDEX idx_products_status (status),
    INDEX idx_products_category (category_id),
    CONSTRAINT chk_products_price CHECK (price >= 0)
);

DESCRIBE categories;
DESCRIBE products;

SELECT COUNT(*) AS category_count
FROM categories;

SELECT COUNT(*) AS product_count
FROM products;

SELECT p.id, p.title, p.seller_identifier, p.legacy_seller_name,
       c.name AS category, p.status, p.price
FROM products p
LEFT JOIN categories c ON c.id = p.category_id
ORDER BY p.id
LIMIT 20;
