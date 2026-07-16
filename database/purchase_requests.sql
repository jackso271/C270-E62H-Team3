CREATE DATABASE IF NOT EXISTS rp_marketplace;

USE rp_marketplace;

CREATE TABLE IF NOT EXISTS purchase_requests (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    product_id BIGINT UNSIGNED NOT NULL,
    buyer_id BIGINT UNSIGNED NULL,
    buyer_identifier VARCHAR(255) NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Pending',
    rejection_reason VARCHAR(500) NULL,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_purchase_requests_product
        FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_purchase_requests_buyer
        FOREIGN KEY (buyer_id)
        REFERENCES users(id)
        ON DELETE SET NULL,
    INDEX idx_purchase_requests_product_status (product_id, status),
    INDEX idx_purchase_requests_buyer (buyer_id),
    INDEX idx_purchase_requests_requested_at (requested_at)
);

SHOW TABLES;
DESCRIBE purchase_requests;
SELECT COUNT(*) AS purchase_request_count FROM purchase_requests;
