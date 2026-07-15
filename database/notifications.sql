USE rp_marketplace;

CREATE TABLE IF NOT EXISTS notifications (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Info',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_notifications_created_at (created_at),
    INDEX idx_notifications_status (status)
);

DESCRIBE notifications;

SELECT COUNT(*) AS notification_count
FROM notifications;

SELECT id, title, status, created_at
FROM notifications
ORDER BY created_at DESC, id DESC
LIMIT 10;
