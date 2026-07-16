CREATE DATABASE IF NOT EXISTS rp_marketplace;

USE rp_marketplace;

CREATE TABLE IF NOT EXISTS messages (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    product_id BIGINT UNSIGNED NOT NULL,
    sender_id BIGINT UNSIGNED NULL,
    receiver_id BIGINT UNSIGNED NULL,
    sender_identifier VARCHAR(255) NULL,
    receiver_identifier VARCHAR(255) NULL,
    message_text TEXT NOT NULL,
    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_messages_product
        FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_messages_sender
        FOREIGN KEY (sender_id)
        REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_messages_receiver
        FOREIGN KEY (receiver_id)
        REFERENCES users(id)
        ON DELETE SET NULL,
    INDEX idx_messages_product_time (product_id, sent_at),
    INDEX idx_messages_receiver_read (receiver_id, read_at),
    INDEX idx_messages_participants
        (sender_id, receiver_id, product_id, sent_at)
);

SHOW TABLES;
DESCRIBE messages;
SELECT COUNT(*) AS message_count FROM messages;
