USE rp_marketplace;

CREATE TABLE IF NOT EXISTS login_attempts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NULL,
    login_identifier VARCHAR(255) NOT NULL,
    was_successful BOOLEAN NOT NULL,
    failure_reason VARCHAR(255) NULL,
    attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_login_attempts_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE SET NULL,
    INDEX idx_login_attempts_user_time (user_id, attempted_at),
    INDEX idx_login_attempts_result_time (was_successful, attempted_at)
);

DESCRIBE login_attempts;

SELECT COUNT(*) AS login_attempt_count
FROM login_attempts;

SELECT id, user_id, login_identifier, was_successful, failure_reason, attempted_at
FROM login_attempts
ORDER BY attempted_at DESC, id DESC
LIMIT 20;
