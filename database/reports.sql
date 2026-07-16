USE rp_marketplace;

CREATE TABLE IF NOT EXISTS reports (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    product_id BIGINT UNSIGNED NULL,
    product_title VARCHAR(150) NOT NULL,
    seller_identifier VARCHAR(255) NULL,
    reported_by VARCHAR(255) NULL,
    reason VARCHAR(255) NOT NULL,
    comments TEXT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME NULL,
    PRIMARY KEY (id),
    INDEX idx_reports_status (status),
    INDEX idx_reports_created_at (created_at),
    INDEX idx_reports_product_id (product_id)
);

DESCRIBE reports;

SELECT COUNT(*) AS report_count
FROM reports;

SELECT id, product_title, reported_by, reason, status, created_at
FROM reports
ORDER BY created_at DESC, id DESC
LIMIT 10;
